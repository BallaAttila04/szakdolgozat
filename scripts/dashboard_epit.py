"""
A napi monitor dashboardja (docs/dashboard.html) es gepi adat-feedje
(docs/adat/) - a termek statikus felulete.

Nincs szerver es nincs bejelentkezes: a GitHub Actions naponta lefuttatja a
monitort, ez a szkript pedig a kis aggregalt tablakbol egyetlen onallo
HTML-t (beagyazott JSON, kulso fuggoseg nelkul) es nehany kis JSON/CSV fajlt
general, amit a GitHub Pages statikusan kiszolgal.

Mi honnan jon:
  outputs/monitor/            allapot.json, jelzesek*.csv, kapuvonal_napi.csv,
                              megrakottsag_napi.csv          (naponta frissul)
  outputs/backtest/           a backtest.py kimenetei        (pillanatkep)
  outputs/kapuk_kiterjesztes/ a kiserleti kapuk sorozatai    (pillanatkep)
  scripts/kapuk.json          a kapuk leirasa

A backtest es a kiserleti kapuk nem futnak naponta (a PortWatch-adat es a
Parquet-tarolo nincs a futtaton). Ha a forrasmappa hianyzik, a blokk a
legutobb publikalt docs/adat/backtest.json, illetve kiserleti_kapuk.json
fajlbol jon, igy a napi futas nem uriti ki a dashboard ezen reszeit.

Kimenet:
  docs/dashboard.html               <- scripts/dashboard_sablon.html + adat
  docs/adat/legutobbi.json          utolso nap, sorozatok, aktiv jelzesek
  docs/adat/jelzesek.csv            a monitor osszes jelzes-sora
  docs/adat/idosor_forgalom.csv     napi atkelesek kapu/irany/csoport szerint
  docs/adat/idosor_megrakottsag.csv napi megrakottsagi tabla
  docs/adat/kiserleti_kapuk_napi.csv  a kiserleti kapuk kereskedelmi atkelesei
  docs/adat/backtest.json           a backtest osszefoglaloja (a dashboard blokkja)
  docs/adat/kiserleti_kapuk.json    a kiserleti kapuk blokkja
  docs/adat/katalogus.json          a feed fajljai: oszlopok, sorok, meret, sha256

Hasznalat:
    python dashboard_epit.py
    python dashboard_epit.py --monitor outputs/monitor --oldal docs
"""

import argparse
import csv
import hashlib
import io
import json
import math
import sys
from datetime import date, datetime, timezone
from pathlib import Path

import pandas as pd

from utak import KIMENET, OLDAL, SABLONOK
# A jelzesi szabaly parameterei egyetlen helyrol: a dashboard JS-e ezekkel
# szamol, igy nem csuszhat el a monitortol.
from monitor import ALAP_HETEK, KUSZOB_SZORZO, MAD_SKALA, MIN_ALAPNAP
from megrakottsag import GORDULO_NAP

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)
except AttributeError:
    pass

# --- Parameterek ----------------------------------------------------------

HELYORZO = "/*DASHBOARD_ADAT*/"
FEED_MAPPA = "adat"
SEMA_VERZIO = 1            # a feed szerkezetenek verzioja; tores eseten no

# A Kiel-csatorna tervezett teljes lezarasa (naplo, 2026-09-18 21:20) - a
# dashboard idosorain jelolt idoszak.
KIEL_NAPOK = ["2026-07-15", "2026-07-16"]

# Ennyi napot mutatnak a KPI-csempek mini-idosorai es a "legutobbi jelzesek"
# lista: egy honap eleg ahhoz, hogy a tartos eltolodas lathato legyen, de a
# csempe meg olvashato marad.
UTOLSO_NAPOK = 30

# A feed osszmerete felett figyelmeztet: a dashboard es a feed gyors
# letolthetosege (mobilon is) a cel; a jelenlegi meret ennek toredeke.
FEED_MAX_MB = 5.0

