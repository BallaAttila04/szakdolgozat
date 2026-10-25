"""
A retrospektiv kuszob visszamenoleges hatasa: ket monitor-allapot (git commit)
jelzes-tablainak osszevetese.

A monitor.py a jelzesi kuszobot a TELJES idosorbol szamolja, ezert egy uj nap
egy korabbi nap minositeset is megvaltoztathatja (a dolgozatban: K13,
stabilitas). Ez a szkript ket commit outputs/monitor/jelzesek*.csv-jet a kozos
(nap, sorozat) sorokon veti ossze, sorozatonkent:
  - a kuszob regi es uj erteke,
  - a jelzett napok szama a kozos napokon,
  - az atminositett napok (a jelzes-osztaly megvaltozott),
  - hany soron valtozott maga az ertek, az alapszint vagy az elteres
    (a forgalmi sorozatokon 0-nak kell lennie; a megrakottsagin nem, mert
    ott az Otsu-kuszob es a hajonkenti P95 is ujraszamolodik).

Csak olvas (git show); a munkakonyvtarat nem modositja.

Hasznalat:
    python atminosites.py dae2366 8954e7f
    python atminosites.py 8954e7f HEAD --fajl jelzesek_megrakottsag.csv
"""

import argparse
import io
import subprocess
import sys

import pandas as pd

from utak import GYOKER

# Ezek a jelzes-osztalyok szamitanak jelzesnek (monitor.py).
JELZES_ELOTAG = "szokatlanul"
# Az elteres osszevetesenek pontossaga: a CSV 4 tizedesre kerekit.
TIZEDES = 6


def tabla(ref: str, fajl: str) -> pd.DataFrame:
    ut = f"{ref}:outputs/monitor/{fajl}"
    ki = subprocess.run(["git", "-C", str(GYOKER), "show", ut], capture_output=True)
    if ki.returncode != 0:
        sys.exit(f"Nem olvashato: {ut}\n{ki.stderr.decode('utf-8', 'replace')}")
    return pd.read_csv(io.BytesIO(ki.stdout), encoding="utf-8")


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("regi", help="a korabbi allapot commitja (pl. dae2366)")
    ap.add_argument("uj", help="a kesobbi allapot commitja (pl. HEAD)")
    ap.add_argument("--fajl", default="jelzesek.csv",
                    help="jelzesek.csv (forgalom) vagy jelzesek_megrakottsag.csv")
    args = ap.parse_args()

    r, u = tabla(args.regi, args.fajl), tabla(args.uj, args.fajl)
    m = r.merge(u, on=["datum", "sorozat"], suffixes=("_regi", "_uj"))
    print(f"{args.fajl}: {args.regi} ({len(r)} sor, utolso nap {r.datum.max()}) -> "
          f"{args.uj} ({len(u)} sor, utolso nap {u.datum.max()}); kozos nap-sorozat sor: {len(m)}")
    for s, g in m.groupby("sorozat", sort=False):
        jel = lambda c: int(g[c].str.startswith(JELZES_ELOTAG).sum())
        valt = g[g.jelzes_regi != g.jelzes_uj]
        ert = int(((g.ertek_regi != g.ertek_uj)
                   | (g.alapszint_regi.fillna(-1) != g.alapszint_uj.fillna(-1))
                   | (g.elteres_regi.fillna(-9).round(TIZEDES)
                      != g.elteres_uj.fillna(-9).round(TIZEDES))).sum())
        print(f"{s:<32} kuszob {g.kuszob_regi.iloc[0]:.4f} -> {g.kuszob_uj.iloc[0]:.4f} | "
              f"jelzett {jel('jelzes_regi')} -> {jel('jelzes_uj')} | atminositett {len(valt)} | "
              f"ertek/alapszint/elteres valtozott: {ert}")
        for _, x in valt.iterrows():
            print(f"    {x.datum}: {x.jelzes_regi} -> {x.jelzes_uj} (elteres {x.elteres_uj:+.4f})")
    print(f"Feldolgozva: {len(r)} + {len(u)} sor, osszevetve {len(m)} kozos sor.")


if __name__ == "__main__":
    main()
