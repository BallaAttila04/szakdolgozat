"""
Napi forgalmi monitor: kapuvonal-atkelesek naponkent, alapszint es jelzes.

A pipeline.py utan fut. Minden validalt naprol (a Parquet-tarolobol) a
kapuvonal.py logikajaval kiszamolja az atkeleseket, es egy kis, gitben
tarolhato tablaba fuzi:

  outputs/monitor/kapuvonal_napi.csv   datum, kapu, irany, csoport, atkeles
  outputs/monitor/jelzesek.csv         naponkent, sorozatonkent: ertek,
                                       alapszint, elteres, kuszob, jelzes
  outputs/monitor/allapot.json         utolso nap, frissites ideje, kuszobok

A nyers es a napi Parquet NEM kerul a repoba, csak ez a harom fajl.

Alapszint: az elozo 4 het azonos hetnapjanak (d-7, d-14, d-21, d-28)
mediánja; legalabb MIN_ALAPNAP ilyen nap kell, kulonben nincs jelzes.
Jelzes: |ertek / alapszint - 1| > kuszob. A kuszobot nem irjuk be kezzel:
a teljes eddigi idosor relativ elteresenek robusztus szorasabol szamoljuk
(KUSZOB_SZORZO x 1,4826 x MAD), sorozatonkent kulon.

A figyelt sorozatok a kereskedelmi (teherhajo + tanker) atkelesek kapunkent
es a ket kapu osszesen - a szabadidos hajozas a csatornalezarasra
erzeketlen (ld. szamok.md, "Napszaki ingadozas").

Hasznalat:
    python monitor.py                      # minden uj validalt nap
    python monitor.py --felulir            # az egesz tabla ujraszamolasa
    python monitor.py --napok 2026-07-15 2026-07-16
"""

import argparse
import csv
import json
import os
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from utak import KIMENET
from kapuvonal import KAPUK, feldolgoz, folyoso
from pipeline import NAPLO_CSV, SEMA, TAROLO, parquet_ut
import megrakottsag

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)
except AttributeError:
    pass

# --- Parameterek ----------------------------------------------------------

MONITOR = KIMENET / "monitor"
KERESKEDELMI = ["Teherhajó", "Tanker"]
OSSZES = "Mindkét kapu"

ALAP_HETEK = 4         # az elozo 4 het azonos hetnapja (a feladatleiras szerint)
MIN_ALAPNAP = 3        # 4-bol legalabb 3 meglevo nap kell az alapszinthez
# 2 x robusztus szoras: normalis eloszlasnal a napok ~95%-a ezen belul esik,
# vagyis rendes ingadozas mellett kb. 20 naponta 1 teves jelzes sorozatonkent.
KUSZOB_SZORZO = 2.0
MAD_SKALA = 1.4826     # MAD -> szoras normalis eloszlasnal


def napi_aggregatum(nap: date, tarolo: Path, folyosok, ki: Path = MONITOR) -> pd.DataFrame:
    pq = parquet_ut(tarolo, nap)
    atk, _ = feldolgoz(pq, folyosok)
    # a megrakottsagi mutatohoz: merules-tortenet es reszletes atkelesek,
    # amig a napi Parquet meg megvan (a futtaton utana torlodik)
    megrakottsag.napi_frissites(nap.isoformat(), pq, atk, ki)
    if atk.empty:
        return pd.DataFrame(columns=["datum", "kapu", "irany", "csoport", "atkeles"])
    g = atk.groupby(["kapu", "irany", "csoport"]).size().reset_index(name="atkeles")
    g.insert(0, "datum", nap.isoformat())
    return g


def sorozatok(tabla: pd.DataFrame) -> pd.DataFrame:
    """Naponkent a figyelt sorozatok erteke (datum x sorozat)."""
    k = tabla[tabla["csoport"].isin(KERESKEDELMI)]
    s = k.pivot_table(index="datum", columns="kapu", values="atkeles",
                      aggfunc="sum", fill_value=0)
    for kapu in KAPUK:
        if kapu not in s:
            s[kapu] = 0
    s = s.reindex(sorted(tabla["datum"].unique()), fill_value=0)
    s[OSSZES] = s[list(KAPUK)].sum(axis=1)
    return s[list(KAPUK) + [OSSZES]]