# A backtestbol a dashboardra kerulo szabalyok az injektalasi tablaban: a
# hivatalos szabaly (R0, k=2), a CUSUM (R4, h=4) es a 7 napos osszeg (R3,
# k=2) - a backtest ezeket emeli ki a szabalyvaltozatok kozul.
BACKTEST_SZABALYOK = ["R0 (k=2)", "R4 CUSUM h=4", "R3 7 napos összeg k=2"]

KERESKEDELMI = ["Teherhajó", "Tanker"]
FORGALOM_SOROZATOK = ["Nagy-Balti-öv", "Øresund", "Mindkét kapu"]


# --- Segedfuggvenyek --------------------------------------------------------

def _ertek(v):
    """JSON-kompatibilis ertek: NaN -> None, egesz erteku float -> int."""
    if v is None:
        return None
    if isinstance(v, float):
        if math.isnan(v):
            return None
        return int(v) if v.is_integer() and abs(v) < 2**53 else round(v, 6)
    if hasattr(v, "item"):          # numpy skalar
        return _ertek(v.item())
    return v


def sorok(df: pd.DataFrame) -> list:
    return [{k: _ertek(v) for k, v in r.items()} for r in df.to_dict("records")]


def csv_olvas(ut: Path) -> pd.DataFrame:
    return pd.read_csv(ut, dtype={"datum": str}, encoding="utf-8")


def fajl_ido(ut: Path) -> str:
    return datetime.fromtimestamp(ut.stat().st_mtime, timezone.utc).date().isoformat()


# --- Monitor (naponta frissul) ------------------------------------------------

def hivatalos_jelzesek(monitor: Path) -> pd.DataFrame:
    """A monitor.py jelzes-tablai egyben, 'tipus' oszloppal."""
    reszek = []
    for nev, tipus in [("jelzesek.csv", "forgalom"),
                       ("jelzesek_megrakottsag.csv", "megrakottsag")]:
        f = monitor / nev
        if f.exists():
            j = csv_olvas(f)
            j.insert(1, "tipus", tipus)
            reszek.append(j)
    if not reszek:
        raise SystemExit(f"Nincs jelzes-tabla a {monitor} mappaban - elobb a monitor.py kell.")
    return pd.concat(reszek, ignore_index=True)


def legutobbi(monitor: Path) -> dict:
    """Az utolso nap allapota: ez a docs/adat/legutobbi.json tartalma, es ezt
    irja ki az 'aismonitor.py allapot' is."""
    a = json.loads((monitor / "allapot.json").read_text(encoding="utf-8"))
    j = hivatalos_jelzesek(monitor)
    nap = a["utolso_nap"]
    kuszob = {**a.get("kuszob", {}), **a.get("kuszob_megrakottsag", {})}
    sorozatok = []
    for nev in dict.fromkeys(j["sorozat"]):
        s = j[j["sorozat"] == nev]
        u = s[s["datum"] == nap]
        r = u.iloc[0] if len(u) else s.iloc[-1]
        sorozatok.append({
            "sorozat": nev, "tipus": r["tipus"], "datum": r["datum"],
            "ertek": _ertek(r["ertek"]), "alapszint": _ertek(r["alapszint"]),
            "elteres": _ertek(r["elteres"]), "kuszob": _ertek(kuszob.get(nev, r["kuszob"])),
            "alapnapok": _ertek(r["alapnapok"]), "jelzes": r["jelzes"]})
    napok = sorted(j["datum"].unique())[-UTOLSO_NAPOK:]
    jel = j[j["datum"].isin(napok) & j["jelzes"].str.startswith("szokatlanul")]
    return {
        "sema_verzio": SEMA_VERZIO,
        "utolso_nap": nap,
        "elso_nap": a.get("elso_nap"),
        "napok_szama": a.get("napok_szama"),
        "frissitve_utc": a.get("frissitve_utc"),
        "utolso_futas": a.get("utolso_futas", {}),
        "szabaly": {"alap_hetek": a.get("alap_hetek"), "min_alapnap": a.get("min_alapnap"),
                    "kuszob_szorzo": a.get("kuszob_szorzo"), "gordulo_nap": a.get("gordulo_nap"),
                    "megrakott_kuszob_relativ_merules": a.get("megrakott_kuszob_relativ_merules")},
        "sorozatok": sorozatok,
        "aktiv_jelzesek": [s for s in sorozatok
                           if s["datum"] == nap and str(s["jelzes"]).startswith("szokatlanul")],
        "jelzesek_utolso_napok": sorok(jel[["datum", "tipus", "sorozat", "ertek", "alapszint",
                                            "elteres", "kuszob", "jelzes"]]),
    }


