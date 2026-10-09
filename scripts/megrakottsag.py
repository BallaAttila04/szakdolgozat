"""
Megrakottsagi mutato: mennyire vannak megrakva a kapuvonalon atkelo tankerek
es teherhajok (7. fazis).

Az AIS `Draught` mezo a hajo aktualis merulese (m), amelyet a szemelyzet
kezzel allit be. Egy hajo merulese megrakva nagyobb, uresen kisebb, ezert a
hajo SAJAT maximalis merulesehez viszonyitott relativ merules jelzi a
rakottsagot:

    max_merules(MMSI) = a hajo hiheto napi meruleseinek 95. percentilise
    relativ merules   = az atkelesnel jelentett merules / max_merules
    megrakott         = relativ merules >= kuszob (Otsu-modszer, csoportonkent)

A 95. percentilis es nem a maximum: egyetlen elutott (pl. 15,0 helyett 5,0)
napi ertek ne legyen a hajo "maximuma". Kevesebb mint 20 napnal a percentilis
a ket legnagyobb ertek koze interpolal, igy a vedelem reszleges (ld. naplo).

Relativ merules csak olyan hajonal ertelmes, amelynek a merulese a megfigyelt
idoszakban valtozott (legalabb ket kulonbozo hiheto napi ertek): ha mindig
ugyanazt jelenti, a relativ merules konstrukcio szerint 1, es a hajo nem ad
informaciot (vagy nem frissitik a mezot, vagy csak egyszer lattuk).

Allomanyok (outputs/monitor/, kicsik, gitbe mehetnek):
  merules_tortenet.csv      hajonkent, naponkent a hiheto merules mediánja
                            (csak tanker es teherhajo), a max_merules alapja
  atkelesek_reszletes.csv   atkelesenkent: datum, kapu, irany, csoport, MMSI,
                            merules, hossz, szelesseg
  megrakottsag_napi.csv     naponkent, kapunkent, iranyonkent, csoportonkent:
                            atkeles, ertekelheto, megrakott, megrakott_arany,
                            volumenindex (Σ hossz × szelesseg × merules, m³)

Hasznalat (a napi frissitest a monitor.py hivja):
    python megrakottsag.py --lefedettseg     # 7a: merulesadat-lefedettseg
    python megrakottsag.py --szamol          # 7b: kuszob, napi tabla, abra
    python megrakottsag.py --teszt           # 7c: teves riasztas, mesterseges csokkenes
"""

import argparse
import json
import sys
from datetime import date, timedelta
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd

from utak import KIMENET
from hajo_statisztika import URES, csoport

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)
except AttributeError:
    pass

# --- Parameterek ----------------------------------------------------------

MONITOR = KIMENET / "monitor"
TORTENET = MONITOR / "merules_tortenet.csv"
RESZLETES = MONITOR / "atkelesek_reszletes.csv"
NAPI = MONITOR / "megrakottsag_napi.csv"
PARAM = MONITOR / "megrakottsag_param.json"
ABRA = KIMENET / "megrakottsag_hisztogram.png"

CSOPORTOK = ["Tanker", "Teherhajó"]

# Hiheto merules (m). Az ITU-R M.1371 szerint a mezo 0,1 m-es lepesu, a 0 azt
# jelenti, hogy "nincs adat", a 25,5 pedig "25,5 m vagy tobb" - ez utobbi
# tehat nem pontos ertek. Az also korlatot az adat eloszlasabol valasztottuk
# (jun. 1 - okt. 6., minden sor, ld. naplo 7a): az 1 m alatti sav gyakorlatilag
# ures (tanker: 1 343 sor a 208,7 millióbol, teher: 0,014%), ami hibas
# kitoltesre utal; az 1-2 m ritka (0,05% / 0,38%), de kis hajonal lehetseges,
# ezert benne marad. A hianyzo merules ures mezokent erkezik, a 0 nem fordul elo.
HIHETO_MIN = 1.0
HIHETO_MAX = 25.5          # kizarolag: a 25,5 a mezo telitett erteke