def jelzesek(s: pd.DataFrame):
    """Alapszint, relativ elteres, adatbol szamolt kuszob, jelzes."""
    idx = {date.fromisoformat(d): d for d in s.index}
    sorok = []
    for nev in s.columns:
        for d, dstr in idx.items():
            alap = [s.at[idx[d - timedelta(weeks=w)], nev]
                    for w in range(1, ALAP_HETEK + 1) if d - timedelta(weeks=w) in idx]
            ertek = int(s.at[dstr, nev])
            sor = {"datum": dstr, "sorozat": nev, "ertek": ertek,
                   "alapnapok": len(alap), "alapszint": "", "elteres": ""}
            if len(alap) >= MIN_ALAPNAP and np.median(alap) > 0:
                m = float(np.median(alap))
                sor["alapszint"] = m
                sor["elteres"] = ertek / m - 1
            sorok.append(sor)
    j = pd.DataFrame(sorok)

    kuszob, zaj = {}, {}
    for nev, g in j[j["elteres"] != ""].groupby("sorozat"):
        e = g["elteres"].astype(float).to_numpy()
        mad = float(np.median(np.abs(e - np.median(e))))
        kuszob[nev] = KUSZOB_SZORZO * MAD_SKALA * mad
        zaj[nev] = {"napok": len(e), "median_abs_elteres": float(np.median(np.abs(e))),
                    "robusztus_szoras": MAD_SKALA * mad,
                    "p90_abs_elteres": float(np.percentile(np.abs(e), 90))}

    def minosit(r):
        if r["elteres"] == "" or r["sorozat"] not in kuszob:
            return "nincs alapszint"
        if r["elteres"] > kuszob[r["sorozat"]]:
            return "szokatlanul magas"
        if r["elteres"] < -kuszob[r["sorozat"]]:
            return "szokatlanul alacsony"
        return "normál"
    j["kuszob"] = j["sorozat"].map(kuszob)
    j["jelzes"] = j.apply(minosit, axis=1)
    for c in ("alapszint", "elteres", "kuszob"):
        j[c] = pd.to_numeric(j[c], errors="coerce").round(4)
    return j, kuszob, zaj


