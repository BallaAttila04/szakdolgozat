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

HELYORZO = "/*ADATHELY*/"


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

    sablon = Path(args.sablon).read_text(encoding="utf-8")
    if HELYORZO not in sablon:
        raise SystemExit(f"A sablonban nincs {HELYORZO} helyorzo: {args.sablon}")

    ki = sablon.replace(HELYORZO, json.dumps(adat, ensure_ascii=False,
                                             separators=(",", ":")))
    Path(args.ki).write_text(ki, encoding="utf-8")
    print(f"-> {args.ki} kiirva ({Path(args.ki).stat().st_size / 1_048_576:.2f} MB)")


if __name__ == "__main__":
    main()