MAX_PERCENTILIS = 95
MIN_ERTEKEK = 2            # ennyi kulonbozo napi ertek kell a "valtozo" hajohoz
KEREKITES = 1              # tizedes: a mezo felbontasa 0,1 m

# A gordulo ablak a monitor jelzesehez: a napi megrakott-szam kicsi es zajos
GORDULO_NAP = 7


def hiheto(d):
    return (d >= HIHETO_MIN) & (d < HIHETO_MAX)


# --- Napi adatgyujtes (a monitor.py hivja, amig a napi Parquet megvan) --------

def napi_hajoadat(pq: Path) -> pd.DataFrame:
    """Hajonkent: tipus (leggyakoribb ervenyes Ship type, dup_db-vel sulyozva),
    a nap hiheto meruleseinek mediánja, hossz, szelesseg. Csak tanker/teher."""
    f = Path(pq).as_posix()
    ures = ", ".join("'" + u.replace("'", "''") + "'" for u in URES)
    con = duckdb.connect()
    con.execute("SET enable_progress_bar = false")
    df = con.execute(f"""
        WITH t AS (
          SELECT MMSI, "Ship type" st, sum(dup_db) n FROM read_parquet('{f}')
          WHERE "Ship type" IS NOT NULL AND upper(trim("Ship type")) NOT IN ({ures})
          GROUP BY 1, 2),
        tip AS (SELECT MMSI, arg_max(st, n) tipus FROM t GROUP BY 1)
        SELECT p.MMSI, tip.tipus,
               median(Draught) FILTER (WHERE Draught >= {HIHETO_MIN} AND Draught < {HIHETO_MAX}) merules,
               median(Length) FILTER (WHERE Length > 0) hossz,
               median(Width) FILTER (WHERE Width > 0) szelesseg
        FROM read_parquet('{f}') p JOIN tip USING (MMSI)
        GROUP BY 1, 2""").df()
    con.close()
    df["csoport"] = df["tipus"].map(csoport)
    df = df[df["csoport"].isin(CSOPORTOK)].drop(columns="tipus")
    df["merules"] = df["merules"].round(KEREKITES)
    return df


def napi_frissites(nap: str, pq: Path, atk: pd.DataFrame, ki: Path = MONITOR):
    """Egy nap hozzaadasa a tortenethez es a reszletes atkeles-tablahoz
    (idempotens: a nap korabbi sorait lecsereli)."""
    h = napi_hajoadat(pq)
    tort = h.dropna(subset=["merules"])[["MMSI", "merules"]].assign(nap=nap)
    _hozzafuz(ki / TORTENET.name, tort[["nap", "MMSI", "merules"]], "nap", nap)

    a = atk[atk["csoport"].isin(CSOPORTOK)].copy() if not atk.empty else atk
    if a is not None and not a.empty:
        a = a.merge(h[["MMSI", "merules", "hossz", "szelesseg"]], on="MMSI", how="left",
                    suffixes=("", "_nap"))
        # Az atkelesnel jelentett merules: a kapufolyosoban mert median, ha
        # hiheto; kulonben a hajo aznapi mediánja.
        kapu_m = pd.to_numeric(a["merules_m"], errors="coerce")
        a["merules"] = np.where(hiheto(kapu_m), kapu_m, a["merules"]).round(KEREKITES)
        a["datum"] = nap
        a = a[["datum", "kapu", "irany", "csoport", "MMSI", "merules", "hossz", "szelesseg"]]
    else:
        a = pd.DataFrame(columns=["datum", "kapu", "irany", "csoport", "MMSI",
                                  "merules", "hossz", "szelesseg"])
    _hozzafuz(ki / RESZLETES.name, a, "datum", nap)


