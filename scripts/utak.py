"""
Kozos utvonalak a szkriptekhez.

Minden szkript a PROJEKT GYOKEREHEZ kepest dolgozik, nem az aktualis
munkakonyvtarhoz - igy barhonnan futtathato:

    python scripts/forgalom_elemzes.py ...      (a gyokerbol)
    python forgalom_elemzes.py ...              (a scripts/ mappabol)

mindketto ugyanoda ir. Az argparse alapertelmezesek ezeket hasznaljak, de
minden utvonal felulirhato parancssorbol.
"""

from pathlib import Path

GYOKER = Path(__file__).resolve().parent.parent

# Nyers, letoltott AIS adat (git-ignore)
ADAT = GYOKER / "data"

# Abrak, tablazatok, koztes fajlok
KIMENET = GYOKER / "outputs"

# Futtatasi naplok (git-ignore)
LOGOK = KIMENET / "logs"

# A terkep sablonja a szkriptek mellett van, mert forraskod
SABLONOK = GYOKER / "scripts"

# A GitHub Pages altal kiszolgalt statikus oldal (docs/ a main agon).
# A nyitolap (index.html) forraskod, a tobbi fajlt az oldal_epit.py masolja
# ide az outputs/-bol.
OLDAL = GYOKER / "docs"
