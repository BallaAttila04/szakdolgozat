"""
Hormuz-elemzes: minimalis kimutathato hatas (MDE) a H1-H3-ra.

UTOLAGOS SZAMITAS, NEM A MERCE RESZE (a hallgato kerese, a 4. fazis utan). A
dontesi szabalyt es a fo eredmenyt nem erinti.

  MDE = (z(1 - alfa/2) + z(ero)) * SE

SE: a kulonbsegek kulonbsegenek bootstrap-szorasa, ugyanazzal a heti blokkos
bootstrappel es maggal, mint a fo elemzesben (hormuz_kozos.bootstrap_did), a
mintanap_mutatok.csv-bol. Ellenorzes: a 95%-os intervallumnak szamjegyre egyeznie
kell az eredmeny.csv-vel, kulonben a szkript megall. A normalis kozelites
ellenorzesere az SE a percentilis-intervallumbol is szamolodik.

A viszonyitasi szint az A26 ablakatlag (a zar elotti 2026-os szint).

A fo oszlop alfa = 0,05-tel szamol. A dontesi szabaly viszont Holm-korrigalt, igy
a legszigorubb (elso) lepcson alfa/3 az erdemi szint: ez kulon oszlop.

Kimenet: outputs/hormuz/mde.csv

Hasznalat:
    python hormuz_mde.py
    python hormuz_mde.py --hormuz outputs/hormuz
"""

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import norm

from hormuz_elemzes import MUTATOK
from hormuz_kozos import ABLAKOK, ALFA, HORMUZ, ablak_atlagok, bootstrap_did, intervallum

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)
except AttributeError:
    pass

# A hallgato altal megadott ero; a szokasos 80%
ERO = 0.80
# Holm elso lepcsoje harom mutatonal (H1-H3)
HOLM_ELSO_ALFA = ALFA / 3
# Az eredmeny.csv-vel valo egyezes turese (kerekitesi zaj, a szamok azonosak kell legyenek)
EGYEZES_TURES = 1e-9
VISZONYITAS = "A26"


def szorzo(alfa, ero=ERO) -> float:
    return float(norm.ppf(1 - alfa / 2) + norm.ppf(ero))


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--hormuz", type=Path, default=HORMUZ)
    args = ap.parse_args()
    h = args.hormuz

    d = pd.read_csv(h / "mintanap_mutatok.csv", dtype={"nap": str})
    d["egy"] = 1
    e = pd.read_csv(h / "eredmeny.csv").set_index("mutato")
    print(f"Beolvasva: {len(d)} mintanap -> " +
          ", ".join(f"{a} {int((d.ablak == a).sum())}" for a in ABLAKOK))
    print(f"Szorzo: alfa={ALFA}, ero={ERO}: {szorzo(ALFA):.4f}; "
          f"alfa={HOLM_ELSO_ALFA:.4f} (Holm 1. lepcso), ero={ERO}: {szorzo(HOLM_ELSO_ALFA):.4f}")

    sorok = []
    for m, (sz, nv, leiras) in MUTATOK.items():
        pont, mintak = bootstrap_did(d, sz, nv)
        a, f = intervallum(mintak)
        if max(abs(a - e.loc[m, "ci95_also"]), abs(f - e.loc[m, "ci95_felso"]),
               abs(pont - e.loc[m, "did"])) > EGYEZES_TURES:
            sys.exit(f"{m}: a bootstrap nem egyezik az eredmeny.csv-vel - megallok.")
        se = float(np.nanstd(mintak, ddof=1))
        se_perc = (f - a) / (2 * norm.ppf(1 - ALFA / 2))
        szint = ablak_atlagok(d, sz, nv)[VISZONYITAS]
        mde = szorzo(ALFA) * se
        mde_holm = szorzo(HOLM_ELSO_ALFA) * se
        sorok.append({"mutato": m, "leiras": leiras, "did": pont, "se_bootstrap": se,
                      "se_percentilisbol": se_perc, "szint_A26": szint,
                      "mde": mde, "mde_szint_arany": mde / szint,
                      "mde_percentilisbol": szorzo(ALFA) * se_perc,
                      "mde_holm1": mde_holm, "mde_holm1_szint_arany": mde_holm / szint,
                      "alfa": ALFA, "ero": ERO, "bootstrap_ervenyes": int((~np.isnan(mintak)).sum())})
    t = pd.DataFrame(sorok)
    t.to_csv(h / "mde.csv", index=False, encoding="utf-8")
    pd.set_option("display.width", 250)
    print("\nEgyezes az eredmeny.csv-vel (pont, 95% CI): mindharom mutatonal rendben")
    print(t.drop(columns=["leiras", "alfa", "ero"]).round(4).to_string(index=False))
    print(f"\nFeldolgozva: {len(d)} mintanap, {len(t)} mutato -> {h / 'mde.csv'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