def kodolt_tabla(df: pd.DataFrame, dim: list, ertekek: list, napok: list) -> dict:
    """Hosszu tabla tomoritve: a dimenziok szotarkent, a sorok indexekkel."""
    szotar = {d: list(dict.fromkeys(sorted(df[d].unique()))) for d in dim}
    nap_i = {d: i for i, d in enumerate(napok)}
    idx = {d: {v: i for i, v in enumerate(szotar[d])} for d in dim}
    ki = []
    for r in df.itertuples(index=False):
        rr = r._asdict()
        ki.append([nap_i[rr["datum"]]] + [idx[d][rr[d]] for d in dim]
                  + [_ertek(rr[e]) for e in ertekek])
    return {"dim": dim, "ertekek": ertekek, **{d: szotar[d] for d in dim}, "sorok": ki}


def monitor_blokk(monitor: Path) -> dict:
    a = json.loads((monitor / "allapot.json").read_text(encoding="utf-8"))
    forg = csv_olvas(monitor / "kapuvonal_napi.csv")
    napok = sorted(forg["datum"].unique())
    meg_f = monitor / "megrakottsag_napi.csv"
    meg = csv_olvas(meg_f) if meg_f.exists() else None
    j = hivatalos_jelzesek(monitor)

    hiv = []
    for nev in dict.fromkeys(j["sorozat"]):
        s = j[j["sorozat"] == nev]
        hiv.append({"nev": nev, "tipus": s["tipus"].iloc[0],
                    "kuszob": _ertek(s["kuszob"].dropna().iloc[0]) if s["kuszob"].notna().any() else None,
                    "datum": s["datum"].tolist(),
                    "ertek": [_ertek(v) for v in s["ertek"]],
                    "alapszint": [_ertek(v) for v in s["alapszint"]],
                    "elteres": [_ertek(v) for v in s["elteres"]],
                    "jelzes": s["jelzes"].tolist()})
    blokk = {
        "allapot": a,
        "napok": napok,
        "forgalom": kodolt_tabla(forg, ["kapu", "irany", "csoport"], ["atkeles"], napok),
        "megrakottsag": (kodolt_tabla(meg[meg["datum"].isin(napok)],
                                      ["kapu", "irany", "csoport"],
                                      ["atkeles", "ertekelheto", "megrakott", "volumenindex"], napok)
                         if meg is not None else None),
        "hivatalos": hiv,
    }
    return blokk, forg, meg, j


# --- Backtest (pillanatkep) -----------------------------------------------------

