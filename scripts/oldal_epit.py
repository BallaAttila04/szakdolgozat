"""
A GitHub Pages oldal osszeallitasa a docs/ mappaba.

A konzulensnek egyetlen linket kell tudnia megnyitni, telepites es
bejelentkezes nelkul. A GitHub Pages a main ag docs/ mappajat szolgalja ki
statikusan, ezert ide kell masolni a mar legeneralt kimeneteket, es ide kell
beagyazni a diagramokat.

Mi honnan jon:
  docs/index.html   <- scripts/oldal_sablon.html + a hajo_statisztika.json-bol
                       generalt SVG-diagramok (helyorzok cserelve)
  docs/terkep.html  <- outputs/terkep.html      (terkep_epit.py allitja elo)
  docs/abrak/*.png  <- outputs/*.png            (a rajzolo szkriptek)

A diagramok SZAMAI kizarolag a mert JSON-bol jonnek, kezzel beirt szam nincs
bennuk - igy ha a meres valtozik, a lap is valtozik, es nem csuszhatnak szet.

Hasznalat:
    python oldal_epit.py
    python oldal_epit.py --oldal docs --stat outputs/hajo_statisztika.json
"""

import argparse
from html import escape
import json
import shutil
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from utak import ADAT, KIMENET, OLDAL, SABLONOK
from abrak_svg import savdiagram, vonaldiagram, tablazat, _ezres

# (forras az outputs/-bol, celutvonal a docs/-on belul)
MASOLANDO = [
    ("terkep.html", "terkep.html"),
    ("forgalmi_profil.png", "abrak/forgalmi_profil.png"),
    ("tomorites_tradeoff.png", "abrak/tomorites_tradeoff.png"),
]

# Az oranként abra sorozatai: (stat-csoportnevek osszevonva, megjelenő nev,
# szin-valtozo). Az elso ot kap sajat szint - ennyi kulonitheto el biztonsagosan
# egymas melletti sorozatokent -, az "egyeb" semleges szurket kap.
MUNKA_SOROZATOK = [
    (["Teherhajó", "Tanker"], "Áruszállítás", "var(--sor-1)"),
    (["Személyszállító"],     "Személyszállító", "var(--sor-2)"),
    (["Szolgálati"],          "Szolgálati",   "var(--sor-3)"),
    (["Halászhajó"],          "Halászhajó",   "var(--sor-4)"),
    (["Egyéb / ismeretlen"],  "Egyéb",        "var(--sor-0)"),
]

# A navigacios statusz angol szabvanyertekei magyarul. Ami nincs a listan,
# az valtozatlanul jelenik meg - nem talalunk ki forditast.
STATUSZ_HU = {
    "Under way using engine": "Géppel úton",
    "Under way sailing": "Vitorlával úton",
    "Moored": "Kikötve",
    "At anchor": "Horgonyon",
    "Engaged in fishing": "Halászik",
    "Restricted maneuverability": "Korlátozott manőverképesség",
    "Constrained by her draught": "Merülése korlátozza",
    "Power-driven vessel towing astern": "Hátul vontat",
    "Power-driven vessel pushing ahead or towing alongside": "Tol vagy oldalt vontat",
    "Not under command": "Kormányképtelen",
    "Aground": "Zátonyon",
    "Reserved for future amendment [HSC]": "(fenntartott kód, HSC)",
    "Reserved for future amendment [WIG]": "(fenntartott kód, WIG)",
    "Reserved for future use": "(fenntartott kód)",
    "(nem jelentett)": "(nem jelentett)",
}

OSZTALY_MAGYARAZAT = {
    "Class A": "kereskedelmi hajók kötelező jeladója",
    "Class B": "kisebb és szabadidős hajók egyszerűsített jeladója",
    "AtoN": "navigációs jelző (bója) – nem hajó",
    "Base Station": "parti bázisállomás – nem hajó",
    "SAR Airborne": "mentőrepülőgép",
    "Search and Rescue Transponder": "mentő-jeladó – nem hajó",
}


def statusz_hu(nev: str) -> str:
    return STATUSZ_HU.get(nev, nev)


