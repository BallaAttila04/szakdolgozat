"""
Hormuz-elemzes, 1. fazis: a PortWatch napi szoros-forgalma (letoltes nelkul).

Bemenet: data/portwatch_chokepoints_2026-10-25.csv (IMF PortWatch, napi
athaladasok szorosonkent; n_tanker = tankerek szama naponta).

Kimenet (outputs/hormuz/):
  portwatch_hormuz.png          a Hormuzi-szoros napi tankerforgalma
                                2025-01-01-tol, 7 napos gordulo atlag,
                                a 02-28-i zar es a 06-18 - 07-08-i reszleges
                                ujranyitas jelolesevel
  portwatch_kontroll.png        Oresund, Dover, Gibraltar 2019-tol: 7 napos
                                gordulo atlag es havi YoY%
  portwatch_did.csv             kulonbsegek kulonbsege a merce szerint:
                                (B26 - A26) - (B25 - A25) szorosonkent, es az
                                Oresund a kontrollokhoz kepest; heti blokkos
                                bootstrap (2 000 ismetles, a blokkok ablakon
                                belul, a szorosok ugyanazon heteit huzva)
  portwatch_elozetes_trend.csv  havi Oresund-YoY 2025-07-tol es az
                                Oresund - Dover kulonbseg havonta

A PortWatch napi adat, ezert itt az ablakok MINDEN napja szerepel (a keddi-
csutortoki mintavetel az AIS-letoltes merete miatt kell, ld. merce).

Hasznalat:
    python hormuz_portwatch.py
    python hormuz_portwatch.py --be data/portwatch_chokepoints.csv --ki outputs/hormuz
"""

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from utak import ADAT
from hormuz_kozos import (ABLAKOK, BOOTSTRAP_N, HORMUZ, UJRANYITAS, ZAR, ablak,
                          ablak_atlagok, blokk, bootstrap_did, bootstrap_p, intervallum)

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)
except AttributeError:
    pass

# --- Parameterek ----------------------------------------------------------

BEMENET = ADAT / "portwatch_chokepoints_2026-10-25.csv"

HORMUZ_NEV = "Strait of Hormuz"
ORESUND = "Oresund Strait"
KONTROLLOK = ["Dover Strait", "Gibraltar Strait"]   # merce, "Kulso kontroll"
MUTATO = "n_tanker"

GORDULO = 7                 # nap; feladat 1. fazis
HORMUZ_KEZDET = "2025-01-01"
KONTROLL_KEZDET = "2019-01-01"
TREND_KEZDET = "2025-07"    # feladat 1. fazis, 4. pont

ROVID = {HORMUZ_NEV: "Hormuz", ORESUND: "Øresund",
         "Dover Strait": "Dover", "Gibraltar Strait": "Gibraltár"}


def betolt(ut: Path) -> pd.DataFrame:
    d = pd.read_csv(ut, usecols=["date", "portname", MUTATO], parse_dates=["date"])
    print(f"Beolvasva: {len(d):,} sor, {d.portname.nunique()} szoros, "
          f"{d.date.min():%Y-%m-%d} - {d.date.max():%Y-%m-%d}")
    return d


def sorozat(d, nev) -> pd.Series:
    s = d[d.portname == nev].set_index("date")[MUTATO].sort_index()
    teljes = pd.date_range(s.index.min(), s.index.max())
    hiany = len(teljes) - len(s)
    if hiany:
        print(f"  {nev}: {hiany} hianyzo nap (NaN marad, nem potoljuk)")
    return s.reindex(teljes)


def havi_yoy(s: pd.Series) -> pd.DataFrame:
    h = s.resample("MS").mean()
    napok = s.resample("MS").count()
    yoy = 100 * (h / h.shift(12) - 1)
    return pd.DataFrame({"atlag": h, "napok": napok, "yoy_szazalek": yoy})


# --- Abrak ---------------------------------------------------------------------

def abra_hormuz(s, ki):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    x = s[HORMUZ_KEZDET:]
    g = x.rolling(GORDULO, min_periods=GORDULO).mean()
    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(x.index, x, color="#BBBBBB", lw=0.6, label="napi")
    ax.plot(g.index, g, color="#4C78A8", lw=1.8, label=f"{GORDULO} napos gördülő átlag")
    for d, felirat in [(ZAR, "zár (02-28)"), (UJRANYITAS[0], "részleges újranyitás (06-18)"),
                       (UJRANYITAS[1], "újra zárva (07-08)")]:
        ax.axvline(pd.Timestamp(d), color="#E45756", ls="--", lw=1)
        ax.text(pd.Timestamp(d), ax.get_ylim()[1] * 0.97, " " + felirat, color="#E45756",
                fontsize=8, va="top", rotation=90)
    ax.set_title("Hormuzi-szoros – tanker-áthaladás naponta (IMF PortWatch)")
    ax.set_ylabel("tanker / nap")
    ax.legend(loc="lower left", fontsize=8)
    fig.tight_layout()
    fig.savefig(ki, dpi=150)
    plt.close(fig)


