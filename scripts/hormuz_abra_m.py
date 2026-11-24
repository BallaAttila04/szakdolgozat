"""
A dolgozat 12. abraja (ablakonkenti atlagok) M1-M3 jelolessel.

A dolgozatban a Hormuz-mutatok jele M1-M3 (a H3 a terbeli racsot jelenti); a szamitas
valtozatlanul a hormuz_elemzes.py-e (abra_ablakok, ablak_ci), a mentett
outputs/hormuz/mintanap_mutatok.csv-bol.

Hasznalat: python hormuz_abra_m.py --ki abra_ablakok_M.png
"""
import argparse
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import hormuz_elemzes as he  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--be", type=Path, default=Path(__file__).resolve().parent.parent / "outputs" / "hormuz" / "mintanap_mutatok.csv")
ap.add_argument("--ki", type=Path, required=True)
a = ap.parse_args()
d = pd.read_csv(a.be)
d["egy"] = 1
he.MUTATOK = {k.replace("H", "M"): v for k, v in he.MUTATOK.items()}
he.abra_ablakok(d, a.ki)
print("->", a.ki)