def szazalek(resz, egesz) -> str:
    return f"{resz / max(egesz, 1) * 100:.1f}%".replace(".", ",")


def tipus_abrak(stat) -> str:
    """Ket savdiagram egymas mellett: hajoszam es uzenetszam ugyanarra."""
    cs = [c for c in stat["csoportok"] if c["hajo"] or c["uzenet"]]
    hajo_sorrend = sorted(cs, key=lambda c: -c["hajo"])

    bal = savdiagram([(c["nev"], c["hajo"]) for c in hajo_sorrend],
                     szin_var="var(--sor-1)")
    # A jobb oldali panel UGYANABBAN a sorrendben all, hogy a ket abra
    # sorrol sorra osszevetheto legyen - kulonben nem a kulonbseget mutatna.
    jobb = savdiagram([(c["nev"], c["uzenet"]) for c in hajo_sorrend],
                      szin_var="var(--sor-2)")

    tabla = tablazat(
        ["Típus", "Hajó", "Hajó %", "Üzenet", "Üzenet %"],
        [[c["nev"], _ezres(c["hajo"]), szazalek(c["hajo"], stat["hajo_db"]),
          _ezres(c["uzenet"]), szazalek(c["uzenet"], stat["uzenet_db"])]
         for c in hajo_sorrend])

    return (f'<div class="parosabra">'
            f'<div><p class="abra-alcim">Hány hajó</p>{bal}</div>'
            f'<div><p class="abra-alcim">Hány üzenet</p>{jobb}</div>'
            f'</div>{tabla}')


def osztaly_kartyak(stat) -> str:
    ki = []
    for o in stat["osztalyok"]:
        if o["hajo"] < 5:            # az egyedi darabok a tablazatba valok
            continue
        arany = szazalek(o["hajo"], stat["hajo_db"])
        magyarazat = OSZTALY_MAGYARAZAT.get(o["nev"], "")
        stat_arany = szazalek(o["statusszal"], o["hajo"])
        ki.append(
            f'<div class="kartya"><span class="szam">{_ezres(o["hajo"])}</span>'
            f'<span class="cimke"><b>{o["nev"]}</b> ({arany})<br>{magyarazat}<br>'
            f'státuszt jelent: {stat_arany}</span></div>')
    return "\n".join(ki)


def statusz_abra(stat) -> str:
    sorok = [(statusz_hu(s["nev"]), s["hajo"]) for s in stat["class_a_statusz"]]
    svg = savdiagram(sorok, szin_var="var(--sor-3)", szelesseg=820,
                     cimke_szeles=232)
    tabla = tablazat(
        ["Státusz (eredeti)", "Magyarul", "Hajó", "Arány"],
        [[s["nev"], statusz_hu(s["nev"]), _ezres(s["hajo"]),
          szazalek(s["hajo"], stat["class_a_db"])]
         for s in stat["class_a_statusz"]])
    return svg + tabla


def ora_abrak(stat):
    orak = stat["orank"]
    cimkek = [f'{s["ora"]:02d}' for s in orak]

    kedv = [s.get("Kedvtelési", 0) for s in orak]
    kedv_svg = vonaldiagram(
        cimkek, [("Kedvtelési", kedv, "var(--sor-5)")],
        y_cimke="hajó", x_cimke="óra")

    sorozatok = []
    for stat_nevek, nev, szin in MUNKA_SOROZATOK:
        ertekek = [sum(s.get(n, 0) for n in stat_nevek) for s in orak]
        sorozatok.append((nev, ertekek, szin))
    munka_svg = vonaldiagram(cimkek, sorozatok, y_cimke="hajó", x_cimke="óra")

    fejlec = ["Óra", "Összes hajó", "Üzenet", "Kedvtelési"] + \
             [nev for _, nev, _ in MUNKA_SOROZATOK]
    tabla_sorok = []
    for i, s in enumerate(orak):
        tabla_sorok.append(
            [f'{s["ora"]:02d}', _ezres(s["hajo"]), _ezres(s["uzenet"]),
             _ezres(kedv[i])] + [_ezres(sor[1][i]) for sor in sorozatok])
    tabla = tablazat(fejlec, tabla_sorok, cimke="Óránkénti számok táblázatban")

    return kedv_svg, munka_svg + tabla