def backtest_blokk(mappa: Path):
    kell = ["bootstrap.csv", "munkapont.csv", "szabalyok.csv", "roc.csv", "injektalas.csv",
            "walkforward.csv", "kuszob_palya.csv", "placebo.csv", "portwatch_egyezes.csv",
            "reprodukcio.csv"]
    hiany = [f for f in kell if not (mappa / f).exists()]
    if hiany:
        return None, hiany
    t = {f[:-4]: pd.read_csv(mappa / f, encoding="utf-8") for f in kell}
    inj = t["injektalas"]
    inj = inj[inj["szabaly"].isin(BACKTEST_SZABALYOK) & (inj["ablak"] == "sajat")]
    inj = inj[["sorozat", "szabaly", "irany", "m", "L", "n", "eszlelt", "arany",
               "keses_min", "keses_median", "keses_max"]]
    kp = t["kuszob_palya"]
    palya = {}
    for nev, g in kp.groupby("sorozat", sort=False):
        palya[nev] = {c: [_ertek(v) for v in g[c]] for c in
                      ["datum", "ertek", "alapszint", "elteres", "kuszob_retro",
                       "kuszob_bovulo", "kuszob_rogzitett", "jelzes_retro", "jelzes_bovulo",
                       "jelzes_rogzitett"]}
    otsu = mappa / "otsu_tanulo.csv"
    return {
        "forras": "outputs/backtest/",
        "keszult": max(fajl_ido(mappa / f) for f in kell),
        "bootstrap": sorok(t["bootstrap"]),
        "munkapont": sorok(t["munkapont"]),
        "szabalyok": sorok(t["szabalyok"]),
        "roc": sorok(t["roc"]),
        "injektalas": sorok(inj),
        "walkforward": sorok(t["walkforward"]),
        "kuszob_palya": palya,
        "placebo": sorok(t["placebo"]),
        "portwatch_egyezes": sorok(t["portwatch_egyezes"]),
        "reprodukcio": sorok(t["reprodukcio"]),
        "otsu_tanulo": sorok(pd.read_csv(otsu, encoding="utf-8")) if otsu.exists() else [],
    }, []


# --- Kiserleti kapuk (pillanatkep) ------------------------------------------------

def kapuk_blokk(mappa: Path, konfig: Path):
    kell = ["kapuvonal_napi.csv", "napi_statisztika.csv", "portwatch_osszevetes.csv",
            "koncentracio.csv", "kiel_ablak.csv"]
    hiany = [f for f in kell if not (mappa / f).exists()]
    if hiany:
        return None, None, hiany
    k = csv_olvas(mappa / "kapuvonal_napi.csv")
    ker = (k[k["csoport"].isin(KERESKEDELMI)]
           .groupby(["datum", "kapu", "irany"], as_index=False)["atkeles"].sum())
    napok = sorted(k["datum"].unique())
    kapuk = json.loads(konfig.read_text(encoding="utf-8"))["kapuk"] if konfig.exists() else []
    sorrend = [g["nev"] for g in kapuk] or sorted(ker["kapu"].unique())
    meta = {g["nev"]: g for g in kapuk}
    tabla = kodolt_tabla(ker, ["kapu", "irany"], ["atkeles"], napok)
    # a kapuk a konfiguracio sorrendjeben (a monitor-kapuk elol)
    regi = tabla["kapu"]
    uj = [n for n in sorrend if n in regi] + [n for n in regi if n not in sorrend]
    atkod = {i: uj.index(n) for i, n in enumerate(regi)}
    tabla["kapu"] = uj
    tabla["sorok"] = [[r[0], atkod[r[1]], *r[2:]] for r in tabla["sorok"]]
    koncentracio = pd.read_csv(mappa / "koncentracio.csv", encoding="utf-8")[
        ["kapu", "ker_atkeles", "ker_hajo", "ker_top5_arany"]]
    blokk = {
        "forras": "outputs/kapuk_kiterjesztes/",
        "keszult": fajl_ido(mappa / "kapuvonal_napi.csv"),
        "napok": napok,
        "kapuk": [{"nev": n, "kiserleti": not meta.get(n, {}).get("monitor", False),
                   "iranyok": meta.get(n, {}).get("iranyok", []),
                   "kifele": meta.get(n, {}).get("kifele"),
                   "indoklas": meta.get(n, {}).get("indoklas", "")} for n in uj],
        "kereskedelmi": tabla,
        "napi_statisztika": sorok(pd.read_csv(mappa / "napi_statisztika.csv", encoding="utf-8")),
        "portwatch": sorok(pd.read_csv(mappa / "portwatch_osszevetes.csv", encoding="utf-8")),
        "koncentracio": sorok(koncentracio),
        "kiel_ablak": sorok(csv_olvas(mappa / "kiel_ablak.csv")),
    }
    hosszu = ker.copy()
    hosszu["kiserleti"] = [int(not meta.get(n, {}).get("monitor", False)) for n in hosszu["kapu"]]
    hosszu = hosszu.rename(columns={"atkeles": "kereskedelmi_atkeles"})
    return blokk, hosszu, []