def _hozzafuz(ut: Path, uj: pd.DataFrame, kulcs: str, ertek: str):
    regi = pd.read_csv(ut, dtype={kulcs: str}) if ut.exists() else uj.iloc[0:0]
    t = pd.concat([regi[regi[kulcs] != ertek], uj], ignore_index=True)
    t = t.sort_values(list(t.columns[:2])).reset_index(drop=True)
    tmp = ut.with_suffix(".tmp")
    t.to_csv(tmp, index=False, encoding="utf-8")
    tmp.replace(ut)


# --- Szamitas -------------------------------------------------------------------

def hajo_max(tort: pd.DataFrame) -> pd.DataFrame:
    """Hajonkent: max_merules (P95), kulonbozo napi ertekek szama, napok."""
    g = tort.groupby("MMSI")["merules"]
    return pd.DataFrame({
        "max_merules": g.quantile(MAX_PERCENTILIS / 100),
        "kulonbozo": g.nunique(),
        "napok": g.size(),
    }).reset_index()


def otsu(x, binek=100):
    """Otsu-kuszob: az osztalyon beluli szorast minimalizalo vagas (a
    hisztogram ket pupja kozotti volgy, kezi valasztas nelkul)."""
    x = np.asarray(x, dtype=float)
    hist, el = np.histogram(x, bins=binek)
    kozep = (el[:-1] + el[1:]) / 2
    w0 = np.cumsum(hist)
    w1 = w0[-1] - w0
    m0 = np.cumsum(hist * kozep) / np.maximum(w0, 1)
    m1 = (np.sum(hist * kozep) - np.cumsum(hist * kozep)) / np.maximum(w1, 1)
    kozti = w0 * w1 * (m0 - m1) ** 2
    i = int(np.argmax(kozti[:-1]))
    return float(el[i + 1])


def relativ(resz: pd.DataFrame, hm: pd.DataFrame) -> pd.DataFrame:
    r = resz.merge(hm, on="MMSI", how="left")
    r["hiheto"] = hiheto(r["merules"])
    r["valtozo"] = r["kulonbozo"].fillna(0) >= MIN_ERTEKEK
    r["ertekelheto"] = r["hiheto"] & r["valtozo"]
    r["rel"] = np.where(r["ertekelheto"], r["merules"] / r["max_merules"], np.nan)
    return r


def kuszobok(r: pd.DataFrame) -> dict:
    return {cs: otsu(r.loc[(r.csoport == cs) & r.ertekelheto, "rel"].clip(upper=1.2))
            for cs in CSOPORTOK}


def napi_tabla(r: pd.DataFrame, kusz: dict) -> pd.DataFrame:
    r = r.copy()
    r["megrakott"] = r["ertekelheto"] & (r["rel"] >= r["csoport"].map(kusz))
    r["volumen"] = np.where(hiheto(r["merules"]), r["hossz"] * r["szelesseg"] * r["merules"], np.nan)
    g = r.groupby(["datum", "kapu", "irany", "csoport"])
    t = pd.DataFrame({
        "atkeles": g.size(),
        "ertekelheto": g["ertekelheto"].sum(),
        "megrakott": g["megrakott"].sum(),
        "volumenindex": g["volumen"].sum(min_count=1).round(0),
    }).reset_index()
    t["megrakott_arany"] = (t["megrakott"] / t["ertekelheto"].replace(0, np.nan)).round(4)
    for c in ("ertekelheto", "megrakott"):
        t[c] = t[c].astype(int)
    return t