def abra_kontroll(sorok: dict, ki):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    nevek = [ORESUND] + KONTROLLOK
    fig, axs = plt.subplots(len(nevek) + 1, 1, figsize=(11, 10), sharex=True)
    szinek = {ORESUND: "#4C78A8", "Dover Strait": "#F58518", "Gibraltar Strait": "#54A24B"}
    for ax, nev in zip(axs, nevek):
        s = sorok[nev][KONTROLL_KEZDET:]
        ax.plot(s.index, s.rolling(GORDULO, min_periods=GORDULO).mean(), color=szinek[nev], lw=1)
        ax.set_ylabel("tanker / nap")
        ax.set_title(f"{ROVID[nev]} – {GORDULO} napos gördülő átlag", fontsize=9, loc="left")
    ax = axs[-1]
    for nev in nevek:
        y = havi_yoy(sorok[nev][KONTROLL_KEZDET:])["yoy_szazalek"]
        ax.plot(y.index, y, color=szinek[nev], lw=1.2, label=ROVID[nev])
    ax.axhline(0, color="#888888", lw=0.6)
    ax.set_ylabel("havi YoY %")
    ax.set_title("Havi átlag az előző év azonos hónapjához képest", fontsize=9, loc="left")
    ax.legend(fontsize=8, ncol=3)
    for a in axs:
        a.axvline(pd.Timestamp(ZAR), color="#E45756", ls="--", lw=0.8)
    fig.suptitle("Tankerforgalom: Øresund és a kontrollszorosok (IMF PortWatch)")
    fig.tight_layout()
    fig.savefig(ki, dpi=150)
    plt.close(fig)


# --- Kulonbsegek kulonbsege -------------------------------------------------------

def ablak_tabla(s: pd.Series) -> pd.DataFrame:
    t = pd.DataFrame({"nap": s.index, "ertek": s.to_numpy()})
    t["ablak"] = [ablak(d) for d in t["nap"]]
    t = t.dropna(subset=["ablak", "ertek"]).copy()
    t["blokk"] = [blokk(d) for d in t["nap"]]
    t["egy"] = 1
    return t


def did_sor(cimke, kontroll, t, tobb, relativ=False):
    if relativ:
        # log-skala: a DiD a ln(ablak-atlag)-okon, (exp - 1) * 100 = %
        pont, mintak = _did_log(t, tobb)
    else:
        pont, mintak = bootstrap_did(t, "ertek", "egy", tobb=tobb)
    a, f = intervallum(mintak)
    sor = {"osszevetes": cimke, "kontroll": kontroll,
           "skala": "relatív (log, %)" if relativ else "szint (tanker/nap)",
           "becsles": pont, "ci_also": a, "ci_felso": f, "p_bootstrap": bootstrap_p(mintak),
           "nulla_az_intervallumban": bool(a <= 0 <= f)}
    if relativ:
        for k in ("becsles", "ci_also", "ci_felso"):
            sor[k] = 100 * (np.exp(sor[k]) - 1)
    return sor