# --- Feed ---------------------------------------------------------------------

FEED_LEIRAS = {
    "legutobbi.json": ("Az utolsó feldolgozott nap: sorozatonként érték, alapszint, eltérés, "
                       "küszöb, jelzés; aktív jelzések; az utolsó futás állapota.", None),
    "jelzesek.csv": ("A monitor összes jelzés-sora (forgalom és megrakottság).",
                     {"datum": "nap (ÉÉÉÉ-HH-NN, UTC)", "tipus": "forgalom | megrakottsag",
                      "sorozat": "a sorozat neve", "ertek": "a nap értéke (átkelés; a 7 napos "
                      "sorozatoknál gördülő összeg)", "alapnapok": "az alapszinthez talált "
                      "korábbi azonos hétnapok száma (0–4)", "alapszint": "az előző 4 hét azonos "
                      "napjainak mediánja (üres: kevesebb mint 3 nap)", "elteres": "ertek / "
                      "alapszint − 1", "kuszob": "a sorozat jelzési küszöbe (relatív)",
                      "jelzes": "normál | szokatlanul magas | szokatlanul alacsony | nincs alapszint"}),
    "idosor_forgalom.csv": ("Napi kapuvonal-átkelések kapu, irány és hajócsoport szerint.",
                            {"datum": "nap", "kapu": "Nagy-Balti-öv | Øresund", "irany":
                             "átkelési irány", "csoport": "hajócsoport (AIS Ship type alapján)",
                             "atkeles": "átkelések száma"}),
    "idosor_megrakottsag.csv": ("Napi megrakottsági tábla (tanker, teherhajó).",
                                {"datum": "nap", "kapu": "kapu", "irany": "irány",
                                 "csoport": "Tanker | Teherhajó", "atkeles": "átkelés",
                                 "ertekelheto": "értékelhető merülésű átkelés",
                                 "megrakott": "megrakottnak minősített átkelés",
                                 "volumenindex": "Σ hossz × szélesség × merülés (m³)",
                                 "megrakott_arany": "megrakott / értékelhető"}),
    "kiserleti_kapuk_napi.csv": ("A kísérleti kapuk napi kereskedelmi (teher + tanker) "
                                 "átkelései – kísérleti, nem a monitor része.",
                                 {"datum": "nap", "kapu": "kapu", "irany": "irány",
                                  "kereskedelmi_atkeles": "teherhajó + tanker átkelés",
                                  "kiserleti": "1 = kísérleti kapu, 0 = monitor-kapu"}),
    "backtest.json": ("A jelzési szabály backtestjének összefoglalója (pillanatkép).", None),
    "kiserleti_kapuk.json": ("A kísérleti kapuk blokkja: sorozatok, statisztika, "
                             "PortWatch-összevetés (pillanatkép).", None),
}


def csv_szoveg(df: pd.DataFrame) -> str:
    b = io.StringIO()
    df.to_csv(b, index=False, lineterminator="\n")
    return b.getvalue()