def szamol(ki: Path = MONITOR, abra: Path = None):
    tort = pd.read_csv(ki / TORTENET.name, dtype={"nap": str})
    resz = pd.read_csv(ki / RESZLETES.name, dtype={"datum": str})
    hm = hajo_max(tort)
    r = relativ(resz, hm)
    kusz = kuszobok(r)
    t = napi_tabla(r, kusz)
    tmp = (ki / NAPI.name).with_suffix(".tmp")
    t.to_csv(tmp, index=False, encoding="utf-8")
    tmp.replace(ki / NAPI.name)
    (ki / PARAM.name).write_text(json.dumps({
        "kuszob": {k: round(v, 4) for k, v in kusz.items()},
        "max_percentilis": MAX_PERCENTILIS, "hiheto": [HIHETO_MIN, HIHETO_MAX],
        "min_kulonbozo_ertek": MIN_ERTEKEK, "elso_nap": t["datum"].min(),
        "utolso_nap": t["datum"].max()}, ensure_ascii=False, indent=1), encoding="utf-8")
    if abra:
        hisztogram(r, kusz, abra)
    return r, kusz, t


def hisztogram(r, kusz, ut):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, axs = plt.subplots(1, 2, figsize=(10, 4), sharey=False)
    for ax, cs in zip(axs, CSOPORTOK):
        x = r.loc[(r.csoport == cs) & r.ertekelheto, "rel"].clip(upper=1.2)
        ax.hist(x, bins=48, range=(0.3, 1.2), color="#4C78A8")
        ax.axvline(kusz[cs], color="#E45756", linestyle="--",
                   label=f"küszöb (Otsu): {kusz[cs]:.2f}")
        ax.set_title(f"{cs} – {len(x):,} értékelhető átkelés".replace(",", " "))
        ax.set_xlabel("relatív merülés (merülés / a hajó P95 merülése)")
        ax.set_ylabel("átkelés")
        ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(ut, dpi=150)


# --- Monitor-sorozatok (7 napos gordulo ablak) --------------------------------

def gordulo_sorozatok(t: pd.DataFrame, napok) -> pd.DataFrame:
    """Naponkent a 7 napos gordulo osszeg: megrakott tanker / teher atkeles
    es tanker-volumenindex, mindket kapu, mindket irany egyutt.

    `napok`: a feldolgozott (adattal rendelkezo) napok. A naptari tartomany
    tobbi napja "nincs adat" (NaN), nem nulla: az ilyen napot tartalmazo
    7 napos ablakra nincs ertek, igy jelzes sem (ld. naplo, 7c: a 09-01 -
    09-04 hiany nullakent hamis "alacsony" jelzest adott volna)."""
    adatos = set(napok)
    idx = pd.date_range(min(napok), max(napok)).strftime("%Y-%m-%d").tolist()
    ki = {}
    for nev, cs, oszlop in [("Megrakott tanker (7 nap)", "Tanker", "megrakott"),
                            ("Megrakott teherhajó (7 nap)", "Teherhajó", "megrakott"),
                            ("Tanker-volumen (7 nap, 1000 m³)", "Tanker", "volumenindex")]:
        s = t[t.csoport == cs].groupby("datum")[oszlop].sum().reindex(idx, fill_value=0)
        s[[d not in adatos for d in idx]] = np.nan
        if oszlop == "volumenindex":
            s = s / 1000
        g = s.rolling(GORDULO_NAP, min_periods=GORDULO_NAP).sum()
        ki[nev] = g
    s = pd.DataFrame(ki).dropna()
    return s.round(0).astype(int)


# --- 7a: lefedettseg -------------------------------------------------------------

