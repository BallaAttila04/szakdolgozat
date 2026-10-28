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
    python atminosites.py dae2366 f8603b3 --lanc --ki outputs/eles_uzem/atminosites_lanc.csv

--lanc: a ket commit kozotti osszes olyan commit, amely a jelzes-fajlokat
modositotta, egymast koveto paronkent (ez az eles uzem napi lepese); mindket
jelzes-fajlra, sorozatonkent egy CSV-sor.
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


def osszevet(r, u):
    """Sorozatonkent: kuszob, jelzett napok, atminositett napok, valtozott ertekek."""
    m = r.merge(u, on=["datum", "sorozat"], suffixes=("_regi", "_uj"))
    ki = []
    for s, g in m.groupby("sorozat", sort=False):
        jel = lambda c: int(g[c].str.startswith(JELZES_ELOTAG).sum())
        valt = g[g.jelzes_regi != g.jelzes_uj]
        ert = int(((g.ertek_regi != g.ertek_uj)
                   | (g.alapszint_regi.fillna(-1) != g.alapszint_uj.fillna(-1))
                   | (g.elteres_regi.fillna(-9).round(TIZEDES)
                      != g.elteres_uj.fillna(-9).round(TIZEDES))).sum())
        ki.append({"sorozat": s, "kozos_nap": len(g),
                   "kuszob_regi": g.kuszob_regi.iloc[0], "kuszob_uj": g.kuszob_uj.iloc[0],
                   "jelzett_regi": jel("jelzes_regi"), "jelzett_uj": jel("jelzes_uj"),
                   "atminositett": len(valt), "valtozott_ertek": ert,
                   "atminositett_napok": " ".join(valt.datum)})
    return m, ki


def lanc(regi, uj, ki_ut):
    fajlok = ["outputs/monitor/jelzesek.csv", "outputs/monitor/jelzesek_megrakottsag.csv"]
    log = subprocess.run(["git", "-C", str(GYOKER), "log", "--format=%h %cs", "--reverse",
                          f"{regi}..{uj}", "--", *fajlok], capture_output=True, text=True)
    commitok = [(regi, "")] + [tuple(x.split()) for x in log.stdout.splitlines() if x.strip()]
    sorok = []
    for (a, _), (b, datum) in zip(commitok, commitok[1:]):
        for fajl in ("jelzesek.csv", "jelzesek_megrakottsag.csv"):
            r, u = tabla(a, fajl), tabla(b, fajl)
            _, ki = osszevet(r, u)
            for x in ki:
                sorok.append({"regi": a, "uj": b, "commit_datum": datum, "utolso_nap": u.datum.max(),
                              "fajl": fajl, **x})
    df = pd.DataFrame(sorok)
    df.to_csv(ki_ut, index=False, encoding="utf-8")
    print(f"{len(commitok) - 1} commitpar ({regi} -> {uj}), {len(df)} sor -> {ki_ut}")
    print(df.groupby("sorozat", sort=False)
            .agg(lepes=("atminositett", "size"), atminositett=("atminositett", "sum"),
                 lepes_atminositessel=("atminositett", lambda v: int((v > 0).sum())),
                 valtozott_ertek=("valtozott_ertek", "sum"))
            .to_string())


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("regi", help="a korabbi allapot commitja (pl. dae2366)")
    ap.add_argument("uj", help="a kesobbi allapot commitja (pl. HEAD)")
    ap.add_argument("--fajl", default="jelzesek.csv",
                    help="jelzesek.csv (forgalom) vagy jelzesek_megrakottsag.csv")
    ap.add_argument("--lanc", action="store_true",
                    help="az osszes koztes commit, egymast koveto paronkent (CSV-be)")
    ap.add_argument("--ki", default=str(GYOKER / "outputs" / "eles_uzem" / "atminosites_lanc.csv"))
    args = ap.parse_args()
    if args.lanc:
        lanc(args.regi, args.uj, args.ki)
        return

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