def feed_irasa(cel: Path, tartalom: dict) -> list:
    """A feed fajljai + katalogus.json. Visszaadja a katalogus sorait."""
    cel.mkdir(parents=True, exist_ok=True)
    katalogus = []
    for nev, szoveg in tartalom.items():
        adat = szoveg.encode("utf-8")
        (cel / nev).write_bytes(adat)
        leiras, oszlopok = FEED_LEIRAS[nev]
        sor = {"fajl": nev, "leiras": leiras, "bajt": len(adat),
               "sha256": hashlib.sha256(adat).hexdigest()}
        if nev.endswith(".csv"):
            olvaso = list(csv.reader(io.StringIO(szoveg)))
            sor["sorok"] = len(olvaso) - 1
            sor["oszlopok"] = [{"nev": o, "leiras": (oszlopok or {}).get(o, "")}
                               for o in olvaso[0]]
        katalogus.append(sor)
    (cel / "katalogus.json").write_text(json.dumps(
        {"sema_verzio": SEMA_VERZIO, "fajlok": katalogus}, ensure_ascii=False, indent=1),
        encoding="utf-8", newline="\n")
    (cel / "README.md").write_text(readme_md(katalogus), encoding="utf-8", newline="\n")
    return katalogus


def readme_md(katalogus: list) -> str:
    """A feed leirasa emberi olvasasra (docs/adat/README.md) - a katalogusbol
    generalva, igy nem tud elcsuszni a tenyleges fajloktol."""
    t = ["# Dán szorosok monitor – adat-feed", "",
         "A napi forgalmi monitor gépi felülete. A fájlok a napi futással együtt frissülnek",
         "(GitHub Actions → GitHub Pages), és változatlan URL-en érhetők el.", "",
         "- Kódolás: UTF-8; CSV: vesszővel tagolt, fejléccel, tizedesjel: pont.",
         "- Dátum: ÉÉÉÉ-HH-NN (a napi AIS-fájl napja, UTC).",
         "- Üres mező: nincs érték (pl. nincs alapszint).",
         f"- A szerkezet verziója: {SEMA_VERZIO} (a `katalogus.json` és a `legutobbi.json`"
         " `sema_verzio` mezője). Visszafelé nem kompatibilis változásnál nő.",
         "- A `katalogus.json` minden fájl méretét, sorszámát és SHA-256 ujjlenyomatát"
         " tartalmazza.", "",
         "## Fájlok", "", "| fájl | leírás | méret | sorok |", "|---|---|---|---|"]
    for s in katalogus:
        kb = f"{s['bajt'] / 1024:.1f}".replace(".", ",")
        t.append(f"| `{s['fajl']}` | {s['leiras']} | {kb} KB | {s.get('sorok', '–')} |")
    for s in katalogus:
        if "oszlopok" in s:
            t += ["", f"## `{s['fajl']}`", "", "| oszlop | jelentés |", "|---|---|"]
            t += [f"| `{o['nev']}` | {o['leiras'] or '–'} |" for o in s["oszlopok"]]
    t += ["", "## `legutobbi.json`", "",
          "| mező | jelentés |", "|---|---|",
          "| `utolso_nap` | az utolsó feldolgozott nap |",
          "| `frissitve_utc` | a monitor utolsó számolása |",
          "| `utolso_futas` | a napi futás állapota: `statusz` (ok / reszleges / hiba), `uzenet`, `ido_utc` |",
          "| `szabaly` | a jelzési szabály paraméterei |",
          "| `sorozatok[]` | sorozatonként az utolsó nap: `ertek`, `alapszint`, `elteres`, `kuszob`, `jelzes` |",
          "| `aktiv_jelzesek[]` | a `sorozatok` közül azok, amelyek az utolsó napon jeleznek |",
          f"| `jelzesek_utolso_napok[]` | az utolsó {UTOLSO_NAPOK} nap jelzései |", "",
          "A `backtest.json` és a `kiserleti_kapuk.json` pillanatkép: a dashboard megfelelő",
          "nézetének adatai, a `keszult` mező szerinti állapotban; naponta nem frissülnek.", ""]
    return "\n".join(t)