# --- H3 es kapuvonal szakaszok ------------------------------------------------

H3_NEVEK = {
    "alap": "eredeti (hajó, idő) sorrend",
    "alap_h3": "eredeti sorrend + h3 oszlop",
    "h3_rendezett": "H3 szerint rendezve",
    "ido_rendezett": "idő szerint rendezve",
}
NAP_CIMKE = {
    "2026-07-08": "07-08 szerda (kontroll)",
    "2026-07-09": "07-09 csütörtök (kontroll)",
    "2026-07-15": "07-15 szerda (lezárás)",
    "2026-07-16": "07-16 csütörtök (lezárás)",
    "2026-09-05": "09-05 szombat",
}
LEZARASI = {"2026-07-15", "2026-07-16"}
KERESKEDELMI = {"Teherhajó", "Tanker"}
KIHAGYOTT_ORA = 11


def html_tabla(fejlec, sorok, kiemelt=()):
    fej = "".join(f"<th>{escape(str(c))}</th>" for c in fejlec)
    test = "".join(
        f'<tr{" class=kiemelt" if i in kiemelt else ""}>'
        + "".join(f"<td>{escape(str(c))}</td>" for c in sor) + "</tr>"
        for i, sor in enumerate(sorok))
    return f'<table class="adat-tabla"><thead><tr>{fej}</tr></thead><tbody>{test}</tbody></table>'


def tized(x, jegy=1):
    return f"{x:.{jegy}f}".replace(".", ",")


def elojeles_szazalek(arany):
    v = (arany - 1) * 100
    return ("+" if v >= 0 else "−") + tized(abs(v)) + "%"


def h3_szakasz(tarolas_csv, gorbe_csv):
    t = pd.read_csv(tarolas_csv).set_index("valtozat")
    sorok = []
    for k, nev in H3_NEVEK.items():
        r = t.loc[k]
        sorok.append([nev, tized(r.meret_mib), f"{int(r.ter_atugorhato)} / {int(r.sorcsoport)}",
                      tized(r.terbeli_ms, 0) + " ms", f"{int(r.ido_atugorhato)} / {int(r.sorcsoport)}",
                      tized(r.idobeli_ms, 0) + " ms"])
    tabla = html_tabla(["változat", "MiB", "térbeli: átugorható", "térbeli", "időbeli: átugorható",
                        "időbeli"], sorok, kiemelt=(2, 3))
    gyors = t.loc["alap", "terbeli_ms"] / t.loc["h3_rendezett", "terbeli_ms"]

    g = pd.read_csv(gorbe_csv)
    cimkek = [f"{_ezres(int(round(v)))} km²" for v in g.terulet_km2]
    rg = g.sorcsoport
    sorozatok = [
        ("H3 szerint", list((g.h3_rendezett_olvasott_rg / rg * 100).round(1)), "var(--sor-1)"),
        ("eredeti", list((g.alap_olvasott_rg / rg * 100).round(1)), "var(--sor-0)"),
        ("idő szerint", list((g.ido_rendezett_olvasott_rg / rg * 100).round(1)), "var(--sor-2)"),
    ]
    svg = vonaldiagram(cimkek, sorozatok, y_cimke="%", x_cimke="lekérdezett terület",
                       y_max=100, x_lepes=1)
    reszlet = tablazat(
        ["Terület", "Napi sorok aránya", "Olvasott sorcsoport: H3 / eredeti / idő", "H3-gyorsulás"],
        [[c, tized(r.sor_arany_szazalek, 2) + "%",
          f"{int(r.h3_rendezett_olvasott_rg)} / {int(r.alap_olvasott_rg)} / {int(r.ido_rendezett_olvasott_rg)}",
          tized(r.h3_gyorsulas) + "×"] for c, r in zip(cimkek, g.itertuples())])
    return {
        "<!--H3_TABLA-->": tabla,
        "<!--H3_SORCSOPORT-->": str(int(t.loc["alap", "sorcsoport"])),
        "<!--H3_GYORS-->": tized(gyors),
        "<!--H3_GORBE-->": svg + reszlet,
    }


