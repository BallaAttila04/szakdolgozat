"""
Hajonkenti STATIKUS adatok kinyerese a napi AIS fajlbol.

Az AIS ketfele uzenetet kever: dinamikus (pozicio, sebesseg) es statikus
(nev, hajotipus, meret, uticel). A DMA napi CSV-jeben a statikus mezok minden
sorra ra vannak masolva, ezert hajonkent eleg egyszer kiolvasni oket.

Mellektermek - adatminoseg: megszamoljuk, hany hajo jelent egymasnak
ellentmondo nevet vagy tipust a nap folyaman. Az AIS statikus mezoi kezzel
beallitott ertekek, amiket a szemelyzet elgepelhet vagy elfelejthet
frissiteni, ezert ez valos jelenseg, nem elmeleti kockazat.

Hasznalat:
    python hajo_adatok.py data/aisdk-2026-07-15.zip
    python hajo_adatok.py <zip> --csak-bbox --ki hajo_adatok.json
"""

import argparse
import json
import sys
import zipfile
from collections import defaultdict
from pathlib import Path

import pandas as pd

from utak import KIMENET

LAT_MIN, LAT_MAX = 54.5, 56.5
LON_MIN, LON_MAX = 10.0, 13.0

CHUNK = 500_000

# Statikus mezok, amiket hajonkent gyujtunk
MEZOK = ["Name", "Ship type", "Callsign", "IMO", "Length", "Width",
         "Type of mobile", "Destination"]
COLS = ["MMSI", "Latitude", "Longitude"] + MEZOK

# Ezeket az ertekeket "nincs adat"-kent kezeljuk
URES = {"", "unknown", "undefined", "nan", "none", "n/a"}


def ures_e(v) -> bool:
    return v is None or str(v).strip().lower() in URES


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("zip_fajl")
    ap.add_argument("--csak-bbox", action="store_true",
                    help="Csak a bounding boxban megjelent hajok")
    ap.add_argument("--ki", default=KIMENET / "hajo_adatok.json")
    args = ap.parse_args()

    path = Path(args.zip_fajl)
    if not path.exists():
        sys.exit(f"Nem letezik: {path}")

    # hajo -> mezo -> {kulonbozo ertekek}
    ertekek = defaultdict(lambda: defaultdict(set))
    bbox_hajok = set()
    osszes = 0

    with zipfile.ZipFile(path) as zf:
        tag = [n for n in zf.namelist() if n.lower().endswith((".csv", ".txt"))][0]
        with zf.open(tag) as raw:
            olvaso = pd.read_csv(raw, usecols=lambda c: c.strip() in COLS,
                                 chunksize=CHUNK, low_memory=False,
                                 encoding="utf-8-sig")
            for ch in olvaso:
                ch.columns = [c.strip() for c in ch.columns]
                osszes += len(ch)

                benne = (ch["Latitude"].between(LAT_MIN, LAT_MAX)
                         & ch["Longitude"].between(LON_MIN, LON_MAX))
                bbox_hajok.update(ch.loc[benne, "MMSI"].unique().tolist())

                # Csak azok a sorok kellenek, ahol legalabb egy statikus mezo ki van toltve
                reszlet = ch[["MMSI"] + MEZOK].drop_duplicates()
                for sor in reszlet.itertuples(index=False):
                    mmsi = sor[0]
                    for i, mezo in enumerate(MEZOK, start=1):
                        v = sor[i]
                        if not ures_e(v):
                            ertekek[mmsi][mezo].add(str(v).strip())

                print(f"  {osszes:>12,} sor", end="\r")
    print()

    kivalasztott = bbox_hajok if args.csak_bbox else set(ertekek.keys())
    print(f"  {osszes:,} sor, {len(ertekek):,} hajo statikus adattal, "
          f"{len(bbox_hajok):,} hajo a bounding boxban")

    # --- Adatminoseg: ellentmondo statikus mezok ---
    utkozes = {m: 0 for m in MEZOK}
    for mmsi in kivalasztott:
        for mezo, halmaz in ertekek.get(mmsi, {}).items():
            if len(halmaz) > 1:
                utkozes[mezo] += 1

    print("\n  Ellentmondo statikus mezok (egy hajo tobbfele erteket jelentett):")
    for mezo, db in sorted(utkozes.items(), key=lambda x: -x[1]):
        if db:
            arany = db / max(len(kivalasztott), 1) * 100
            print(f"    {mezo:<16} {db:>5} hajo ({arany:.1f}%)")

    # --- Kimenet: hajonkent egy rekord ---
    ki = {}
    hianyzo_nev = 0
    for mmsi in sorted(kivalasztott):
        m = ertekek.get(mmsi, {})
        rek = {}
        for mezo in MEZOK:
            h = m.get(mezo)
            if h:
                # tobb ertek eseten a leghosszabb (a csonkolt valtozatok kiszurese)
                rek[mezo] = max(h, key=len) if len(h) > 1 else next(iter(h))
        if "Name" not in rek:
            hianyzo_nev += 1
        ki[str(mmsi)] = rek

    print(f"\n  {hianyzo_nev:,} hajonak ({hianyzo_nev/max(len(ki),1)*100:.1f}%) "
          f"nincs bejelentett neve")

    Path(args.ki).write_text(json.dumps(ki, ensure_ascii=False,
                                        separators=(",", ":")), encoding="utf-8")
    meret = Path(args.ki).stat().st_size / 1024
    print(f"-> {args.ki} kiirva ({len(ki):,} hajo, {meret:,.0f} KB)")


if __name__ == "__main__":
    main()