def lefedettseg(ki: Path = MONITOR):
    tort = pd.read_csv(ki / TORTENET.name, dtype={"nap": str})
    resz = pd.read_csv(ki / RESZLETES.name, dtype={"datum": str})
    hm = hajo_max(tort)
    r = relativ(resz, hm)
    r["van"] = pd.to_numeric(r["merules"], errors="coerce").notna()
    sorok = []
    for (kapu, cs), g in r.groupby(["kapu", "csoport"]):
        sorok.append({"kapu": kapu, "csoport": cs, "atkeles": len(g),
                      "van_merules_%": round(100 * g["van"].mean(), 1),
                      "hiheto_%": round(100 * g["hiheto"].mean(), 1),
                      "hiheto_es_valtozo_%": round(100 * g["ertekelheto"].mean(), 1)})
    for cs, g in r.groupby("csoport"):
        sorok.append({"kapu": "Mindkét kapu", "csoport": cs, "atkeles": len(g),
                      "van_merules_%": round(100 * g["van"].mean(), 1),
                      "hiheto_%": round(100 * g["hiheto"].mean(), 1),
                      "hiheto_es_valtozo_%": round(100 * g["ertekelheto"].mean(), 1)})
    lef = pd.DataFrame(sorok)
    # hajoszinten: a kapun atkelo hajok kozul hanynak valtozik a merulese
    hajok = resz[["MMSI", "csoport"]].drop_duplicates().merge(hm, on="MMSI", how="left")
    hajok["valtozo"] = hajok["kulonbozo"].fillna(0) >= MIN_ERTEKEK
    hajo = hajok.groupby("csoport").agg(hajo=("MMSI", "nunique"),
                                        valtozo=("valtozo", "sum"),
                                        median_napok=("napok", "median")).reset_index()
    hajo["valtozo_%"] = (100 * hajo["valtozo"] / hajo["hajo"]).round(1)
    return lef, hajo, r


# --- 7c: teszt ---------------------------------------------------------------------

def teves_riasztasok(j: pd.DataFrame, sorozatok) -> pd.DataFrame:
    v = j[j.sorozat.isin(sorozatok) & (j.jelzes != "nincs alapszint")].copy()
    v["honap"] = v["datum"].str[:7]
    return (v.assign(jelzett=v.jelzes.str.startswith("szokatlanul"))
             .groupby(["sorozat", "honap"])
             .agg(napok=("datum", "size"), jelzett=("jelzett", "sum")).reset_index())


