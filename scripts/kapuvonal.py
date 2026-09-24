"""
Kapuvonal-metrika: hany hajo kel at tenylegesen a dan szorosokon.

Az eddigi forgalmi mutato (orankenti egyedi hajoszam a teljes teruleten) a
szabadidos hajozast merte, amelyre egy csatornalezarasnak nincs hatasa. Ez a
szkript azt szamolja, amit egy kereskedelmi utvonal-valtozas tenylegesen
erint: hany hajo haladt at a szoros keresztmetszeten, milyen iranyban, es
milyen tipusu.

Modszer:
  1. Kapuvonal: egy szelessegi kor a szoroson keresztben, parttol partig.
     A vonalak hosszat az adatbol ellenoriztuk: a savban levo osszes pozicio
     a vonalon belul esik (ld. naplo).
  2. H3-folyoso: a vonal menti 8-as felbontasu cellak es ket cellanyi
     kornyezetuk (kb. 2 km mindket oldalon). Csak az ide eso poziciokat
     vizsgaljuk - a H3 itt indexkent szerepel.
  3. Atkeles: egy hajo ket egymast koveto pozicioja a vonal ket oldalan van,
     es a ketto kozott legfeljebb MAX_RES_MP telt el. Az irany a szelesseg
     valtozasabol adodik (eszak = kifele a Balti-tengerbol).

Kimenet:
  outputs/kapuvonal_atkelesek.csv  - atkelesenkent egy sor
  outputs/kapuvonal_napi.csv       - naponkent, kapunkent, tipusonkent

Hasznalat:
    python kapuvonal.py data/aisdk-2026-07-15.zip
    python kapuvonal.py data/aisdk-2026-07-*.zip data/aisdk-2026-09-05.zip
"""

import argparse
import csv
import sys
import zipfile
from collections import Counter, defaultdict
from pathlib import Path

import h3
import numpy as np
import pandas as pd

from utak import KIMENET
from hajo_statisztika import csoport, tisztit

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except AttributeError:
    pass

# --- Parameterek ----------------------------------------------------------

# Kapuvonalak: (szelesseg, nyugati veg, keleti veg). A vegpontok szarazfoldon
# vannak; az adatbol ellenorizve, hogy a savban minden pozicio a vonalon belul
# esik (Nagy-Balti-ov: 10,75-11,14 K; Oresund: 12,56-12,67 K).
KAPUK = {
    "Nagy-Balti-öv": (55.40, 10.60, 11.35),
    # 56,07 E: a Helsingor-Helsingborg komp utvonala (56,04 E) alatt marad,
    # igy a kompok nem keresztezik oda-vissza a vonalat
    "Øresund": (56.07, 12.40, 12.85),
}

H3_FELBONTAS = 8          # ~0,74 km2/cella
FOLYOSO_K = 2             # a vonal menti cellak ket gyurunyi kornyezete

# Ket egymast koveto pozicio kozott legfeljebb ennyi ido telhet el. Hosszabb
# vetelkieses felett nem tudjuk, mi tortent kozben, ezert nem szamolunk
# atkelest. 10 perc: a lassu Class B hajok 3 perces adaskozenel bovebb.
MAX_RES_MP = 600

CHUNK = 500_000
TS = "# Timestamp"
OSZLOPOK = {TS, "MMSI", "Latitude", "Longitude", "Ship type", "Draught"}

# A 2026-07-08-i 11. ora adathianyos (ld. szamok.md), ezert az
# osszehasonlitasokhoz ezt az orat minden naprol kihagyjuk.
KIHAGYOTT_ORA = 11


def folyoso(lat, lon0, lon1):
    a = h3.latlng_to_cell(lat, lon0, H3_FELBONTAS)
    b = h3.latlng_to_cell(lat, lon1, H3_FELBONTAS)
    ut = h3.grid_path_cells(a, b)
    cellak = set()
    for c in ut:
        cellak.update(h3.grid_disk(c, FOLYOSO_K))
    return {h3.str_to_int(c) for c in cellak}


def atkelesek(df, kapu_lat):
    """df: egy kapu folyosojaba eso poziciok (MMSI, ts, lat, lon)."""
    df = df.sort_values(["MMSI", "ts"], kind="stable")
    m = df["MMSI"].to_numpy()
    t = df["ts"].to_numpy().astype("datetime64[s]").astype(np.int64)
    la = df["Latitude"].to_numpy()
    ugyanaz = m[1:] == m[:-1]
    dt = t[1:] - t[:-1]
    elotte = la[:-1] - kapu_lat
    utana = la[1:] - kapu_lat
    eszakra = (elotte < 0) & (utana >= 0)
    delre = (elotte >= 0) & (utana < 0)
    jo = ugyanaz & (dt <= MAX_RES_MP) & (eszakra | delre)
    idx = np.flatnonzero(jo) + 1
    return pd.DataFrame({
        "MMSI": m[idx],
        "ts": df["ts"].to_numpy()[idx],
        "irany": np.where(eszakra[idx - 1], "észak", "dél"),
    })


