"""
A terkep osszeallitasa: sablon + poziciok + hajoadatok -> egy HTML.

A harom bemenet kulon szuletik, mert kulon is ertelmes:
  - terkep_adat.py    -> poziciok szabalyos idoracson (nagy, szamitasigenyes)
  - hajo_adatok.py    -> hajonkenti statikus adatok (kicsi, kulon is hasznos)
  - terkep_sablon.html -> a lap maga, adat nelkul (szerkesztheto anelkul, hogy
                          az adatot ujra kellene generalni)

Ez a szkript csak osszefuzi oket, hogy a sablon szerkesztese utan ne kelljen
ujraszamolni semmit.

Hasznalat:
    python terkep_epit.py
    python terkep_epit.py --sablon terkep_sablon.html --ki terkep.html
"""

import argparse
import json
from pathlib import Path

from utak import KIMENET, SABLONOK
from hajo_statisztika import csoport as stat_csoport

HELYORZO = "/*ADATHELY*/"

# A terkep megjelenitesi csoportjai. Az elso HAROM kap sajat szint: a terkepen
# barmely ket pont egymas melle kerulhet, ezert az osszes szinpart ellenorizni
# kellett, es haromnal tobb szin mar nem kulonitheto el megbizhatoan (sem
# szinlatas-zavar mellett, sem normal latassal).
# A tobbi csoport semleges szurke, es a jelmagyarazatbol szurheto ki egyesevel.
# A csoportnevek a hajo_statisztika.py CSOPORTOK ertekeibol jonnek.
TERKEP_CSOPORTOK = [
    ("Áruszállítás",       ["Teherhajó", "Tanker"]),          # sajat szin
    ("Személyszállítás",   ["Személyszállító"]),              # sajat szin
    ("Kedvtelési",         ["Kedvtelési"]),                   # sajat szin
    ("Halászat",           ["Halászhajó"]),                   # semleges
    ("Szolgálati",         ["Szolgálati"]),                   # semleges
    ("Egyéb / ismeretlen", ["Egyéb / ismeretlen"]),           # semleges
]
SAJAT_SZINU = 3

# stat-csoportnev -> terkep-csoport indexe
STAT_INDEX = {stat_nev: i
              for i, (_, stat_nevek) in enumerate(TERKEP_CSOPORTOK)
              for stat_nev in stat_nevek}


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--sablon", default=SABLONOK / "terkep_sablon.html")
    ap.add_argument("--poziciok", default=KIMENET / "terkep_adat.json")
    ap.add_argument("--hajok", default=KIMENET / "hajo_adatok.json")
    ap.add_argument("--ki", default=KIMENET / "terkep.html")
    args = ap.parse_args()

    adat = json.loads(Path(args.poziciok).read_text(encoding="utf-8"))

    hajo_path = Path(args.hajok)
    if hajo_path.exists():
        info = json.loads(hajo_path.read_text(encoding="utf-8"))
        # Csak a terkepen tenylegesen szereplo hajok adatai kellenek
        kell = {str(h["m"]) for h in adat["hajok"]}
        adat["info"] = {k: v for k, v in info.items() if k in kell}
        print(f"  hajoadat: {len(adat['info']):,} hajo a(z) {len(info):,}-bol")
    else:
        print(f"  FIGYELEM: {hajo_path} nem letezik - a lap hajoadatok nelkul epul")
        adat["info"] = {}

    # --- Hajonkenti terkep-csoport (szinezeshez es szureshez) ---
    ismeretlen_idx = len(TERKEP_CSOPORTOK) - 1
    db = [0] * len(TERKEP_CSOPORTOK)
    for h in adat["hajok"]:
        rek = adat["info"].get(str(h["m"]), {})
        g = STAT_INDEX.get(stat_csoport(rek.get("Ship type", "")), ismeretlen_idx)
        h["g"] = g
        db[g] += 1

    adat["csoportok"] = [{"nev": nev, "db": db[i], "sajat_szin": i < SAJAT_SZINU}
                         for i, (nev, _) in enumerate(TERKEP_CSOPORTOK)]
    print("  terkep-csoportok:")
    for i, (nev, _) in enumerate(TERKEP_CSOPORTOK):
        jel = "szin" if i < SAJAT_SZINU else "szurke"
        print(f"    {nev:<20} {db[i]:>5} hajo  ({jel})")

    sablon = Path(args.sablon).read_text(encoding="utf-8")
    if HELYORZO not in sablon:
        raise SystemExit(f"A sablonban nincs {HELYORZO} helyorzo: {args.sablon}")

    ki = sablon.replace(HELYORZO, json.dumps(adat, ensure_ascii=False,
                                             separators=(",", ":")))
    Path(args.ki).write_text(ki, encoding="utf-8")
    print(f"-> {args.ki} kiirva ({Path(args.ki).stat().st_size / 1_048_576:.2f} MB)")


if __name__ == "__main__":
    main()
