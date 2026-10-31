"""
A meroszam megvalasztasanak hatasa a napi minositesre, a teljes idosoron.

A dolgozat 3.4 alfejezetenek elso esete eredetileg ket napra (2026-07-15/16)
mutatta meg, hogy ugyanabbol az adatbol a meroszamtol fuggoen mas eltérés
adodik. Ez a szkript ugyanazt az osszehasonlitast a monitor fagyasztott,
144 napos allapotan (kapuvonal_napi.csv) minden napra elvegzi, harom
valtozatban, a ket kapu osszesitett napi atkelesen:

  A  naiv       minden hajotipus, rogzitett viszonyitas (az osszevetheto
                napok mediánja; evszakot es hetnapot nem kezel)
  B  hetnap     minden hajotipus, a monitor alapszintje (az elozo 4 het
                azonos hetnapjanak mediánja)
  C  monitor    kereskedelmi (teherhajo + tanker) atkeles, a monitor
                alapszintje - ez a monitor "Mindkét kapu" sorozata

A kuszob mindharom valtozatban a monitor szabalya (KUSZOB_SZORZO x 1,4826 x
MAD, a sajat elteres-sorozatbol), a jelzes ugyanaz a fuggveny (monitor.jelzesek).
Az osszevetes csak azokon a napokon fut, ahol B-nek es C-nek is van alapszintje.

Ellenorzes: a C valtozat napra pontosan egyezik-e a fagyasztott jelzesek.csv
"Mindkét kapu" soraival (ELLENORZES sor a kimenetben).

Az eredeti eset elso meroszama (oranankenti egyedi hajoszam a teljes vizsgalt
teruleten) a fagyasztott allapotbol nem szamolhato: a monitor csak kapuvonal-
atkeleseket tarol. Az A valtozat ezert az atkelesszamot hasznalja.

Csak olvas: <monitor>/kapuvonal_napi.csv, <monitor>/jelzesek.csv.
Kimenet: <ki>/mertekszam_napi.csv (naponkent harom elteres es minosites),
         <ki>/mertekszam_osszegzes.csv.

Hasznalat:
    python mertekszam_hatas.py
    python mertekszam_hatas.py --monitor outputs/fagyasztas_2026-10-22/monitor --ki outputs/kiel_csere
"""

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from utak import KIMENET
from kapuvonal import KAPUK
import monitor

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)
except AttributeError:
    pass

# A dolgozat szamai a 2026-10-22-i fagyasztott allapotra vonatkoznak.
FAGYASZTOTT = KIMENET / "fagyasztas_2026-10-22" / "monitor"
KI = KIMENET / "kiel_csere"

VALTOZATOK = {"A": "naiv (minden hajó, rögzített szint)",
              "B": "hétnap (minden hajó, monitor-alapszint)",
              "C": "monitor (kereskedelmi, monitor-alapszint)"}


def osszes_hajo(tabla: pd.DataFrame) -> pd.DataFrame:
    """A ket kapu osszes atkelese naponkent, hajotipustol fuggetlenul."""
    k = tabla[tabla["kapu"].isin(list(KAPUK))]
    s = k.groupby("datum")["atkeles"].sum()
    s = s.reindex(sorted(tabla["datum"].unique()), fill_value=0)
    return s.to_frame(monitor.OSSZES)