def feldolgoz(zip_ut, folyosok):
    gyujto = {k: [] for k in KAPUK}
    tipus = defaultdict(Counter)
    merules = defaultdict(list)
    osszes = 0
    with zipfile.ZipFile(zip_ut) as zf:
        tag = [n for n in zf.namelist() if n.lower().endswith((".csv", ".txt"))][0]
        with zf.open(tag) as raw:
            for ch in pd.read_csv(raw, usecols=lambda c: c.strip() in OSZLOPOK,
                                  chunksize=CHUNK, low_memory=False,
                                  encoding="utf-8-sig"):
                ch.columns = [c.strip() for c in ch.columns]
                osszes += len(ch)
                for nev, (lat, lo0, lo1) in KAPUK.items():
                    sav = ch[ch["Latitude"].between(lat - 0.04, lat + 0.04)
                             & ch["Longitude"].between(lo0, lo1)]
                    if sav.empty:
                        continue
                    cella = np.fromiter(
                        (h3.str_to_int(h3.latlng_to_cell(a, b, H3_FELBONTAS))
                         for a, b in zip(sav["Latitude"], sav["Longitude"])),
                        dtype=np.int64, count=len(sav))
                    sav = sav[np.isin(cella, list(folyosok[nev]))]
                    if sav.empty:
                        continue
                    for mm, st, dr in zip(sav["MMSI"], sav["Ship type"], sav["Draught"]):
                        s = tisztit(st)
                        if s:
                            tipus[mm][s] += 1
                        if dr == dr and dr > 0:
                            merules[mm].append(float(dr))
                    gyujto[nev].append(sav[[TS, "MMSI", "Latitude", "Longitude"]])
                print(f"  {osszes:>12,} sor", end="\r")
    print(f"  {osszes:>12,} sor beolvasva")

    ki = []
    for nev, darabok in gyujto.items():
        if not darabok:
            continue
        df = pd.concat(darabok, ignore_index=True)
        df["ts"] = pd.to_datetime(df[TS], format="%d/%m/%Y %H:%M:%S", errors="coerce")
        df = df.dropna(subset=["ts"])
        a = atkelesek(df, KAPUK[nev][0])
        a["kapu"] = nev
        a["folyoso_pozicio"] = len(df)
        ki.append(a)
    atk = pd.concat(ki, ignore_index=True) if ki else pd.DataFrame()
    atk["csoport"] = [csoport(tipus[m].most_common(1)[0][0]) if tipus[m] else "Egyéb / ismeretlen"
                      for m in atk["MMSI"]]
    atk["merules_m"] = [round(float(np.median(merules[m])), 1) if merules[m] else None
                        for m in atk["MMSI"]]
    return atk, osszes


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("zipek", nargs="+")
    ap.add_argument("--atkelesek", default=KIMENET / "kapuvonal_atkelesek.csv")
    ap.add_argument("--napi", default=KIMENET / "kapuvonal_napi.csv")
    args = ap.parse_args()

    folyosok = {n: folyoso(*v) for n, v in KAPUK.items()}
    for n, c in folyosok.items():
        print(f"Kapu: {n:<14} lat {KAPUK[n][0]}, H3-folyoso: {len(c)} cella")

    minden = []
    for z in args.zipek:
        p = Path(z)
        if not p.exists():
            sys.exit(f"Nem letezik: {p}")
        nap = p.stem.replace("aisdk-", "")
        print(f"\n{nap}:")
        atk, _ = feldolgoz(p, folyosok)
        atk["nap"] = nap
        minden.append(atk)
        for kapu in KAPUK:
            k = atk[atk["kapu"] == kapu]
            ker = k[k["csoport"].isin(["Teherhajó", "Tanker"])]
            print(f"  {kapu:<14} {len(k):>5} atkeles, {k['MMSI'].nunique():>4} hajo | "
                  f"tanker {int((k['csoport']=='Tanker').sum()):>3}, "
                  f"teherhajo {int((k['csoport']=='Teherhajó').sum()):>3}, "
                  f"kereskedelmi eszakra/delre {int((ker['irany']=='észak').sum())}/"
                  f"{int((ker['irany']=='dél').sum())}")

    osszes = pd.concat(minden, ignore_index=True)
    osszes = osszes[["nap", "kapu", "ts", "MMSI", "irany", "csoport", "merules_m"]]
    osszes.to_csv(args.atkelesek, index=False, encoding="utf-8")

    osszes["ora"] = pd.to_datetime(osszes["ts"]).dt.hour
    sorok = []
    for (nap, kapu, cs), g in osszes.groupby(["nap", "kapu", "csoport"]):
        g2 = g[g["ora"] != KIHAGYOTT_ORA]
        sorok.append({"nap": nap, "kapu": kapu, "csoport": cs,
                      "atkeles": len(g), "eszakra": int((g["irany"] == "észak").sum()),
                      "delre": int((g["irany"] == "dél").sum()),
                      "hajo": g["MMSI"].nunique(),
                      f"atkeles_{KIHAGYOTT_ORA}_ora_nelkul": len(g2)})
    with Path(args.napi).open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(sorok[0].keys()))
        w.writeheader()
        w.writerows(sorok)
    print(f"\n-> {args.atkelesek} ({len(osszes):,} atkeles)")
    print(f"-> {args.napi}")


if __name__ == "__main__":
    main()