def mesterseges_csokkenes(r, kusz, napok, het_kezdet, arany, kuszob_fix, seed=0):
    """A teszt-masolaton a megadott het megrakott tankereinek `arany`-at
    uresse teszi; visszaadja, hanyadik napon (0 = a het elso napja) jelez
    elsonek a "Megrakott tanker (7 nap)" sorozat, vagy None."""
    from monitor import jelzesek
    rng = np.random.default_rng(seed)
    t = napi_tabla(r, kusz)
    r2 = r.copy()
    r2["megrakott0"] = r2["ertekelheto"] & (r2["rel"] >= r2["csoport"].map(kusz))
    het = [(date.fromisoformat(het_kezdet) + timedelta(days=i)).isoformat() for i in range(7)]
    jelolt = r2.index[(r2.csoport == "Tanker") & r2.megrakott0 & r2.datum.isin(het)]
    uritendo = rng.choice(jelolt, size=int(round(arany * len(jelolt))), replace=False)
    # "ures": a relativ merules a kuszob ala kerul (a hajo uresen kelt at)
    r2.loc[uritendo, "rel"] = kusz["Tanker"] * 0.8
    t2 = napi_tabla(r2.drop(columns="megrakott0"), kusz)
    s1 = gordulo_sorozatok(t, napok)[["Megrakott tanker (7 nap)"]]
    s2 = gordulo_sorozatok(t2, napok)[["Megrakott tanker (7 nap)"]]
    j1, _, _ = jelzesek(s1)
    j2, _, _ = jelzesek(s2)
    # a kuszob a modositatlan adatbol szamolt (a monitor ezt ismerte volna);
    # csak az a nap szamit eszlelesnek, amelyen az eredeti adat NEM jelzett
    # alacsonyat (kulonben egy mar meglevo teves riasztast szamolnank)
    eredeti = set(j1.loc[j1["elteres"] < -kuszob_fix, "datum"])
    j2["jelez"] = (j2["elteres"] < -kuszob_fix) & ~j2["datum"].isin(eredeti)
    for i, d in enumerate(het + [(date.fromisoformat(het[-1]) + timedelta(days=k)).isoformat()
                                 for k in range(1, 8)]):
        sor = j2[j2.datum == d]
        if len(sor) and bool(sor["jelez"].iloc[0]):
            return i, len(jelolt), len(uritendo)
    return None, len(jelolt), len(uritendo)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--ki", type=Path, default=MONITOR)
    ap.add_argument("--lefedettseg", action="store_true")
    ap.add_argument("--szamol", action="store_true")
    ap.add_argument("--teszt", action="store_true")
    ap.add_argument("--abra", type=Path, default=ABRA)
    args = ap.parse_args()

    if args.lefedettseg:
        lef, hajo, _ = lefedettseg(args.ki)
        print("Atkelesek merulesadata kapunkent es csoportonkent:")
        print(lef.to_string(index=False))
        print("\nA kapun atkelo hajok, amelyeknek a merulese valtozik "
              f"(>= {MIN_ERTEKEK} kulonbozo hiheto napi ertek):")
        print(hajo.to_string(index=False))
        lef.to_csv(KIMENET / "megrakottsag_lefedettseg.csv", index=False, encoding="utf-8")

    if args.szamol:
        r, kusz, t = szamol(args.ki, args.abra)
        print(f"Kuszob (Otsu): " + ", ".join(f"{k} {v:.3f}" for k, v in kusz.items()))
        print(f"-> {args.ki / NAPI.name} ({len(t)} sor), {args.abra}")

    if args.teszt:
        from monitor import jelzesek
        tort = pd.read_csv(args.ki / TORTENET.name, dtype={"nap": str})
        resz = pd.read_csv(args.ki / RESZLETES.name, dtype={"datum": str})
        r = relativ(resz, hajo_max(tort))
        kusz = kuszobok(r)
        napok = sorted(resz["datum"].unique())
        t = napi_tabla(r, kusz)
        s = gordulo_sorozatok(t, napok)
        j, kuszob, _ = jelzesek(s)
        tr = teves_riasztasok(j, list(s.columns))
        print("Teves riasztasok havonta (a teljes idoszak 'normal' adatnak tekintve):")
        print(tr.to_string(index=False))
        tr.to_csv(KIMENET / "megrakottsag_teves_riasztas.csv", index=False, encoding="utf-8")
        print("Kuszobok:", {k: round(v, 3) for k, v in kuszob.items()})

        kfix = kuszob["Megrakott tanker (7 nap)"]
        alapos = [d for d in napok
                  if d in set(j[(j.sorozat == "Megrakott tanker (7 nap)")
                                & (j.jelzes != "nincs alapszint")].datum)]
        # hetfotol kezdodo hetek, amelyek elso napjan mar van alapszint, es
        # utana meg 14 nap adat van a kesleltetes meresehez
        hetek = [d for d in alapos if date.fromisoformat(d).weekday() == 0
                 and (date.fromisoformat(d) + timedelta(days=13)).isoformat() <= napok[-1]]
        sorok = []
        for arany in (0.4, 0.3, 0.2):
            for h in hetek:
                k, n, u = mesterseges_csokkenes(r, kusz, napok, h, arany, kfix)
                sorok.append({"arany": arany, "het": h, "megrakott_tanker": n, "uritve": u,
                              "jelzes_napja": k})
        ts = pd.DataFrame(sorok)
        ts.to_csv(KIMENET / "megrakottsag_csokkenes_teszt.csv", index=False, encoding="utf-8")
        print("\nMesterseges csokkenes (0 = a het elso napja; ures = 14 napon belul nem jelez):")
        print(ts.to_string(index=False))
        osz = ts.groupby("arany").agg(hetek=("het", "size"),
                                      eszlelt=("jelzes_napja", lambda x: x.notna().sum()),
                                      median_nap=("jelzes_napja", "median")).reset_index()
        print(osz.to_string(index=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