def keszult_megtart(uj: dict, cel: Path, nev: str) -> dict:
    """A pillanatkep 'keszult' datuma a forrasfajl mtime-jabol jon, ami a
    futtaton a git checkout ideje - igy minden nap a futas napjat mutatna.
    Ha a blokk tartalma a legutobb publikalttal azonos, a publikalt datum marad:
    a 'keszult' azt jelenti, mikor valtozott utoljara a pillanatkep."""
    regi = regi_blokk(cel, nev)
    if regi and "keszult" in regi:
        normal = json.loads(json.dumps(uj, ensure_ascii=False))
        if {k: v for k, v in normal.items() if k != "keszult"} == \
                {k: v for k, v in regi.items() if k != "keszult"}:
            uj["keszult"] = regi["keszult"]
    return uj


def regi_blokk(cel: Path, nev: str):
    f = cel / nev
    if f.exists():
        try:
            return json.loads(f.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return None
    return None


def jsonba(x) -> str:
    return json.dumps(x, ensure_ascii=False, separators=(",", ":"), allow_nan=False)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--monitor", type=Path, default=KIMENET / "monitor")
    ap.add_argument("--backtest", type=Path, default=KIMENET / "backtest")
    ap.add_argument("--kapuk-be", type=Path, default=KIMENET / "kapuk_kiterjesztes")
    ap.add_argument("--kapuk-konfig", type=Path, default=SABLONOK / "kapuk.json")
    ap.add_argument("--sablon", type=Path, default=SABLONOK / "dashboard_sablon.html")
    ap.add_argument("--oldal", type=Path, default=OLDAL, help="Az oldal celmappaja (alap: docs/)")
    args = ap.parse_args()

    if not (args.monitor / "allapot.json").exists():
        sys.exit(f"Hianyzik: {args.monitor / 'allapot.json'} - elobb a monitor.py kell.")
    feed_cel = args.oldal / FEED_MAPPA

    mon, forg, meg, j = monitor_blokk(args.monitor)
    print(f"Monitor: {len(forg):,} forgalmi sor, "
          f"{len(meg) if meg is not None else 0:,} megrakottsagi sor, {len(j):,} jelzes-sor, "
          f"{len(mon['napok'])} nap ({mon['napok'][0]} - {mon['napok'][-1]})")

    bt, hiany = backtest_blokk(args.backtest)
    if bt is None:
        bt = regi_blokk(feed_cel, "backtest.json")
        print(f"Backtest: a forras hianyos ({', '.join(hiany)}) - "
              + ("a korabban publikalt backtest.json marad" if bt else "a blokk ures lesz"))
    else:
        bt = keszult_megtart(bt, feed_cel, "backtest.json")
        print(f"Backtest: {args.backtest} ({bt['keszult']}), {len(bt['roc'])} ROC-pont, "
              f"{len(bt['injektalas'])} injektalasi sor")

    kp, kp_hosszu, hiany = kapuk_blokk(args.kapuk_be, args.kapuk_konfig)
    if kp is None:
        kp = regi_blokk(feed_cel, "kiserleti_kapuk.json")
        print(f"Kiserleti kapuk: a forras hianyos ({', '.join(hiany)}) - "
              + ("a korabban publikalt kiserleti_kapuk.json marad" if kp else "a blokk ures lesz"))
    else:
        kp = keszult_megtart(kp, feed_cel, "kiserleti_kapuk.json")
        print(f"Kiserleti kapuk: {len(kp['kapuk'])} kapu, {len(kp['napok'])} nap, "
              f"{len(kp['kereskedelmi']['sorok']):,} sor")

    # --- feed ---
    lu = legutobbi(args.monitor)
    lu["generalva_utc"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    tartalom = {
        "legutobbi.json": json.dumps(lu, ensure_ascii=False, indent=1),
        "jelzesek.csv": csv_szoveg(j),
        "idosor_forgalom.csv": csv_szoveg(forg),
    }
    if meg is not None:
        tartalom["idosor_megrakottsag.csv"] = csv_szoveg(meg)
    if kp_hosszu is not None:
        tartalom["kiserleti_kapuk_napi.csv"] = csv_szoveg(kp_hosszu)
    elif (feed_cel / "kiserleti_kapuk_napi.csv").exists():
        tartalom["kiserleti_kapuk_napi.csv"] = (feed_cel / "kiserleti_kapuk_napi.csv").read_text(encoding="utf-8")
    if bt:
        tartalom["backtest.json"] = json.dumps(bt, ensure_ascii=False, separators=(",", ":"))
    if kp:
        tartalom["kiserleti_kapuk.json"] = json.dumps(kp, ensure_ascii=False, separators=(",", ":"))
    katalogus = feed_irasa(feed_cel, tartalom)

    # --- dashboard ---
    adat = {
        "epitve_utc": lu["generalva_utc"],
        "sema_verzio": SEMA_VERZIO,
        "szabaly": {"alap_hetek": ALAP_HETEK, "min_alapnap": MIN_ALAPNAP,
                    "kuszob_szorzo": KUSZOB_SZORZO, "mad_skala": MAD_SKALA,
                    "gordulo_nap": GORDULO_NAP},
        "kiel": KIEL_NAPOK,
        "utolso_napok": UTOLSO_NAPOK,
        **mon,
        "backtest": bt,
        "kapuk": kp,
        "fajlok": [{k: v for k, v in s.items() if k != "sha256"} for s in katalogus]
                  + [{"fajl": "katalogus.json", "leiras": "A feed gépi leírása: fájlok, "
                      "oszlopok, sorszám, méret, SHA-256.",
                      "bajt": (feed_cel / "katalogus.json").stat().st_size},
                     {"fajl": "README.md", "leiras": "A feed leírása (a katalógusból generálva).",
                      "bajt": (feed_cel / "README.md").stat().st_size}],
    }
    sablon = args.sablon.read_text(encoding="utf-8")
    if sablon.count(HELYORZO) != 1:
        sys.exit(f"A sablonban pontosan egy {HELYORZO} helyorzo kell: {args.sablon}")
    # a </script> lezaras ne kerulhessen a beagyazott JSON-ba
    lap = sablon.replace(HELYORZO, jsonba(adat).replace("</", "<\\/"))
    if HELYORZO in lap or "/*DASHBOARD_" in lap:
        sys.exit("Kicsereletlen helyorzo maradt a dashboardban")
    args.oldal.mkdir(parents=True, exist_ok=True)
    (args.oldal / "dashboard.html").write_text(lap, encoding="utf-8", newline="\n")

    feed_bajt = sum(f.stat().st_size for f in feed_cel.iterdir() if f.is_file())
    print(f"\n  dashboard.html  {len(lap.encode('utf-8')) / 1024:>8,.0f} KB")
    for s in katalogus:
        print(f"  {FEED_MAPPA}/{s['fajl']:<26} {s['bajt'] / 1024:>8,.1f} KB"
              + (f"  {s['sorok']:>6,} sor" if "sorok" in s else ""))
    print(f"  feed osszesen: {feed_bajt / 1_048_576:.2f} MB "
          f"({sum(1 for f in feed_cel.iterdir() if f.is_file())} fajl)")
    print(f"  aktiv jelzes az utolso napon ({lu['utolso_nap']}): {len(lu['aktiv_jelzesek'])}")
    if feed_bajt / 1_048_576 > FEED_MAX_MB:
        print(f"  FIGYELEM: a feed nagyobb, mint {FEED_MAX_MB} MB")
    print(f"\n-> {args.oldal / 'dashboard.html'}\n-> {feed_cel}/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
