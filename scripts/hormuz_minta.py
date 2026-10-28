"""
Hormuz-elemzes, 2. fazis: a merce szerinti mintanapok.

Minden kedd es csutortok az A26, B26, A25 es B25 ablakon belul (az ablakok
a hormuz_kozos.py-ban, a dolgozat/hormuz_elozetes_merce.md szerint). Hianyzo
vagy serult napot nem potolunk, csak naplozunk (merce).

Kimenet: outputs/hormuz/mintanapok.csv (nap, ablak, hetnap, het)

Hasznalat:
    python hormuz_minta.py
    python hormuz_minta.py --ki masik/mintanapok.csv
"""

import argparse
import sys
from pathlib import Path

from hormuz_kozos import ABLAKOK, HORMUZ, mintanapok

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except AttributeError:
    pass


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--ki", type=Path, default=HORMUZ / "mintanapok.csv")
    args = ap.parse_args()

    m = mintanapok()
    args.ki.parent.mkdir(parents=True, exist_ok=True)
    m.to_csv(args.ki, index=False, encoding="utf-8")
    for nev, (k, v) in ABLAKOK.items():
        g = m[m.ablak == nev]
        print(f"  {nev}: {k} - {v}: {len(g)} mintanap ({g.het.nunique()} het), "
              f"elso {g.nap.min()}, utolso {g.nap.max()}")
    print(f"Osszesen: {len(m)} mintanap -> {args.ki}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
