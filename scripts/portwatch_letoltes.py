"""
IMF PortWatch napi chokepoint-forgalom letoltese.

A PortWatch AIS-bol szarmaztatott napi hajoforgalmi es szallitokapacitas-
becslest publikal 28 strategiai tengeri szorosra/csatornara
(Daily_Chokepoints_Data FeatureService). Ez kulso, fuggetlen viszonyitasi
pont a sajat dan AIS-feldolgozasunkhoz: osszevetheto vele a sajat szamolt
tanker-forgalom, es a dan szoros relativ sulya is lathato a tobbi nagy uti
irany (pl. Hormuz) mellett.

Az adat MERETBEN elhanyagolhato a projekt tobbi reszehez kepest: soronkent
egy nap egy chokepoint, nehany egesz szammal. Mert ertek (2026-09-22):
1000 sor letoltese 158 357 bajt - a teljes 28 szoros ~7.7 eves tortenete
(78 764 sor) ezert becsulhetoen ~12 MB, egyetlen napi AIS ZIP tortedeke.

FONTOS - amit a "dan szoros" NEM fed le pontosan: a PortWatch csak az
"Oresund Strait"-et koveti (chokepoint10), a Nagy-Balti-ovet (Storebaelt)
es a Kis-Balti-ovet (Lillebaelt) nem. A sajat bounding boxunk
(54.5-56.5E, 10.0-13.0K) mindharmat lefedi, ezert a sajat szamolt
tanker-forgalmunk STRUKTURALISAN nagyobb kell legyen, mint a PortWatch
Oresund-erteke - ez nem hiba, modszertani kulonbseg, es a dolgozatban ki
kell mondani.

MEG NEM tisztazott: a legutobbi kb. 2-3 het adata (2026-09-22-i lekerdezes-
kor) feltunoen alacsonynak tunt a korabbi honapokhoz kepest - nagy
valoszinuseggel feldolgozasi keses a PortWatch oldalan (heti frissitesuek),
nem valodi forgalomcsokkenes. Ellenorizve nem lett, ezert az elemzeshez
erdemes ezt a legutobbi savot kihagyni vagy kulon kezelni.

Forras: IMF PortWatch, Daily_Chokepoints_Data FeatureService,
services9.arcgis.com/weJ1QsnbMYJlCHdG. Licenc: IMF altalanos felhasznalasi
feltetelek (imf.org/external/terms.htm) - idezes elott at kell olvasni.

Hasznalat:
    python portwatch_letoltes.py                              # mind a 28 szoros
    python portwatch_letoltes.py --chokepoint chokepoint10 chokepoint6
    python portwatch_letoltes.py --ki data/portwatch.csv
"""

import argparse
import csv
import sys
import time
from pathlib import Path

import requests

from utak import ADAT

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except AttributeError:
    pass

BASE = ("https://services9.arcgis.com/weJ1QsnbMYJlCHdG/arcgis/rest/services/"
        "Daily_Chokepoints_Data/FeatureServer/0/query")

MEZOK = ["date", "portid", "portname", "n_container", "n_dry_bulk",
         "n_general_cargo", "n_roro", "n_tanker", "n_cargo", "n_total",
         "capacity_container", "capacity_dry_bulk", "capacity_general_cargo",
         "capacity_roro", "capacity_tanker", "capacity_cargo", "capacity"]

# A szolgaltatas egy hivasra ennyi sort ad vissza - lapozni kell (resultOffset).
# Merve 2026-09-22: 1000 sor/hivas a tenyleges felso korlat.
LAP_MERET = 1000

# Udvarias ismetlesi keses hivasok kozott - publikus, kulcs nelkuli
# szolgaltatas, nem akarjuk eltulterhelni sok egymas utani kerdessel
KESES_MP = 0.2

# A dolgozat szempontjabol kozvetlenul relevans ket szoros (ld. naplo.md)
DAN_SZOROS = "chokepoint10"    # Oresund Strait
HORMUZ = "chokepoint6"         # Strait of Hormuz


def lekerdez(where: str, offset: int):
    parameterek = {
        "where": where,
        "outFields": ",".join(MEZOK),
        "orderByFields": "portid,date",
        "resultOffset": offset,
        "resultRecordCount": LAP_MERET,
        "f": "json",
    }
    v = requests.get(BASE, params=parameterek, timeout=30)
    v.raise_for_status()
    d = v.json()
    if "error" in d:
        sys.exit(f"API hiba: {d['error']}")
    return d.get("features", [])


def letolt(where: str):
    sorok = []
    offset = 0
    while True:
        darab = lekerdez(where, offset)
        if not darab:
            break
        sorok.extend(f["attributes"] for f in darab)
        offset += len(darab)
        print(f"  {offset:>7,} sor letoltve", end="\r")
        if len(darab) < LAP_MERET:
            break
        time.sleep(KESES_MP)
    print()
    return sorok


def main():
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--chokepoint", nargs="*", default=None,
                    help="Csak ezeket a chokepoint-azonositokat toltse le "
                         "(pl. chokepoint10 chokepoint6). Alapbol mind a 28-at.")
    ap.add_argument("--ki", default=ADAT / "portwatch_chokepoints.csv")
    args = ap.parse_args()

    if args.chokepoint:
        idezett = ",".join(f"'{c}'" for c in args.chokepoint)
        where = f"portid IN ({idezett})"
    else:
        where = "1=1"

    print(f"Letoltes: {BASE}")
    print(f"Szures: {where}")
    sorok = letolt(where)

    if not sorok:
        sys.exit("Nem jott vissza egy sor sem - ellenorizd a szurest.")

    szorosok = sorted({(s["portid"], s["portname"]) for s in sorok})
    datumok = sorted(s["date"] for s in sorok if s.get("date"))

    print(f"\n  {len(sorok):,} sor, {len(szorosok)} szoros")
    for pid, nev in szorosok:
        print(f"    {pid:<14} {nev}")
    if datumok:
        print(f"  idotartomany: {datumok[0]} - {datumok[-1]}")

    Path(args.ki).parent.mkdir(parents=True, exist_ok=True)
    with Path(args.ki).open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(MEZOK)
        for s in sorok:
            w.writerow([s.get(m) for m in MEZOK])

    meret = Path(args.ki).stat().st_size / 1024
    print(f"\n-> {args.ki} kiirva ({meret:,.0f} KB)")


if __name__ == "__main__":
    main()