def _did_log(t, tobb):
    """Ugyanaz a blokk-huzas, a DiD a ln(ablak-atlagokon). A bootstrap_did
    a szamlalo/nevezo aranyt atlagolja, ezert itt kozvetlenul huzunk."""
    from hormuz_kozos import SEED, _blokk_osszegek, did
    sorozatok = [(t, "ertek", "egy")] + list(tobb or [])
    blokkok = [_blokk_osszegek(*s) for s in sorozatok]

    def becsles(idx):
        dids = []
        for b in blokkok:
            atl = {n: np.log(b[n][idx[n]][:, 0].sum() / b[n][idx[n]][:, 1].sum()) for n in ABLAKOK}
            dids.append(did(atl))
        return dids[0] - (np.mean(dids[1:]) if len(dids) > 1 else 0.0)

    teljes = {n: np.arange(blokkok[0][n].shape[0]) for n in ABLAKOK}
    pont = becsles(teljes)
    rng = np.random.default_rng(SEED)
    mintak = np.array([becsles({n: rng.integers(0, len(x), len(x)) for n, x in teljes.items()})
                       for _ in range(BOOTSTRAP_N)])
    return pont, mintak


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--be", type=Path, default=BEMENET)
    ap.add_argument("--ki", type=Path, default=HORMUZ)
    args = ap.parse_args()
    args.ki.mkdir(parents=True, exist_ok=True)

    d = betolt(args.be)
    sorok = {n: sorozat(d, n) for n in [HORMUZ_NEV, ORESUND] + KONTROLLOK}

    # 1. Hormuz-abra
    abra_hormuz(sorok[HORMUZ_NEV], args.ki / "portwatch_hormuz.png")
    h = sorok[HORMUZ_NEV]
    for k, v in [("2026-02-01", "2026-02-27"), ("2026-03-09", "2026-05-29"),
                 ("2026-06-18", "2026-07-08"), ("2026-07-09", "2026-10-18")]:
        print(f"  Hormuz {k} - {v}: {h[k:v].mean():.1f} tanker/nap ({h[k:v].count()} nap)")

    # 2. Kontroll-abra
    abra_kontroll(sorok, args.ki / "portwatch_kontroll.png")

    # 3. Kulonbsegek kulonbsege
    tablak = {n: ablak_tabla(sorok[n]) for n in [ORESUND] + KONTROLLOK}
    print("\nAblak-atlagok (tanker/nap; napok szama):")
    for n, t in tablak.items():
        atl = ablak_atlagok(t, "ertek", "egy")
        db = t.groupby("ablak").size()
        print(f"  {ROVID[n]:<10} " + "  ".join(f"{a} {atl[a]:6.2f} ({db.get(a, 0)})" for a in ABLAKOK))
    eredm = []
    for relativ in (False, True):
        for n in [ORESUND] + KONTROLLOK:
            eredm.append(did_sor(ROVID[n], "–", tablak[n], None, relativ))
        for k in KONTROLLOK:
            eredm.append(did_sor("Øresund − kontroll", ROVID[k], tablak[ORESUND],
                                 [(tablak[k], "ertek", "egy")], relativ))
        eredm.append(did_sor("Øresund − kontroll", "Dover és Gibraltár átlaga", tablak[ORESUND],
                             [(tablak[k], "ertek", "egy") for k in KONTROLLOK], relativ))
    did_t = pd.DataFrame(eredm)
    for c in ("becsles", "ci_also", "ci_felso"):
        did_t[c] = did_t[c].round(3)
    did_t["p_bootstrap"] = did_t["p_bootstrap"].round(4)
    did_t["bootstrap_n"] = BOOTSTRAP_N
    did_t.to_csv(args.ki / "portwatch_did.csv", index=False, encoding="utf-8")
    print("\nKulonbsegek kulonbsege, (B26 - A26) - (B25 - A25), 95% heti blokkos bootstrap:")
    print(did_t.drop(columns="bootstrap_n").to_string(index=False))

    # 4. Elozetes trend
    yo = havi_yoy(sorok[ORESUND])
    yd = havi_yoy(sorok["Dover Strait"])
    yg = havi_yoy(sorok["Gibraltar Strait"])
    tr = pd.DataFrame({
        "honap": yo.index.strftime("%Y-%m"),
        "oresund_atlag": yo["atlag"].round(2).to_numpy(),
        "oresund_napok": yo["napok"].to_numpy(),
        "oresund_yoy": yo["yoy_szazalek"].round(1).to_numpy(),
        "dover_yoy": yd["yoy_szazalek"].reindex(yo.index).round(1).to_numpy(),
        "gibraltar_yoy": yg["yoy_szazalek"].reindex(yo.index).round(1).to_numpy(),
    })
    tr["oresund_minus_dover_szazalekpont"] = (tr["oresund_yoy"] - tr["dover_yoy"]).round(1)
    tr = tr[tr["honap"] >= TREND_KEZDET]
    tr.to_csv(args.ki / "portwatch_elozetes_trend.csv", index=False, encoding="utf-8")
    print(f"\nElozetes trend, havonta ({TREND_KEZDET}-tol; YoY %, kulonbseg szazalekpont):")
    print(tr.to_string(index=False))

    print(f"\nFeldolgozott sor: {len(d):,}; ablakokba eso nap (Oresund): "
          f"{len(tablak[ORESUND])}")
    for f in ("portwatch_hormuz.png", "portwatch_kontroll.png", "portwatch_did.csv",
              "portwatch_elozetes_trend.csv"):
        print(f"-> {args.ki / f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