def kapu_szakasz(atkeles_csv, pw_csv):
    a = pd.read_csv(atkeles_csv)
    a["ora"] = pd.to_datetime(a["ts"]).dt.hour
    k = a[a["csoport"].isin(KERESKEDELMI)]
    pw = pd.read_csv(pw_csv)
    pw = pw[pw["portid"] == "chokepoint10"].set_index("date")

    napok = sorted(k["nap"].unique())
    sorok, mi_o, pw_o, mi_t, pw_t = [], [], [], [], []
    for nap in napok:
        o = k[(k.nap == nap) & (k.kapu == "Øresund")]
        t = int((o.csoport == "Tanker").sum())
        c = int((o.csoport == "Teherhajó").sum())
        pt, po = int(pw.loc[nap, "n_tanker"]), int(pw.loc[nap, "n_total"])
        mi_o.append(t + c); pw_o.append(po); mi_t.append(t); pw_t.append(pt)
        sorok.append([NAP_CIMKE.get(nap, nap), t, c, t + c, pt, po, tized((t + c) / po, 2)])
    pw_tabla = html_tabla(["nap", "saját: tanker", "saját: teher", "saját: össz.",
                           "PortWatch: tanker", "PortWatch: össz.", "arány"], sorok)
    r = np.corrcoef(mi_o, pw_o)[0, 1]
    r_t = np.corrcoef(mi_t, pw_t)[0, 1]
    arany = np.mean(np.array(mi_o) / np.array(pw_o))

    k2 = k[k.ora != KIHAGYOTT_ORA]
    tabla = k2.groupby(["nap", "kapu"]).size().unstack(fill_value=0)
    ossz = tabla.sum(axis=1)
    kiel_sorok, kiemelt = [], []
    for i, nap in enumerate(napok):
        kiel_sorok.append([NAP_CIMKE.get(nap, nap), int(tabla.loc[nap, "Nagy-Balti-öv"]),
                           int(tabla.loc[nap, "Øresund"]), int(ossz[nap])])
        if nap in LEZARASI:
            kiemelt.append(i)
    kiel_tabla = html_tabla(["nap", "Nagy-Balti-öv", "Øresund", "összesen"], kiel_sorok,
                            kiemelt=tuple(kiemelt))
    lez = (ossz["2026-07-15"] + ossz["2026-07-16"]) / (ossz["2026-07-08"] + ossz["2026-07-09"])
    zaj = ossz["2026-07-09"] / ossz["2026-07-08"]
    return {
        "<!--KAPU_PW_TABLA-->": pw_tabla,
        "<!--KAPU_R-->": tized(r, 2),
        "<!--KAPU_R_TANKER-->": tized(r_t, 2),
        "<!--KAPU_ARANY-->": tized(arany, 2),
        "<!--KAPU_KIEL_TABLA-->": kiel_tabla,
        "<!--KAPU_KIEL-->": elojeles_szazalek(lez),
        "<!--KAPU_ZAJ-->": tized((zaj - 1) * 100) + "%",
    }


# --- Napi monitor szakasz -----------------------------------------------------

MONITOR_KEZDET, MONITOR_VEG = "<!--MONITOR_KEZDET-->", "<!--MONITOR_VEG-->"
MONITOR_NAPOK = 30
JELZES_OSZTALY = {"szokatlanul magas": "jelzes-fel", "szokatlanul alacsony": "jelzes-le"}


