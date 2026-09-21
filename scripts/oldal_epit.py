"""
A GitHub Pages oldal osszeallitasa a docs/ mappaba.

A konzulensnek egyetlen linket kell tudnia megnyitni, telepites es
bejelentkezes nelkul. A GitHub Pages a main ag docs/ mappajat szolgalja ki
statikusan, ezert ide kell masolni a mar legeneralt kimeneteket.

Mi honnan jon:
  docs/index.html   - FORRASKOD, kezzel karbantartott, ezt a szkript nem
                      irja felul
  docs/terkep.html  <- outputs/terkep.html      (terkep_epit.py allitja elo)
  docs/abrak/*.png  <- outputs/*.png            (a rajzolo szkriptek)

Ezert a szkript nem general semmit, csak masol - igy nem kell ujraszamolni a
tobb perces mereseket ahhoz, hogy az oldal frissuljon.

Hasznalat:
    python oldal_epit.py
    python oldal_epit.py --oldal docs
"""

import argparse
import shutil
import sys
from pathlib import Path

from utak import KIMENET, OLDAL

# (forras az outputs/-bol, celutvonal a docs/-on belul)
MASOLANDO = [
    ("terkep.html", "terkep.html"),
    ("forgalmi_profil.png", "abrak/forgalmi_profil.png"),
    ("tomorites_tradeoff.png", "abrak/tomorites_tradeoff.png"),
]

# A nyitolap forraskod, nem generalt kimenet - sose masoljuk folule
KEZZEL_KARBANTARTOTT = {"index.html"}


def main():
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--kimenet", default=KIMENET,
                    help="A generalt fajlok forrasa (alap: outputs/)")
    ap.add_argument("--oldal", default=OLDAL,
                    help="Az oldal celmappaja (alap: docs/)")
    args = ap.parse_args()

    forras = Path(args.kimenet)
    cel = Path(args.oldal)

    nyitolap = cel / "index.html"
    if not nyitolap.exists():
        sys.exit(f"Hianyzik a nyitolap: {nyitolap}\n"
                 f"Ez forraskod, nem generalt fajl - a repobol kell jonnie.")

    masolva = 0
    hianyzo = []
    osszes_bajt = 0

    for honnan, hova in MASOLANDO:
        if Path(hova).name in KEZZEL_KARBANTARTOTT:
            continue
        f = forras / honnan
        c = cel / hova
        if not f.exists():
            hianyzo.append(honnan)
            continue
        c.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(f, c)
        meret = c.stat().st_size
        osszes_bajt += meret
        masolva += 1
        print(f"  {honnan:<28} -> {hova:<32} {meret/1024:>8,.0f} KB")

    print(f"\n  {masolva} fajl masolva, osszesen "
          f"{osszes_bajt/1_048_576:.1f} MB")

    if hianyzo:
        print(f"\n  FIGYELEM - {len(hianyzo)} forrasfajl hianyzik, "
              f"az oldalon torott hivatkozas lesz:")
        for h in hianyzo:
            print(f"    {h}")
        print("  Futtasd le eloszor az ezeket eloallito szkripteket "
              "(ld. README.md).")

    print(f"\n-> {cel} kesz. Helyi ellenorzes:")
    print(f"     python -m http.server 8000 --directory {cel}")
    print("     majd http://localhost:8000")

    return 1 if hianyzo else 0


if __name__ == "__main__":
    sys.exit(main())