def atomi_csv(df: pd.DataFrame, ut: Path):
    tmp = ut.with_suffix(".tmp")
    df.to_csv(tmp, index=False, encoding="utf-8")
    os.replace(tmp, ut)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--tarolo", type=Path, default=TAROLO)
    ap.add_argument("--pipeline-naplo", type=Path, default=NAPLO_CSV)
    ap.add_argument("--ki", type=Path, default=MONITOR)
    ap.add_argument("--napok", nargs="*", help="Csak ezek a napok (YYYY-MM-DD)")
    ap.add_argument("--felulir", action="store_true",
                    help="A mar a tablaban levo napokat is ujraszamolja")
    args = ap.parse_args()
    args.ki.mkdir(parents=True, exist_ok=True)
    tabla_ut = args.ki / "kapuvonal_napi.csv"

    tabla = (pd.read_csv(tabla_ut, dtype={"datum": str}) if tabla_ut.exists()
             else pd.DataFrame(columns=["datum", "kapu", "irany", "csoport", "atkeles"]))
    meglevo = set(tabla["datum"])

    # Csak validalt nap kerulhet be: ha a pipeline aznap hibas volt, a tabla
    # (es igy az oldal) a korabbi jo allapoton marad.
    with args.pipeline_naplo.open(encoding="utf-8") as fh:
        validalt = {s["nap"] for s in csv.DictReader(fh)
                    if s["statusz"] == "validalt" and str(s.get("sema")) == str(SEMA)}
    jeloltek = sorted(args.napok) if args.napok else sorted(validalt)
    uj = [d for d in jeloltek if d in validalt
          and parquet_ut(args.tarolo, date.fromisoformat(d)).exists()
          and (args.felulir or d not in meglevo)]
    kimaradt = [d for d in (args.napok or []) if d not in validalt]
    print(f"Monitor: {len(meglevo)} nap mar a tablaban, {len(uj)} uj/ujraszamolando"
          + (f"; NEM validalt, kihagyva: {', '.join(kimaradt)}" if kimaradt else ""))

    if uj:
        folyosok = {n: folyoso(*v) for n, v in KAPUK.items()}
        uj_sorok = []
        for d in uj:
            print(f"\n{d}:")
            uj_sorok.append(napi_aggregatum(date.fromisoformat(d), args.tarolo, folyosok, args.ki))
        tabla = pd.concat([tabla[~tabla["datum"].isin(uj)]] + uj_sorok, ignore_index=True)
        tabla = tabla.sort_values(["datum", "kapu", "irany", "csoport"]).reset_index(drop=True)
        tabla["atkeles"] = tabla["atkeles"].astype(int)
        atomi_csv(tabla, tabla_ut)

    if tabla.empty:
        print("A tabla ures, nincs mit kiertekelni.")
        return 1

    s = sorozatok(tabla)
    j, kuszob, zaj = jelzesek(s)
    atomi_csv(j, args.ki / "jelzesek.csv")

    # Megrakottsag: ugyanaz a jelzesi logika, 7 napos gordulo ablakon
    mk, mz, mparam = {}, {}, {}
    if (args.ki / megrakottsag.RESZLETES.name).exists():
        _, mkusz, mt = megrakottsag.szamol(args.ki)
        ms = megrakottsag.gordulo_sorozatok(mt, list(s.index))
        if not ms.empty:          # 7 napnal rovidebb idosoron meg nincs gordulo ertek
            mj, mk, mz = jelzesek(ms)
            atomi_csv(mj, args.ki / "jelzesek_megrakottsag.csv")
        mparam = {k: round(v, 4) for k, v in mkusz.items()}

    allapot = {
        "utolso_nap": s.index.max(),
        "napok_szama": len(s),
        "elso_nap": s.index.min(),
        "frissitve_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "kuszob": {k: round(v, 4) for k, v in kuszob.items()},
        "zajszint": {k: {kk: round(vv, 4) if isinstance(vv, float) else vv
                         for kk, vv in v.items()} for k, v in zaj.items()},
        "alap_hetek": ALAP_HETEK, "min_alapnap": MIN_ALAPNAP,
        "kuszob_szorzo": KUSZOB_SZORZO,
        "kuszob_megrakottsag": {k: round(v, 4) for k, v in mk.items()},
        "zajszint_megrakottsag": {k: {kk: round(vv, 4) if isinstance(vv, float) else vv
                                      for kk, vv in v.items()} for k, v in mz.items()},
        "megrakott_kuszob_relativ_merules": mparam,
        "gordulo_nap": megrakottsag.GORDULO_NAP,
    }
    (args.ki / "allapot.json").write_text(json.dumps(allapot, ensure_ascii=False, indent=1),
                                         encoding="utf-8")

    print(f"\nIdosor: {allapot['elso_nap']} - {allapot['utolso_nap']} ({len(s)} nap), "
          f"{len(tabla):,} sor a tablaban")
    for nev in s.columns:
        z = zaj.get(nev)
        if z:
            print(f"  {nev:<14} kuszob ±{kuszob[nev]:.1%}  (robusztus szoras "
                  f"{z['robusztus_szoras']:.1%}, median |elteres| {z['median_abs_elteres']:.1%}, "
                  f"{z['napok']} nap alapszinttel)")
    jel = j[j["jelzes"].str.startswith("szokatlanul")]
    print(f"\nJelzett nap-sorozat parok: {len(jel)}")
    for r in jel.itertuples():
        print(f"  {r.datum} {r.sorozat:<14} {r.ertek:>4} vs {r.alapszint:>6.1f}  "
              f"({r.elteres:+.1%})  {r.jelzes}")
    print(f"\n-> {tabla_ut}\n-> {args.ki / 'jelzesek.csv'}\n-> {args.ki / 'allapot.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