def monitor_szakasz(mappa: Path) -> str:
    """A "Napi monitor" szakasz HTML-je az outputs/monitor/ fajljaibol.
    A jelolok kozti resz a --csak-monitor modban onalloan cserelheto."""
    allapot_f, jel_f = mappa / "allapot.json", mappa / "jelzesek.csv"
    if not (allapot_f.exists() and jel_f.exists()):
        return f"{MONITOR_KEZDET}<p>A monitor még nem futott.</p>{MONITOR_VEG}"
    a = json.loads(allapot_f.read_text(encoding="utf-8"))
    j = pd.read_csv(jel_f, dtype={"datum": str})
    sorozat_nevek = list(dict.fromkeys(j["sorozat"]))
    utolso = a["utolso_nap"]
    frissitve = a["frissitve_utc"].replace("T", " ").replace("+00:00", "")

    hiba = ""
    if a.get("utolso_futas", {}).get("statusz") not in (None, "ok"):
        f = a["utolso_futas"]
        hiba = (f'<div class="jelzes">A legutóbbi futás ({escape(f.get("ido_utc", "").replace("T", " ").replace("+00:00", ""))} UTC) '
                f'nem frissítette az adatot: {escape(f.get("uzenet", ""))}. Az alábbi számok '
                f'a(z) {utolso} napra vonatkoznak.</div>')

    # utolso nap kartyai
    u = j[j["datum"] == utolso].set_index("sorozat")
    kartyak = []
    for nev in sorozat_nevek:
        r = u.loc[nev]
        if pd.isna(r["alapszint"]):
            al = "alapszint még nincs (kevés korábbi nap)"
        else:
            al = (f"4 hét azonos napja: {tized(r['alapszint'])} · "
                  f"{elojeles_szazalek(1 + r['elteres'])} · {r['jelzes']}")
        kartyak.append(f'<div class="kartya"><span class="szam">{int(r["ertek"])}</span>'
                       f'<span class="cimke"><b>{escape(nev)}</b><br>{al}</span></div>')

    # utolso 30 nap idosora
    napok = sorted(j["datum"].unique())[-MONITOR_NAPOK:]
    szinek = ["var(--sor-1)", "var(--sor-2)", "var(--sor-0)"]
    sorozatok = []
    for nev, szin in zip(sorozat_nevek, szinek):
        s = j[j["sorozat"] == nev].set_index("datum")["ertek"]
        sorozatok.append((nev, [int(s.get(d, 0)) for d in napok], szin))
    svg = vonaldiagram([d[5:] for d in napok], sorozatok, y_cimke="átkelés",
                       x_cimke="nap", x_lepes=5)

    # megrakottsag: 7 napos gordulo osszeg (ha a monitor mar szamolja)
    mj_f = mappa / "jelzesek_megrakottsag.csv"
    mj = pd.read_csv(mj_f, dtype={"datum": str}) if mj_f.exists() else None
    m_doboz = ""
    if mj is not None and len(mj):
        m_napok = [d for d in napok if d in set(mj["datum"])]
        m_sor = []
        for nev, szin in zip(["Megrakott tanker (7 nap)", "Megrakott teherhajó (7 nap)"],
                             ["var(--sor-2)", "var(--sor-1)"]):
            ss = mj[mj["sorozat"] == nev].set_index("datum")["ertek"]
            if len(ss):
                m_sor.append((nev, [int(ss.get(d, 0)) for d in m_napok], szin))
        mk = a.get("kuszob_megrakottsag", {})
        rk = a.get("megrakott_kuszob_relativ_merules", {})
        m_doboz = f"""
<div class="abra-doboz">
  <p class="abra-cim">Megrakott tankerek és teherhajók átkelése, 7 napos gördülő összeg, utolsó {len(m_napok)} nap</p>
  <p class="abra-alcim">Megrakottnak számít az átkelés, ha a hajó jelentett merülése a saját
     (95. percentilis) merülésének legalább {tized(rk.get('Tanker', 0) * 100, 0)}%-a (tanker), illetve
     {tized(rk.get('Teherhajó', 0) * 100, 0)}%-a (teherhajó); a küszöb a relatív merülés
     eloszlásából számolódik. Jelzési küszöb: ±{tized(mk.get('Megrakott tanker (7 nap)', 0) * 100)}% (tanker),
     ±{tized(mk.get('Megrakott teherhajó (7 nap)', 0) * 100)}% (teherhajó).</p>
  {vonaldiagram([d[5:] for d in m_napok], m_sor, y_cimke="átkelés / 7 nap", x_cimke="nap", x_lepes=5)}
</div>"""
        j = pd.concat([j, mj], ignore_index=True)

    # jelzesek az utolso 30 napban (atkelesek es megrakottsag)
    jel = j[j["datum"].isin(napok) & j["jelzes"].str.startswith("szokatlanul")]
    jel_tabla = (html_tabla(
        ["nap", "sorozat", "érték", "alapszint", "eltérés", "jelzés"],
        [[r.datum, r.sorozat, int(r.ertek), tized(r.alapszint), elojeles_szazalek(1 + r.elteres),
          r.jelzes] for r in jel.itertuples()])
        if len(jel) else "<p>Az utolsó 30 napban nem volt jelzés.</p>")

    kuszob = ", ".join(f"{escape(n)}: ±{tized(v * 100)}%" for n, v in a["kuszob"].items())
    return f"""{MONITOR_KEZDET}
<h2 id="monitor">Napi monitor</h2>

<p class="frissites">Utoljára frissítve: <b>{frissitve} UTC</b> · a legutóbbi
feldolgozott nap: <b>{utolso}</b> · idősor: {a['elso_nap']} – {utolso}
({a['napok_szama']} nap)</p>
{hiba}
<p>A lánc naponta, emberi beavatkozás nélkül fut: letölti az előző napok AIS-fájlját,
validálja és Parquet-formátumba alakítja, majd kiszámolja a kereskedelmi
(teherhajó és tanker) kapuvonal-átkeléseket. A dán szolgáltató a napi fájlt kb.
48 órával a nap vége után teszi közzé, ezért a legfrissebb adat 2–3 napos. Minden
napot az előző négy hét azonos napjainak mediánjához mérünk; a jelzési küszöb a
teljes eddigi idősor ingadozásából számolódik (2 × robusztus szórás): {kuszob}.</p>

<div class="racs">{''.join(kartyak)}</div>

<div class="abra-doboz">
  <p class="abra-cim">Kereskedelmi átkelések naponta, utolsó {len(napok)} nap</p>
  {svg}
</div>
{m_doboz}
<div class="abra-doboz">
  <p class="abra-cim">Jelzések az utolsó {len(napok)} napban</p>
  <div class="tabla-gorgeto">{jel_tabla}</div>
</div>
{MONITOR_VEG}"""


