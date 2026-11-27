"""Kapuvonal korüli ide-oda váltás: kereskedelmi hajók napi, kapunkénti átkelésszáma 2 fölött.

Többlet = sum(max(0, n - 2)) hajó-nap-kapu csoportonként; eset = csoport, ahol n > 2.
A monitornál azt is megnézi, mely jelzések múlnak a többleten.
Használat: python scripts/ide_oda_ellenorzes.py > outputs/ide_oda_ellenorzes.txt
"""
from pathlib import Path
import pandas as pd

O = Path(__file__).resolve().parent.parent / "outputs"
KER = ["Teherhajó", "Tanker"]


def tobblet(ut, nap, ig=None):
    d = pd.read_csv(ut)
    d = d[d.csoport.isin(KER)]
    if ig:
        d = d[d[nap] <= ig]  # a dolgozat fagyasztott monitorállapota
    g = d.groupby([nap, "MMSI", "kapu"]).size()
    s = (g - 2).clip(lower=0)
    print(f"{ut.relative_to(O)}: {d[nap].nunique()} nap, {len(d)} kereskedelmi átkelés, "
          f"többlet {int(s.sum())}, eset {int((g > 2).sum())}")
    return g[g > 2]


esetek = tobblet(O / "monitor/atkelesek_reszletes.csv", "datum", ig="2026-10-22")
print(esetek.to_string())
tobblet(O / "hormuz/atkelesek.csv", "nap")
k = O / "hormuz/kitoltes/atkelesek.csv"
if k.exists():
    tobblet(k, "nap")

F = O / "fagyasztas_2026-10-22/monitor/jelzesek.csv"
j = pd.read_csv(F if F.exists() else O / "monitor/jelzesek.csv")
tb = (esetek - 2).reset_index(name="t")
for _, r in tb.groupby("datum"):
    dt = r.datum.iloc[0]
    for sor in ["Nagy-Balti-öv", "Øresund", "Mindkét kapu"]:
        x = j[(j.datum == dt) & (j.sorozat == sor)]
        if x.empty:
            continue
        x = x.iloc[0]
        le = r.t.sum() if sor == "Mindkét kapu" else r[r.kapu == sor].t.sum()
        uj = (x.ertek - le - x.alapszint) / x.alapszint
        print(f"{dt} {sor}: {x.ertek} -> {x.ertek - le}, eltérés {x.elteres:+.3f} -> {uj:+.3f}, "
              f"küszöb {x.kuszob:.3f}, jelzés: {x.jelzes} -> {'jelez' if abs(uj) > x.kuszob else 'normál'}")