def naiv(s: pd.Series):
    """Elteres a teljes idosor mediánjatol, a monitor kuszobszabalyaval."""
    e = s / float(np.median(s)) - 1
    mad = float(np.median(np.abs(e - np.median(e))))
    kuszob = monitor.KUSZOB_SZORZO * monitor.MAD_SKALA * mad
    jel = np.where(e > kuszob, "szokatlanul magas",
                   np.where(e < -kuszob, "szokatlanul alacsony", "normál"))
    return e, kuszob, jel


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--monitor", type=Path, default=FAGYASZTOTT, help="monitor CSV-k (csak olvas)")
    ap.add_argument("--ki", type=Path, default=KI)
    args = ap.parse_args()

    tabla = pd.read_csv(args.monitor / "kapuvonal_napi.csv")
    print(f"Beolvasva: {len(tabla):,} sor, {tabla['datum'].nunique()} nap "
          f"({tabla['datum'].min()} - {tabla['datum'].max()})")

    jb, kb, _ = monitor.jelzesek(osszes_hajo(tabla))
    jc, kc, _ = monitor.jelzesek(monitor.sorozatok(tabla)[[monitor.OSSZES]])
    jc = jc[jc["sorozat"] == monitor.OSSZES]

    # ellenorzes a fagyasztott monitorkimenettel
    fagy = pd.read_csv(args.monitor / "jelzesek.csv")
    fagy = fagy[fagy["sorozat"] == monitor.OSSZES].set_index("datum")
    cc = jc.set_index("datum")
    egyezik = int(((cc["jelzes"] == fagy["jelzes"])
                   & (cc["elteres"].fillna(9) .round(4) == fagy["elteres"].fillna(9).round(4))).sum())
    print(f"ELLENORZES: C valtozat vs. fagyasztott jelzesek.csv ({monitor.OSSZES}): "
          f"{egyezik}/{len(fagy)} nap egyezik; kuszob {kc[monitor.OSSZES]:.4f}")

    d = pd.DataFrame({"datum": cc.index})
    d["ertek_osszes"] = osszes_hajo(tabla)[monitor.OSSZES].reindex(d["datum"]).to_numpy()
    d["ertek_keresk"] = cc["ertek"].to_numpy()
    d["elteres_B"] = jb.set_index("datum")["elteres"].reindex(d["datum"]).to_numpy()
    d["jelzes_B"] = jb.set_index("datum")["jelzes"].reindex(d["datum"]).to_numpy()
    d["elteres_C"], d["jelzes_C"] = cc["elteres"].to_numpy(), cc["jelzes"].to_numpy()

    ert = d[d["elteres_B"].notna() & d["elteres_C"].notna()].copy()
    print(f"Osszevetheto nap (B-nek es C-nek is van alapszintje): {len(ert)} / {len(d)}")
    # az A szintje es kuszobe is csak ezekbol a napokbol, hogy a harom valtozat
    # ugyanarra a napkeszletre vonatkozzon
    ea, ka, ja = naiv(ert["ertek_osszes"].astype(float))
    ert["elteres_A"], ert["jelzes_A"] = ea.round(4), ja
    d = d.merge(ert[["datum", "elteres_A", "jelzes_A"]], on="datum", how="left")

    kuszob = {"A": ka, "B": kb[monitor.OSSZES], "C": kc[monitor.OSSZES]}
    sorok = []
    for v, nev in VALTOZATOK.items():
        e = ert[f"elteres_{v}"].astype(float)
        j = ert[f"jelzes_{v}"]
        sorok.append({"valtozat": v, "leiras": nev, "napok": len(e),
                      "robusztus_szoras": round(monitor.MAD_SKALA * float(np.median(np.abs(e - e.median()))), 4),
                      "kuszob": round(kuszob[v], 4),
                      "jelzett": int((j != "normál").sum()),
                      "magas": int((j == "szokatlanul magas").sum()),
                      "alacsony": int((j == "szokatlanul alacsony").sum())})
    ossz = pd.DataFrame(sorok)

    def jelzett(v):
        return ert[f"jelzes_{v}"] != "normál"

    parok = []
    for a, b in (("A", "C"), ("B", "C"), ("A", "B")):
        kul = (ert[f"elteres_{a}"] - ert[f"elteres_{b}"]).abs()
        ellentetes = int((np.sign(ert[f"elteres_{a}"]) * np.sign(ert[f"elteres_{b}"]) < 0).sum())
        mas_min = int((jelzett(a) != jelzett(b)).sum())
        parok.append({"par": f"{a}-{b}", "median_abs_kulonbseg_szp": round(100 * kul.median(), 1),
                      "p90_abs_kulonbseg_szp": round(100 * kul.quantile(0.9), 1),
                      "max_abs_kulonbseg_szp": round(100 * kul.max(), 1),
                      "max_nap": ert.loc[kul.idxmax(), "datum"],
                      "ellentetes_elojel": ellentetes, "mas_minosites": mas_min,
                      "mindketto_jelez": int((jelzett(a) & jelzett(b)).sum())})
    par = pd.DataFrame(parok)
    harom = int((jelzett("A") | jelzett("B") | jelzett("C")).sum())
    egyutt = int((jelzett("A") & jelzett("B") & jelzett("C")).sum())

    args.ki.mkdir(parents=True, exist_ok=True)
    d.to_csv(args.ki / "mertekszam_napi.csv", index=False)
    pd.concat([ossz, par], ignore_index=True).to_csv(args.ki / "mertekszam_osszegzes.csv", index=False)

    print()
    print(ossz.to_string(index=False))
    print()
    print(par.to_string(index=False))
    print(f"\nLegalabb egy valtozatban jelzett nap: {harom}; mindharomban: {egyutt}")
    print(f"-> {args.ki / 'mertekszam_napi.csv'}")
    print(f"-> {args.ki / 'mertekszam_osszegzes.csv'}")


if __name__ == "__main__":
    main()