def csak_monitor(oldal: Path, mappa: Path) -> int:
    """A kesz docs/index.html-ben csak a monitor-szakaszt csereli ki. A napi
    utemezett futas ezt hivja: igy nem kellenek hozza a tobbi szakasz
    bemenetei (amelyek egy resze nincs a repoban)."""
    f = oldal / "index.html"
    lap = f.read_text(encoding="utf-8")
    k, v = lap.find(MONITOR_KEZDET), lap.find(MONITOR_VEG)
    if k < 0 or v < 0:
        sys.exit(f"A {f} nem tartalmazza a monitor-jeloloket - "
                 f"elobb egy teljes 'python scripts/oldal_epit.py' kell.")
    lap = lap[:k] + monitor_szakasz(mappa) + lap[v + len(MONITOR_VEG):]
    f.write_text(lap, encoding="utf-8")
    print(f"  {f}: a monitor-szakasz frissitve")
    return 0


def main():
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--csak-monitor", action="store_true",
                    help="Csak a 'Napi monitor' szakaszt frissiti a meglevo index.html-ben")
    ap.add_argument("--monitor", default=KIMENET / "monitor")
    ap.add_argument("--kimenet", default=KIMENET,
                    help="A generalt fajlok forrasa (alap: outputs/)")
    ap.add_argument("--oldal", default=OLDAL,
                    help="Az oldal celmappaja (alap: docs/)")
    ap.add_argument("--sablon", default=SABLONOK / "oldal_sablon.html")
    ap.add_argument("--stat", default=KIMENET / "hajo_statisztika.json")
    args = ap.parse_args()

    if args.csak_monitor:
        return csak_monitor(Path(args.oldal), Path(args.monitor))

    forras = Path(args.kimenet)
    cel = Path(args.oldal)
    sablon_fajl = Path(args.sablon)
    stat_fajl = Path(args.stat)

    for f, mi in [(sablon_fajl, "a lap sablonja"), (stat_fajl, "a statisztika")]:
        if not f.exists():
            sys.exit(f"Hianyzik {mi}: {f}\n"
                     f"Futtasd le eloszor: python scripts/hajo_statisztika.py <zip>")

    stat = json.loads(stat_fajl.read_text(encoding="utf-8"))
    print(f"Statisztika: {stat_fajl.name} "
          f"({stat['nap']}, {stat['hajo_db']:,} hajo)")

    kedv = next((c for c in stat["csoportok"] if c["nev"] == "Kedvtelési"),
                {"hajo": 0, "uzenet": 0})
    aru = sum(c["hajo"] for c in stat["csoportok"]
              if c["nev"] in ("Teherhajó", "Tanker"))
    ora_hajo = [s["hajo"] for s in stat["orank"]]
    ingadozas = max(ora_hajo) / max(min(ora_hajo), 1)

    kedv_svg, munka_svg = ora_abrak(stat)

    csere = {
        "<!--NAP-->": stat["nap"],
        "<!--HAJO_DB-->": _ezres(stat["hajo_db"]),
        "<!--TIPUS_SAVOK-->": tipus_abrak(stat),
        "<!--KEDV_HAJO_SZAZ-->": szazalek(kedv["hajo"], stat["hajo_db"]),
        "<!--KEDV_UZENET_SZAZ-->": szazalek(kedv["uzenet"], stat["uzenet_db"]),
        "<!--OSZTALY_KARTYAK-->": osztaly_kartyak(stat),
        "<!--CLASS_A_DB-->": _ezres(stat["class_a_db"]),
        "<!--STATUSZ_SAVOK-->": statusz_abra(stat),
        "<!--NAPI_INGADOZAS-->": f"{ingadozas:.2f}".replace(".", ","),
        "<!--ORA_KEDV-->": kedv_svg,
        "<!--ORA_MUNKA-->": munka_svg,
        "<!--ARU_DB-->": _ezres(aru),
        "<!--NEM_HAJO_DB-->": _ezres(stat["nem_hajo_db"]),
        **h3_szakasz(KIMENET / "h3_tarolas.csv", KIMENET / "h3_teruletmeret.csv"),
        **kapu_szakasz(KIMENET / "kapuvonal_atkelesek.csv",
                       ADAT / "portwatch_chokepoints.csv"),
        "<!--MONITOR-->": monitor_szakasz(Path(args.monitor)),
    }

    lap = sablon_fajl.read_text(encoding="utf-8")
    hianyzo_helyorzo = [k for k in csere if k not in lap]
    if hianyzo_helyorzo:
        sys.exit("A sablonban nincs meg ez a helyorzo: "
                 + ", ".join(hianyzo_helyorzo))
    for kulcs, ertek in csere.items():
        lap = lap.replace(kulcs, ertek)

    maradek = [k for k in csere if k in lap]
    if maradek:
        sys.exit(f"Kicsereletlen helyorzo maradt: {maradek}")

    cel.mkdir(parents=True, exist_ok=True)
    (cel / "index.html").write_text(lap, encoding="utf-8")
    print(f"  index.html generalva ({len(lap)/1024:.0f} KB, "
          f"{len(csere)} helyorzo cserelve)")

    masolva, hianyzo, osszes_bajt = 0, [], 0
    for honnan, hova in MASOLANDO:
        f = forras / honnan
        c = cel / hova
        if not f.exists():
            hianyzo.append(honnan)
            continue
        c.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(f, c)
        osszes_bajt += c.stat().st_size
        masolva += 1
        print(f"  {honnan:<28} -> {hova:<32} {c.stat().st_size/1024:>8,.0f} KB")

    print(f"\n  {masolva} fajl masolva, osszesen {osszes_bajt/1_048_576:.1f} MB")

    if hianyzo:
        print(f"\n  FIGYELEM - {len(hianyzo)} forrasfajl hianyzik, "
              f"az oldalon torott hivatkozas lesz:")
        for h in hianyzo:
            print(f"    {h}")
        print("  Futtasd le eloszor az ezeket eloallito szkripteket "
              "(ld. README.md).")

    print(f"\n-> {cel} kesz. Helyi ellenorzes:")
    print(f"     python -m http.server 8000 --directory {cel}")

    return 1 if hianyzo else 0


if __name__ == "__main__":
    sys.exit(main())
