"""
A Hormuz-elemzes kozos resze: az idoablakok, a mintanapok, a heti blokkos
bootstrap es a Holm-korrekcio. Minden ertek a dolgozat/hormuz_elozetes_merce.md
szerinti (rogzitve 2026-10-28, commit 0807fd3); itt nem valtoztatjuk.

A tobbi Hormuz-szkript (hormuz_portwatch.py, hormuz_minta.py, hormuz_napi.py,
hormuz_elemzes.py) innen importal, hogy az ablakok es a becsles egy helyen
legyen definialva.
"""

from datetime import date, timedelta

import numpy as np
import pandas as pd

from utak import KIMENET

HORMUZ = KIMENET / "hormuz"

# --- Idoablakok (merce, "Idoszakok") ---------------------------------------
# A: zar elott; B: zarva (az elso, atmeneti het kimarad); 25: ugyanezek a
# naptari ablakok 2025-ben (kontroll). Mindket vegpont benne van.
ABLAKOK = {
    "A26": (date(2026, 1, 12), date(2026, 2, 27)),
    "B26": (date(2026, 3, 9), date(2026, 5, 29)),
    "A25": (date(2025, 1, 13), date(2025, 2, 28)),
    "B25": (date(2025, 3, 10), date(2025, 5, 30)),
}

# Mintavetel: minden kedd es csutortok az ablakokon belul (weekday: H=0)
MINTA_HETNAPOK = (1, 3)

# Esemenydatumok az abrakhoz (merce + naplo 2026-10-28 11:00)
ZAR = date(2026, 2, 28)
UJRANYITAS = (date(2026, 6, 18), date(2026, 7, 8))

# Bootstrap (merce, "Becsles es dontesi szabaly")
BOOTSTRAP_N = 2000
ALFA = 0.05
SEED = 20261028           # rogzitett, hogy a futas reprodukalhato legyen


def ablak(nap) -> str | None:
    """A nap melyik ablakba esik (vagy None)."""
    d = pd.Timestamp(nap).date()
    for nev, (k, v) in ABLAKOK.items():
        if k <= d <= v:
            return nev
    return None


def mintanapok() -> pd.DataFrame:
    sorok = []
    for nev, (k, v) in ABLAKOK.items():
        d = k
        while d <= v:
            if d.weekday() in MINTA_HETNAPOK:
                sorok.append({"nap": d.isoformat(), "ablak": nev,
                              "hetnap": ["H", "K", "Sze", "Cs", "P", "Szo", "V"][d.weekday()],
                              "het": blokk(d)})
            d += timedelta(days=1)
    return pd.DataFrame(sorok)


def blokk(nap) -> str:
    """A heti blokk azonositoja: az ISO-het hetfoje. Mind a negy ablak
    hetfon kezdodik, igy a blokkok teljes hetek (az utolso a pentekig tart)."""
    d = pd.Timestamp(nap).date()
    return (d - timedelta(days=d.weekday())).isoformat()


# --- Becsles -----------------------------------------------------------------

def _blokk_osszegek(df, szamlalo, nevezo):
    """Ablakonkent a heti blokkok (szamlalo, nevezo) osszegei: tomb, alak (n_blokk, 2)."""
    ki = {}
    for nev in ABLAKOK:
        g = df[df["ablak"] == nev]
        if g.empty:
            ki[nev] = np.zeros((0, 2))
            continue
        s = g.groupby("blokk")[[szamlalo, nevezo]].sum()
        ki[nev] = s.to_numpy(dtype=float)
    return ki


def did(atlag: dict) -> float:
    """(B26 - A26) - (B25 - A25)"""
    return (atlag["B26"] - atlag["A26"]) - (atlag["B25"] - atlag["A25"])


def ablak_atlagok(df, szamlalo, nevezo) -> dict:
    """Ablakonkent sum(szamlalo) / sum(nevezo). Napi atlaghoz a nevezo a
    napok szama (egy oszlop csupa 1-gyel), aranyhoz a nevezo darabszama."""
    b = _blokk_osszegek(df, szamlalo, nevezo)
    return {n: (x[:, 0].sum() / x[:, 1].sum()) if x[:, 1].sum() else np.nan
            for n, x in b.items()}


def bootstrap_did(df, szamlalo, nevezo, n=BOOTSTRAP_N, seed=SEED, tobb=None):
    """Heti blokkos bootstrap a kulonbsegek kulonbsegere.

    df oszlopai: ablak, blokk, szamlalo, nevezo. A blokkokat ablakon belul,
    visszatevessel huzzuk (merce). `tobb`: tovabbi (df, szamlalo, nevezo)
    sorozatok, amelyeket UGYANAZOKKAL a blokk-indexekkel huzunk (pl. az
    Oresund es a kontrollszoros ugyanazon hetei); ekkor a visszaadott minta
    az elso sorozat DiD-je minusz a tovabbiak DiD-jenek atlaga.

    Visszaad: (pontbecsles, bootstrap-mintak tombje)."""
    sorozatok = [(df, szamlalo, nevezo)] + list(tobb or [])
    blokkok = [_blokk_osszegek(*s) for s in sorozatok]
    for b in blokkok[1:]:
        for nev in ABLAKOK:
            if b[nev].shape[0] != blokkok[0][nev].shape[0]:
                raise ValueError(f"{nev}: a sorozatok blokkszama elter")

    def becsles(idx):
        dids = []
        for b in blokkok:
            atl = {}
            for nev in ABLAKOK:
                x = b[nev][idx[nev]]
                atl[nev] = x[:, 0].sum() / x[:, 1].sum() if x[:, 1].sum() else np.nan
            dids.append(did(atl))
        return dids[0] - (np.mean(dids[1:]) if len(dids) > 1 else 0.0)

    teljes = {nev: np.arange(blokkok[0][nev].shape[0]) for nev in ABLAKOK}
    pont = becsles(teljes)
    rng = np.random.default_rng(seed)
    mintak = np.empty(n)
    for i in range(n):
        idx = {nev: rng.integers(0, len(t), len(t)) for nev, t in teljes.items()}
        mintak[i] = becsles(idx)
    return pont, mintak


def intervallum(mintak, alfa=ALFA):
    """Percentilis-intervallum (1 - alfa)."""
    m = mintak[~np.isnan(mintak)]
    return float(np.quantile(m, alfa / 2)), float(np.quantile(m, 1 - alfa / 2))


def bootstrap_p(mintak) -> float:
    """Ketoldali bootstrap p-ertek: 2 * min(P(theta* <= 0), P(theta* >= 0)).
    Ez a percentilis-intervallummal konzisztens: p < alfa pontosan akkor,
    ha az (1 - alfa) intervallum nem tartalmazza a nullat."""
    m = mintak[~np.isnan(mintak)]
    return float(min(1.0, 2 * min((m <= 0).mean(), (m >= 0).mean())))


def holm(pk: dict, alfa=ALFA) -> dict:
    """Holm-fele lepcsozetes eljaras. pk: nev -> p. Visszaad nevenkent:
    korrigalt p, a lepeshez tartozo szint (alfa / (m - k + 1)) es elvetes."""
    m = len(pk)
    rend = sorted(pk, key=lambda k: pk[k])
    ki, max_p, meg_elvet = {}, 0.0, True
    for i, nev in enumerate(rend):
        szint = alfa / (m - i)
        max_p = max(max_p, min(1.0, (m - i) * pk[nev]))
        elvet = meg_elvet and pk[nev] < szint
        meg_elvet = elvet
        ki[nev] = {"p_holm": max_p, "szint": szint, "rang": i + 1, "elvet": elvet}
    return ki
