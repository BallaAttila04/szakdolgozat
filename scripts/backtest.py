"""
A napi monitor jelzesi szabalyanak backtestje (a dolgozat ertekelesi fejezete).

A monitor.py szabalya: alapszint = az elozo 4 het azonos hetnapjanak mediánja
(legalabb 3 nap), relativ elteres = ertek / alapszint - 1, kuszob =
2 x 1,4826 x MAD a TELJES idosor elteresebol (retrospektiv). Ez a szkript a
szabalyt NEM valtoztatja meg, hanem kivulrol ertekeli:

  1. Reprodukcio: a monitor fuggvenyeivel (import, nem masolat) es a sajat,
     vektorizalt motorral ujraszamolja a jelzeseket, es napra pontosan
     osszeveti az outputs/monitor/jelzesek*.csv-vel (ELLENORZES).
  2. Walk-forward: minden d napra a kuszob csak a d elotti napok elteresebol
     (bovulo ablak), illetve egy rogzitett tanuloidoszakbol (utana befagyasztva).
  3. Szabalyvaltozatok ugyanazon a walk-forward kereten (R0-R4).
  4. Szintetikus esemeny-injektalas: szorzos csokkenes / novekedes minden
     lehetseges kezdonapra; eszlelesi arany, keses, teves riasztas, ROC.
  5. Placebo-teszt a Kiel-lezarasra (07-15 - 07-16).
  6. Kulso referencia: ugyanaz a szabaly a PortWatch Oresund-sorozatan.
  7. Heti blokk-bootstrap konfidenciaintervallum.

Csak olvas: outputs/monitor/*.csv, data/portwatch_chokepoints.csv.
Kimenet: outputs/backtest/ (kis CSV-k + PNG abrak).

Hasznalat:
    python backtest.py
    python backtest.py --ki outputs/backtest --bootstrap 2000
"""

import argparse
import sys
import time
import warnings
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

from utak import ADAT, KIMENET
import monitor
import megrakottsag

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)
except AttributeError:
    pass

# --- Parameterek ----------------------------------------------------------

MONITOR = KIMENET / "monitor"
BACKTEST = KIMENET / "backtest"
PORTWATCH = ADAT / "portwatch_chokepoints.csv"

# A monitor elo parameterei - innen vesszuk at, nem masoljuk (ha a monitor
# valtozik, a backtest is a valtozott szabalyt meri).
ALAP_HETEK = monitor.ALAP_HETEK          # 4
MIN_ALAPNAP = monitor.MIN_ALAPNAP        # 3
KUSZOB_SZORZO = monitor.KUSZOB_SZORZO    # 2,0
MAD_SKALA = monitor.MAD_SKALA            # 1,4826
GORDULO = megrakottsag.GORDULO_NAP       # 7

# Walk-forward minimalis tanuloido: 21 alapszintes nap = 3 teljes het, igy
# minden hetnap legalabb 3-szor szerepel a MAD-ban (a hetnapi zaj-kulonbseg
# nem torzitja). A MAD-bol becsult szoras relativ hibaja kb. 1,17/sqrt(n):
# n = 21-nel ~25%, n = 28-nal ~22% - a kulonbseg kicsi, a 21 viszont a Kiel-
# ablakot (07-15) mar lefedi az elso alapszintes nap (06-22) utan. A 28-as
# erteket erzekenysegi valtozatkent kulon is lefuttatjuk.
MIN_TANULO = 21
MIN_TANULO_ERZEKENYSEG = 28

# Rogzitett tanuloidoszak: junius-julius (az adat elso ket honapja); utana a
# kuszob befagy. Ket honap a legrovidebb, amelyben az elso alapszintes nap
# (06-22) utan is >= 5 het (40 nap) elteres gyulik ossze.
TANULO_VEG = "2026-07-31"

# R1: kuszobszorzo-racs. 1,5-3 sigma: normalis eloszlasnal ketoldali 13,4% -
# 0,27% varhato jelzesi arany; a 2 a jelenlegi ertek.
K_R1 = (1.5, 2.0, 2.5, 3.0)
# A ROC-gorbehez surubb racs ugyanebben a tartomanyban (+ szelek).
K_ROC = tuple(float(k) for k in np.round(np.arange(1.0, 4.01, 0.25), 2))

# R2: alapszint-hetek. 2 het = gyorsan alkalmazkodik, zajos median; 6 het =
# stabil, de lassan koveti a szezont. A min. napszam: legfeljebb egy hianyzo
# het (W-1), de legalabb 2 ertek (1 ertek "mediánja" nem robusztus).
HETEK_R2 = (2, 3, 4, 6)


def min_alapnap(w):
    return MIN_ALAPNAP if w == ALAP_HETEK else max(2, w - 1)


# R4: ketoldali tabularis CUSUM a log(ertek / alapszint) standardizalt
# erteken (Page, 1954 - a hivatkozast a szovegiro ellenorzi). A referencia-
# ertek 0,5 szoras: ez az 1 szorasnyi tartos eltolodas eszlelesere optimalis
# beallitas; a dontesi hatar h = 4 a szakirodalomban szokasos (h = 4-5)
# ertekek kozul az erzekenyebb [NEM ELLENORIZVE: forras-hivatkozas].
CUSUM_REF = 0.5
CUSUM_H = 4.0
CUSUM_H_RACS = (1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 8.0, 10.0)

# Esemeny-injektalas: nagysag es hossz. 10-50%: a 10% a napi zajszint
# (median |elteres| 7,6-11,1%) alatt van, az 50% egy teljes forgalomterelodes
# nagysagrendje. Hossz: 1 nap (egynapos zavar), 2 nap (a Kiel-lezaras
# hossza), 7 nap (tartos valtozas, a megrakottsagi 7c teszt hossza).
INJ_M = (0.1, 0.2, 0.3, 0.4, 0.5)
INJ_L = (1, 2, 7)
UTOABLAK = 7        # eszlelesi ablak: az esemeny L napja + 7 nap utana

# A Kiel-lezaras (2026-07-15 szerda - 07-16 csutortok) es a hozza illo
# injektalt eset (2 nap, +/-30%: a monitor 07-15-i +33,0%-os eltereserol).
KIEL = ("2026-07-15", "2026-07-16")
KIEL_M, KIEL_L = 0.3, 2
GYENGE_M, GYENGE_L = 0.1, 7     # a "gyenge, tartos" eset a ROC masik paneljehez

# Ajanlott munkapont: a legnagyobb k (legkevesebb teves riasztas), amely a
# Kiel-meretu esemenyt meg legalabb 90%-ban eszleli.
CEL_ESZLELES = 0.9

# Heti blokk-bootstrap: a napok autokorrelaltak (heti ritmus, tobbnapos
# zavarok), ezert egesz naptari heteket mintavetelezunk.
BOOT_B = 2000
SEED = 20261012

# Elorenezes-teszt: minden 7. napnal vagjuk el az idosort (hetnaponkent mas
# nap esik a vagasra, igy minden hetnap szerepel; 131 napnal ~19 vagas).
ELORE_LEPES = 7

# A "teves riasztas" a modositatlan adaton mert jelzesi rata; a Kiel-
# lezaras es az azt koveto nap (07-15 - 07-17) valodi esemeny lehet, ezert
# kulon, ezek nelkul is megadjuk.
KIEL_KORNYEK = ("2026-07-15", "2026-07-16", "2026-07-17")

PW_NEV = "Oresund Strait"
NINCS = -9

KAPU_SOROZATOK = ["Nagy-Balti-öv", "Øresund", "Mindkét kapu"]


# --- Motor: alapszint, elteres, kuszob ---------------------------------------

def ertekek(napi, gordulo):
    """A jelzett ertek: a napi szam, vagy annak 7 napos gordulo osszege
    (ugyanugy, mint a megrakottsag.gordulo_sorozatok: osszeg, majd kerekites)."""
    if not gordulo:
        return napi
    return pd.Series(napi).rolling(GORDULO, min_periods=GORDULO).sum().round(0).to_numpy()


def alapszint(x, hetek=ALAP_HETEK, min_nap=MIN_ALAPNAP):
    """Az elozo `hetek` het azonos hetnapjanak mediánja (folytonos naptar)."""
    n = len(x)
    M = np.full((hetek, n), np.nan)
    for w in range(1, hetek + 1):
        if 7 * w < n:
            M[w - 1, 7 * w:] = x[:n - 7 * w]
    db = np.sum(~np.isnan(M), axis=0)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        med = np.nanmedian(M, axis=0)
    return np.where((db >= min_nap) & (med > 0), med, np.nan)


def elteres(x, hetek=ALAP_HETEK, min_nap=MIN_ALAPNAP):
    b = alapszint(x, hetek, min_nap)
    with np.errstate(invalid="ignore", divide="ignore"):
        return x / b - 1, b


def mad(v):
    return float(np.median(np.abs(v - np.median(v))))


def mad_palya(e, t0=0, t1=None, min_db=MIN_TANULO):
    """Walk-forward: a t. napra a MAD csak a t elotti ervenyes elteresekbol."""
    n = len(e)
    t1 = n if t1 is None else min(t1, n)
    ki = np.full(n, np.nan)
    ok = ~np.isnan(e)
    db = np.concatenate([[0], np.cumsum(ok)])      # db[t] = ervenyes napok t elott
    for t in range(max(t0, 1), t1):
        if db[t] >= min_db:
            ki[t] = mad(e[:t][ok[:t]])
    return ki


def osztalyoz(e, kuszob):
    """+1 szokatlanul magas, -1 szokatlanul alacsony, 0 normal, NINCS."""
    e2, k2 = np.broadcast_arrays(e, kuszob)
    c = np.full(e2.shape, NINCS, dtype=np.int8)
    ok = ~np.isnan(e2) & ~np.isnan(k2)
    c[ok] = 0
    c[ok & (e2 > k2)] = 1
    c[ok & (e2 < -k2)] = -1
    return c


def retro(x, k=KUSZOB_SZORZO):
    """A monitor retrospektiv szabalya (a teljes idosor MAD-ja)."""
    e, b = elteres(x)
    v = e[~np.isnan(e)]
    kusz = k * MAD_SKALA * mad(v) if len(v) else np.nan
    return osztalyoz(e, kusz), e, b, kusz


def cusum(z, t0, t1, init=None, H=CUSUM_H_RACS, allapot=False):
    """Ketoldali tabularis CUSUM; jelzes utan az adott oldal nullazodik.
    init: (S+, S-) a t0 nap elotti allapot (az injektalt futashoz)."""
    H = np.asarray(H, dtype=float)
    n = len(z)
    sp = np.zeros(len(H)) if init is None else init[0].copy()
    sm = np.zeros(len(H)) if init is None else init[1].copy()
    cl = np.full((len(H), n), NINCS, dtype=np.int8)
    tort = np.zeros((2, len(H), n + 1)) if allapot else None
    for t in range(t0, t1):
        if allapot:
            tort[0, :, t], tort[1, :, t] = sp, sm
        if np.isnan(z[t]):
            continue
        sp = np.maximum(0.0, sp + z[t] - CUSUM_REF)
        sm = np.maximum(0.0, sm - z[t] - CUSUM_REF)
        hi, lo = sp > H, sm > H
        cl[:, t] = np.where(hi, 1, np.where(lo, -1, 0))
        sp[hi] = 0.0
        sm[lo] = 0.0
    return cl, tort


def futtat(napi, gordulo, r3, veg_i, t0=0, t1=None, cusum_init=None, allapot=False):
    """Minden walk-forward szabalyvaltozat osztalyozasa a [t0, t1) napokra.
    Kulcs: (csalad, parameter). Az R0 = ("R1", 2.0)."""
    n = len(napi)
    t1 = n if t1 is None else t1
    x = ertekek(napi, gordulo)
    res, tort = {}, None
    for w in HETEK_R2:
        e, b = elteres(x, w, min_alapnap(w))
        m = mad_palya(e, t0, t1)
        if w != ALAP_HETEK:
            res[("R2", w)] = osztalyoz(e, KUSZOB_SZORZO * MAD_SKALA * m)
            continue
        kr = np.array(K_ROC)[:, None]
        cl = osztalyoz(e, kr * MAD_SKALA * m[None, :])
        for i, k in enumerate(K_ROC):
            res[("R1", k)] = cl[i]
        # rogzitett tanuloidoszak: veg_i utan a kuszob befagy
        mf = m.copy()
        ok = ~np.isnan(e[:veg_i + 1])
        lo = max(veg_i + 1, t0)
        if lo < t1:
            mf[lo:t1] = mad(e[:veg_i + 1][ok]) if ok.sum() >= MIN_TANULO else np.nan
        res[("R0fix", KUSZOB_SZORZO)] = osztalyoz(e, KUSZOB_SZORZO * MAD_SKALA * mf)
        # CUSUM a log-aranyon (0 erteknel 0,5-os folytonossagi korrekcio)
        with np.errstate(invalid="ignore", divide="ignore"):
            lr = np.log(np.where(x > 0, x, 0.5) / b)
        ml = mad_palya(lr, t0, t1)
        with np.errstate(invalid="ignore", divide="ignore"):
            z = lr / (MAD_SKALA * ml)
        z[~np.isfinite(z)] = np.nan
        ccl, tort = cusum(z, t0, t1, cusum_init, allapot=allapot)
        for i, h in enumerate(CUSUM_H_RACS):
            res[("R4", h)] = ccl[i]
    if r3:
        x3 = ertekek(napi, True)
        e3, _ = elteres(x3)
        m3 = mad_palya(e3, t0, t1)
        cl = osztalyoz(e3, np.array(K_ROC)[:, None] * MAD_SKALA * m3[None, :])
        for i, k in enumerate(K_ROC):
            res[("R3", k)] = cl[i]
    return res, tort


def szabaly_nev(kulcs):
    cs, p = kulcs
    if cs == "R1":
        return "R0 (k=2)" if p == KUSZOB_SZORZO else f"R1 k={p:g}"
    if cs == "R0fix":
        return "R0 rögzített tanulóidő"
    if cs == "R2":
        return f"R2 {p} hét"
    if cs == "R3":
        return f"R3 7 napos összeg k={p:g}"
    if cs == "R4":
        return f"R4 CUSUM h={p:g}"
    return str(kulcs)


# A fo osszevetesi tablaban szereplo szabalyok
FO_SZABALYOK = ([("R1", KUSZOB_SZORZO), ("R0fix", KUSZOB_SZORZO)]
                + [("R1", k) for k in K_R1 if k != KUSZOB_SZORZO]
                + [("R2", w) for w in HETEK_R2 if w != ALAP_HETEK]
                + [("R3", KUSZOB_SZORZO), ("R4", CUSUM_H)])


# --- Adatok ------------------------------------------------------------------

def beolvas(mon: Path):
    tabla = pd.read_csv(mon / "kapuvonal_napi.csv", dtype={"datum": str})
    s = monitor.sorozatok(tabla)
    tort = pd.read_csv(mon / megrakottsag.TORTENET.name, dtype={"nap": str})
    resz = pd.read_csv(mon / megrakottsag.RESZLETES.name, dtype={"datum": str})
    r = megrakottsag.relativ(resz, megrakottsag.hajo_max(tort))
    kusz = megrakottsag.kuszobok(r)
    mt = megrakottsag.napi_tabla(r, kusz)          # csak memoriaban, nem irjuk ki
    ms = megrakottsag.gordulo_sorozatok(mt, list(s.index))
    return tabla, s, tort, resz, mt, ms


def napi_megrakottsag(mt, naptar, adatos):
    """A gordulo sorozatok NAPI alapja (a megrakottsag.gordulo_sorozatok
    belseje gordites nelkul) - az injektalashoz kell."""
    ki = {}
    for nev, cs, oszlop in [("Megrakott tanker (7 nap)", "Tanker", "megrakott"),
                            ("Megrakott teherhajó (7 nap)", "Teherhajó", "megrakott"),
                            ("Tanker-volumen (7 nap, 1000 m³)", "Tanker", "volumenindex")]:
        v = mt[mt.csoport == cs].groupby("datum")[oszlop].sum().reindex(naptar, fill_value=0)
        v[[d not in adatos for d in naptar]] = np.nan
        if oszlop == "volumenindex":
            v = v / 1000
        ki[nev] = (v.to_numpy(dtype=float), oszlop != "volumenindex")
    return ki


def otsu_tanulo(resz, tort, veg):
    """A megrakottsagi Otsu-kuszob csak a `veg` napig tarto atkelesekbol (a
    hajonkenti P95 marad a teljes tortenetbol). Visszaad: (kuszobok, napi tabla)."""
    r = megrakottsag.relativ(resz, megrakottsag.hajo_max(tort))
    kusz = megrakottsag.kuszobok(r[r.datum <= veg])
    return kusz, megrakottsag.napi_tabla(r, kusz)


def nulla_injektalas(sorozat, orig, allap, veg_i, n):
    """Konzisztencia: modositatlan adattal a reszleges (t0 = kezdonap, CUSUM-
    allapottal inditott) futas pontosan a teljes futas osztalyait adja-e.
    Visszaad: (osszevetett nap-szabaly cellak, elteres)."""
    db = elt = 0
    for nev, sp in sorozat.items():
        res0 = orig[nev]
        barmely = np.zeros(n, bool)
        for c in res0.values():
            barmely |= c != NINCS
        for st in np.flatnonzero(barmely):
            t1 = min(n, st + max(INJ_L) + UTOABLAK)
            init = allap[nev][:, :, st]
            res, _ = futtat(sp["napi"].copy(), sp["gordulo"], sp["r3"], veg_i, st, t1,
                            cusum_init=(init[0], init[1]))
            for k, c in res.items():
                db += t1 - st
                elt += int((c[st:t1] != res0[k][st:t1]).sum())
    return db, elt


def elorenezes_teszt(sorozat, orig, veg_i, n, lepes=ELORE_LEPES, seed=SEED):
    """Nincs-e elorenezes: a t utani napokat veletlen szorzoval (0,3-3x)
    elrontjuk, es a [0, t] napok osztalyai nem valtozhatnak - egyik
    szabalyvaltozatnal sem (a rogzitett tanuloidoszakos kuszob is csak a
    TANULO_VEG utani napokra ervenyes, es csak az addigi adatbol jon)."""
    rng = np.random.default_rng(seed)
    db = elt = 0
    for nev, sp in sorozat.items():
        for t in range(0, n - 1, lepes):
            mod = sp["napi"].copy()
            mod[t + 1:] = mod[t + 1:] * rng.uniform(0.3, 3.0, n - t - 1)
            if sp["egesz"]:
                mod = np.round(mod)
            res, _ = futtat(mod, sp["gordulo"], sp["r3"], veg_i)
            for k, c in res.items():
                db += t + 1
                elt += int((c[:t + 1] != orig[nev][k][:t + 1]).sum())
    return db, elt


def osszevet(sajat: pd.DataFrame, fajl: Path):
    """Napra pontos osszevetes a monitor CSV-jevel. Visszaad: (sorok, elteres)."""
    ref = pd.read_csv(fajl, dtype={"datum": str})
    m = ref.merge(sajat, on=["datum", "sorozat"], how="outer", suffixes=("_ref", "_uj"),
                  indicator=True)
    hiany = int((m["_merge"] != "both").sum())
    b = m[m["_merge"] == "both"]
    elt = hiany
    for c in ("ertek", "alapnapok", "alapszint", "elteres", "kuszob"):
        a1 = pd.to_numeric(b[f"{c}_ref"], errors="coerce").round(4)
        a2 = pd.to_numeric(b[f"{c}_uj"], errors="coerce").round(4)
        elt += int((~((a1 == a2) | (a1.isna() & a2.isna()))).sum())
    elt += int((b["jelzes_ref"] != b["jelzes_uj"]).sum())
    return len(ref), int((b["jelzes_ref"] != b["jelzes_uj"]).sum()), elt


CIMKE = {1: "szokatlanul magas", -1: "szokatlanul alacsony", 0: "normál",
         NINCS: "nincs alapszint"}


# --- Kiertekeles -------------------------------------------------------------

def teves_riasztas(cl, napok):
    """Jelzett nap / ertekelt nap x 30 a megadott napokon."""
    v = cl[napok]
    v = v[v != NINCS]
    return len(v), int((v != 0).sum()), (30 * (v != 0).sum() / len(v)) if len(v) else np.nan


def kappa(a, b):
    a, b = np.asarray(a), np.asarray(b)
    kat = np.union1d(a, b)
    po = float(np.mean(a == b))
    pe = float(sum(np.mean(a == k) * np.mean(b == k) for k in kat))
    return po, (po - pe) / (1 - pe) if pe < 1 else np.nan


def heti_bootstrap(blokk, ertek, nevezo, rng, B=BOOT_B, szorzo=1.0):
    """Blokk-bootstrap: `blokk` cimkek szerint egesz blokkokat huz vissza-
    tevessel; a statisztika szorzo x sum(ertek) / sum(nevezo)."""
    df = pd.DataFrame({"b": blokk, "e": ertek, "n": nevezo}).groupby("b")[["e", "n"]].sum()
    e, n = df["e"].to_numpy(float), df["n"].to_numpy(float)
    idx = rng.integers(0, len(df), size=(B, len(df)))
    st = szorzo * e[idx].sum(1) / np.maximum(n[idx].sum(1), 1)
    return float(np.percentile(st, 2.5)), float(np.percentile(st, 97.5)), len(df)


def placebo(x, naptar, kiel_i, eredet):
    """2 napos osszevont relativ elteres: (x1+x2)/(b1+b2) - 1, minden
    egymast koveto napparra, ahol mindket napnak van alapszintje."""
    _, b = elteres(x)
    ok = ~np.isnan(x) & ~np.isnan(b)
    sorok = []
    for t in range(len(x) - 1):
        if ok[t] and ok[t + 1]:
            sorok.append({"kezd": naptar[t], "hetnap": date.fromisoformat(naptar[t]).weekday(),
                          "elteres2": (x[t] + x[t + 1]) / (b[t] + b[t + 1]) - 1,
                          "atfed_kiel": abs(t - kiel_i) <= 1, "kiel": t == kiel_i})
    p = pd.DataFrame(sorok)
    if p.empty or not p["kiel"].any():
        return None, p
    kv = float(p.loc[p.kiel, "elteres2"].iloc[0])
    ki = {"eredet": eredet, "kiel_elteres2": kv}
    for nev, maszk in [("minden_2napos", ~p.atfed_kiel),
                       ("szerda_csutortok", ~p.atfed_kiel & (p.hetnap == 2))]:
        v = p.loc[maszk, "elteres2"].to_numpy()
        ki[f"{nev}_N"] = len(v)
        ki[f"{nev}_rang"] = int(1 + (v > kv).sum())                    # 1 = legnagyobb
        ki[f"{nev}_p_felso"] = (1 + (v >= kv).sum()) / (len(v) + 1)
        ki[f"{nev}_p_ketoldali"] = (1 + (np.abs(v) >= abs(kv)).sum()) / (len(v) + 1)
        ki[f"{nev}_median"] = float(np.median(v)) if len(v) else np.nan
    return ki, p


# --- Abrak -------------------------------------------------------------------

SZIN = {"kek": "#2a78d6", "narancs": "#eb6834", "aqua": "#1baf7a",
        "szurke": "#8a8984", "tinta": "#0b0b0b", "halvany": "#c9c8c2"}


def plt_init():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({"font.size": 9, "axes.spines.top": False,
                         "axes.spines.right": False, "axes.grid": True,
                         "grid.color": "#e6e5e0", "grid.linewidth": 0.6,
                         "axes.edgecolor": "#8a8984", "axes.titlesize": 10})
    return plt


def abra_kuszob(palya: pd.DataFrame, ut: Path):
    plt = plt_init()
    import matplotlib.dates as mdates
    nevek = list(dict.fromkeys(palya["sorozat"]))
    fig, axs = plt.subplots(2, 3, figsize=(13, 7), sharex=True)
    for ax, nev in zip(axs.flat, nevek):
        g = palya[palya.sorozat == nev]
        d = pd.to_datetime(g["datum"])
        ax.scatter(d, g["elteres"].abs() * 100, s=6, color=SZIN["halvany"],
                   label="|eltérés| (napi)", zorder=1)
        ax.plot(d, g["kuszob_retro"] * 100, color=SZIN["szurke"], lw=1.5, ls=":",
                label="retrospektív (teljes idősor)")
        ax.plot(d, g["kuszob_bovulo"] * 100, color=SZIN["kek"], lw=2,
                label="walk-forward, bővülő ablak")
        ax.plot(d, g["kuszob_rogzitett"] * 100, color=SZIN["narancs"], lw=2, ls="--",
                label="walk-forward, rögzített (jún–júl)")
        ax.axvspan(pd.Timestamp(KIEL[0]), pd.Timestamp(KIEL[1]) + pd.Timedelta(days=1),
                   color=SZIN["tinta"], alpha=0.08, lw=0)
        ax.set_title(nev)
        ax.set_ylabel("küszöb / |eltérés| (%)")
        ax.set_ylim(0, max(60, float(np.nanmax(g["kuszob_bovulo"] * 100)) + 5))
        ax.xaxis.set_major_locator(mdates.MonthLocator())
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%m-%d"))
    axs[0, 0].legend(fontsize=7, loc="upper left")
    fig.suptitle("A jelzési küszöb pályája (k = 2; szürke sáv: Kiel-lezárás, 07-15–16)")
    fig.tight_layout()
    fig.savefig(ut, dpi=150)
    plt.close(fig)


def abra_roc(roc: pd.DataFrame, ajanlott: dict, ut: Path):
    plt = plt_init()
    esetek = [("kiel", f"2 napos, ±30% esemény (Kiel-méret)"),
              ("gyenge", f"7 napos, ±10% esemény (gyenge, tartós)")]
    fig, axs = plt.subplots(2, 3, figsize=(13, 7.5), sharex=True, sharey=True)
    for j, nev in enumerate(KAPU_SOROZATOK):
        for i, (eset, cim) in enumerate(esetek):
            ax = axs[i, j]
            for cs, szin, cimke in [("R1", SZIN["kek"], "napi érték, k-rács (R0/R1)"),
                                    ("R3", SZIN["narancs"], "7 napos összeg, k-rács (R3)"),
                                    ("R4", SZIN["aqua"], "CUSUM, h-rács (R4)")]:
                # a parameter sorrendjeben kotjuk ossze (k / h novekvo)
                g = roc[(roc.sorozat == nev) & (roc.csalad == cs)].sort_values("param")
                ax.plot(g["fa30"], g[f"eszl_{eset}"] * 100, marker="o", ms=4, lw=2,
                        color=szin, label=cimke)
            r0 = roc[(roc.sorozat == nev) & (roc.csalad == "R1") & (roc.param == KUSZOB_SZORZO)]
            ax.scatter(r0["fa30"], r0[f"eszl_{eset}"] * 100, s=90, facecolor="none",
                       edgecolor=SZIN["tinta"], lw=1.5, zorder=5, label="jelenlegi (k = 2)")
            for _, r in roc[(roc.sorozat == nev) & (roc.csalad == "R1")
                            & roc.param.isin([1.5, 2.5, 3.0])].iterrows():
                ax.annotate(f"k={r.param:g}", (r.fa30, r[f'eszl_{eset}'] * 100),
                            textcoords="offset points", xytext=(4, -10), fontsize=7,
                            color="#52514e")
            ax.set_title(f"{nev} – {cim}", fontsize=9)
            if i == 1:
                ax.set_xlabel("téves riasztás / 30 nap (módosítatlan adat)")
            if j == 0:
                ax.set_ylabel("észlelési arány (%)")
            ax.set_ylim(-3, 103)
    axs[0, 0].legend(fontsize=7, loc="lower right")
    fig.suptitle("Észlelés vs. téves riasztás (walk-forward, közös értékelési ablak)")
    fig.tight_layout()
    fig.savefig(ut, dpi=150)
    plt.close(fig)


def abra_keses(inj: pd.DataFrame, ut: Path):
    plt = plt_init()
    fig, axs = plt.subplots(1, 3, figsize=(13, 4), sharey=False)
    for ax, L in zip(axs, INJ_L):
        adat, cimkek = [], []
        for m in INJ_M:
            g = inj[(inj.L == L) & np.isclose(inj.m, m) & (inj.keses >= 0)]
            adat.append(g["keses"].to_numpy())
            n = len(inj[(inj.L == L) & np.isclose(inj.m, m)])
            cimkek.append(f"{m:.0%}\n{len(g)}/{n}")
        bp = ax.boxplot(adat, tick_labels=cimkek, patch_artist=True, widths=0.5,
                        medianprops={"color": SZIN["tinta"], "lw": 1.5})
        for b in bp["boxes"]:
            b.set_facecolor(SZIN["kek"])
            b.set_alpha(0.55)
        ax.axhspan(-0.5, L - 0.5, color=SZIN["narancs"], alpha=0.08, lw=0)
        ax.set_title(f"{L} napos esemény (narancs sáv: az esemény napjai)")
        ax.set_xlabel("nagyság; észlelt / összes injektálás")
        ax.set_ylabel("késés (nap; 0 = az esemény első napja)")
        ax.set_ylim(-0.5, L + UTOABLAK - 0.5)
    fig.suptitle("Észlelési késés – R0 walk-forward, a három kapu-sorozat, mindkét irány")
    fig.tight_layout()
    fig.savefig(ut, dpi=150)
    plt.close(fig)


def abra_placebo(plac: dict, ut: Path):
    plt = plt_init()
    nevek = list(plac)
    fig, axs = plt.subplots(2, 4, figsize=(15, 7))
    for ax, nev in zip(axs.flat, nevek):
        ki, p = plac[nev]
        v = p.loc[~p.atfed_kiel, "elteres2"] * 100
        sz = p.loc[~p.atfed_kiel & (p.hetnap == 2), "elteres2"] * 100
        ax.hist(v, bins=30 if len(v) < 300 else 60, color=SZIN["halvany"],
                edgecolor="white", lw=0.5, label="minden 2 napos ablak")
        ax.hist(sz, bins=30 if len(v) < 300 else 60, range=(v.min(), v.max()),
                color=SZIN["kek"], alpha=0.8, edgecolor="white", lw=0.5,
                label="szerda–csütörtök párok")
        ax.axvline(ki["kiel_elteres2"] * 100, color=SZIN["narancs"], lw=2.5,
                   label="Kiel 07-15–16")
        ax.set_title(f"{nev}\nKiel {ki['kiel_elteres2']:+.1%}, rang "
                     f"{ki['minden_2napos_rang']}/{ki['minden_2napos_N'] + 1}, "
                     f"p={ki['minden_2napos_p_felso']:.3f}", fontsize=8.5)
        ax.set_xlabel("2 napos relatív eltérés (%)")
        ax.set_ylabel("ablak")
    for ax in list(axs.flat)[len(nevek):]:
        ax.axis("off")
    axs[0, 0].legend(fontsize=7)
    fig.suptitle("Placebo-teszt: a Kiel-ablak eltérése a saját idősor 2 napos ablakai között")
    fig.tight_layout()
    fig.savefig(ut, dpi=150)
    plt.close(fig)


# --- Fo program --------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--monitor", type=Path, default=MONITOR, help="monitor CSV-k (csak olvas)")
    ap.add_argument("--portwatch", type=Path, default=PORTWATCH)
    ap.add_argument("--ki", type=Path, default=BACKTEST)
    ap.add_argument("--bootstrap", type=int, default=BOOT_B)
    args = ap.parse_args()
    args.ki.mkdir(parents=True, exist_ok=True)
    ido0 = time.time()
    rng = np.random.default_rng(SEED)
    pd.set_option("display.width", 200)
    pd.set_option("display.max_columns", 30)

    tabla, s, tort, resz, mt, ms = beolvas(args.monitor)
    print(f"Beolvasva: kapuvonal_napi {len(tabla):,} sor, atkelesek_reszletes {len(resz):,} sor, "
          f"merules_tortenet {len(tort):,} sor; {len(s)} nap ({s.index.min()} - {s.index.max()})")

    # ===== 1. REPRODUKCIO =====================================================
    print("\n=== 1. Reprodukcio (ellenorzes) ===")
    rep = []
    ref_mt = pd.read_csv(args.monitor / megrakottsag.NAPI.name, dtype={"datum": str})
    kulcs = ["datum", "kapu", "irany", "csoport"]
    mm = ref_mt.merge(mt, on=kulcs, how="outer", suffixes=("_ref", "_uj"), indicator=True)
    e_mt = int((mm["_merge"] != "both").sum())
    for c in ("atkeles", "ertekelheto", "megrakott", "volumenindex", "megrakott_arany"):
        a1, a2 = mm[f"{c}_ref"].astype(float), mm[f"{c}_uj"].astype(float)
        e_mt += int((~(np.isclose(a1, a2) | (a1.isna() & a2.isna()))).sum())
    rep.append({"ellenorzes": "megrakottsag_napi.csv ujraszamolva (memoriaban)",
                "sorok": len(ref_mt), "jelzes_elteres": "", "barmely_mezo_elteres": e_mt})

    j_mon, kusz_mon, _ = monitor.jelzesek(s)
    n, dj, de = osszevet(j_mon, args.monitor / "jelzesek.csv")
    rep.append({"ellenorzes": "monitor.jelzesek() vs jelzesek.csv", "sorok": n,
                "jelzes_elteres": dj, "barmely_mezo_elteres": de})
    jm_mon, kuszm_mon, _ = monitor.jelzesek(ms)
    n, dj, de = osszevet(jm_mon, args.monitor / "jelzesek_megrakottsag.csv")
    rep.append({"ellenorzes": "monitor.jelzesek(gordulo) vs jelzesek_megrakottsag.csv",
                "sorok": n, "jelzes_elteres": dj, "barmely_mezo_elteres": de})

    # sajat motor, folytonos naptaron
    naptar = pd.date_range(s.index.min(), s.index.max()).strftime("%Y-%m-%d").tolist()
    adatos = set(s.index)
    veg_i = naptar.index(TANULO_VEG)
    kiel_i = naptar.index(KIEL[0])
    assert date.fromisoformat(KIEL[0]).weekday() == 2, "a Kiel-ablak elso napja nem szerda"
    sorozat = {}
    for nev in KAPU_SOROZATOK:
        sorozat[nev] = {"napi": s[nev].reindex(naptar).to_numpy(dtype=float),
                        "gordulo": False, "egesz": True, "r3": True}
    for nev, (v, egesz) in napi_megrakottsag(mt, naptar, adatos).items():
        sorozat[nev] = {"napi": v, "gordulo": True, "egesz": egesz, "r3": False}
    # a napi alap gorditve = a monitor gordulo sorozata?
    e_g = 0
    for nev in ms.columns:
        g = pd.Series(ertekek(sorozat[nev]["napi"], True), index=naptar).dropna()
        e_g += int((g.reindex(ms.index).to_numpy() != ms[nev].to_numpy()).sum()) \
            + abs(len(g) - len(ms))
    rep.append({"ellenorzes": "napi megrakottsagi alap 7 napra gorditve vs gordulo_sorozatok()",
                "sorok": int(ms.size), "jelzes_elteres": "", "barmely_mezo_elteres": e_g})
    sajat = []
    for nev, sp in sorozat.items():
        cl, e, b, kusz = retro(ertekek(sp["napi"], sp["gordulo"]))
        sajat.append(pd.DataFrame({"datum": naptar, "sorozat": nev,
                                   "jelzes_uj": [CIMKE[int(c)] for c in cl]}))
    sajat = pd.concat(sajat)
    for fajl in ("jelzesek.csv", "jelzesek_megrakottsag.csv"):
        ref = pd.read_csv(args.monitor / fajl, dtype={"datum": str})
        m = ref.merge(sajat, on=["datum", "sorozat"], how="left")
        rep.append({"ellenorzes": f"sajat vektorizalt motor (retrospektiv) vs {fajl}",
                    "sorok": len(ref), "jelzes_elteres": int((m.jelzes != m.jelzes_uj).sum()),
                    "barmely_mezo_elteres": int(m.jelzes_uj.isna().sum())})
    rep = pd.DataFrame(rep)
    rep.to_csv(args.ki / "reprodukcio.csv", index=False, encoding="utf-8")
    print(rep.to_string(index=False))
    if (pd.to_numeric(rep["barmely_mezo_elteres"]) > 0).any():
        print("!! A reprodukcio NEM egyezik - a tovabbi szamok nem a monitor szabalyat merik.")

    # ===== 2. WALK-FORWARD ====================================================
    print("\n=== 2. Walk-forward vs. retrospektiv (R0, k = 2) ===")
    orig, allap, palya, wf = {}, {}, [], []
    for nev, sp in sorozat.items():
        res, tortc = futtat(sp["napi"], sp["gordulo"], sp["r3"], veg_i, allapot=True)
        orig[nev], allap[nev] = res, tortc
        x = ertekek(sp["napi"], sp["gordulo"])
        cr, e, b, kr = retro(x)
        m = mad_palya(e)
        m28 = mad_palya(e, min_db=MIN_TANULO_ERZEKENYSEG)
        cw = res[("R1", KUSZOB_SZORZO)]
        cf = res[("R0fix", KUSZOB_SZORZO)]
        c28 = osztalyoz(e, KUSZOB_SZORZO * MAD_SKALA * m28)
        mf = m.copy()
        mf[veg_i + 1:] = mad(e[:veg_i + 1][~np.isnan(e[:veg_i + 1])])
        palya.append(pd.DataFrame({
            "datum": naptar, "sorozat": nev, "ertek": x, "alapszint": b, "elteres": e,
            "kuszob_retro": kr, "kuszob_bovulo": KUSZOB_SZORZO * MAD_SKALA * m,
            "kuszob_rogzitett": KUSZOB_SZORZO * MAD_SKALA * mf,
            "jelzes_retro": cr, "jelzes_bovulo": cw, "jelzes_rogzitett": cf,
            "jelzes_bovulo28": c28}))
        for valt, c in [("bovulo (min. 21 nap)", cw), ("rogzitett (jun-jul)", cf),
                        ("bovulo (min. 28 nap)", c28)]:
            ok = (c != NINCS) & (cr != NINCS)
            nap = np.flatnonzero(ok)
            _, jr, far = teves_riasztas(cr, nap)
            _, jw, faw = teves_riasztas(c, nap)
            elt = np.flatnonzero(ok & (c != cr))
            wf.append({"sorozat": nev, "valtozat": valt, "napok": len(nap),
                       "elso_nap": naptar[nap[0]] if len(nap) else "",
                       "jelzes_retro": jr, "jelzes_wf": jw, "elter_nap": len(elt),
                       "elter_arany": len(elt) / len(nap) if len(nap) else np.nan,
                       "fa30_retro": far, "fa30_wf": faw,
                       "kuszob_retro": kr,
                       "kuszob_wf_utolso": KUSZOB_SZORZO * MAD_SKALA * m[-1],
                       "kuszob_wf_min": np.nanmin(KUSZOB_SZORZO * MAD_SKALA * m),
                       "kuszob_wf_max": np.nanmax(KUSZOB_SZORZO * MAD_SKALA * m),
                       "elter_napok": " ".join(f"{naptar[i][5:]}({int(cr[i]):+d}>{int(c[i]):+d})"
                                               for i in elt)})
    palya = pd.concat(palya, ignore_index=True)
    palya.round(5).to_csv(args.ki / "kuszob_palya.csv", index=False, encoding="utf-8")
    wf = pd.DataFrame(wf)
    wf.round(4).to_csv(args.ki / "walkforward.csv", index=False, encoding="utf-8")
    print(wf.drop(columns=["elter_napok"]).round(3).to_string(index=False))
    print("Eltero napok (retro > walk-forward osztaly):")
    for r in wf.itertuples():
        if r.elter_nap:
            print(f"  {r.sorozat} / {r.valtozat}: {r.elter_napok}")
    kielp = palya[palya.datum.isin([KIEL[0], KIEL[1], "2026-07-17"])]
    print("Kiel-napok (elteres; retro / bovulo / rogzitett osztaly):")
    for r in kielp.itertuples():
        print(f"  {r.datum} {r.sorozat:<32} {r.elteres:+.3f}  {int(r.jelzes_retro):+d} / "
              f"{int(r.jelzes_bovulo):+d} / {int(r.jelzes_rogzitett):+d}"
              .replace("-9", "nincs"))

    # ===== 2b. A WALK-FORWARD MOTOR ELLENORZESE ==============================
    print("\n=== 2b. A walk-forward motor ellenorzese ===")
    t_ell = time.time()
    db, elt = nulla_injektalas(sorozat, orig, allap, veg_i, len(naptar))
    rep.loc[len(rep)] = {"ellenorzes": "nulla-injektalas: reszleges futas (t0, CUSUM-allapot) "
                         "= teljes futas", "sorok": db, "jelzes_elteres": elt,
                         "barmely_mezo_elteres": elt}
    db, elt = elorenezes_teszt(sorozat, orig, veg_i, len(naptar))
    rep.loc[len(rep)] = {"ellenorzes": f"elorenezes-teszt: a t utani napok elrontasa nem "
                         f"valtoztat a [0, t] osztalyokon (minden {ELORE_LEPES}. t)",
                         "sorok": db, "jelzes_elteres": elt, "barmely_mezo_elteres": elt}
    rep.to_csv(args.ki / "reprodukcio.csv", index=False, encoding="utf-8")
    print(rep.tail(2).to_string(index=False))
    print(f"({time.time() - t_ell:.0f} mp)")

    # A megrakottsagi sorozatok napi erteke maga is retrospektiv parameterbol
    # (Otsu-kuszob a teljes idoszakbol) jon: mennyit szamit, ha az is csak a
    # jun-jul tanuloidoszakbol szamolodna?
    kusz_t, mt_t = otsu_tanulo(resz, tort, TANULO_VEG)
    kusz_f = megrakottsag.kuszobok(megrakottsag.relativ(resz, megrakottsag.hajo_max(tort)))
    otsu_sor = []
    for nev, (v, egesz) in napi_megrakottsag(mt_t, naptar, adatos).items():
        sp = sorozat[nev]
        c_t = futtat(v, True, False, veg_i)[0][("R1", KUSZOB_SZORZO)]
        c_f = orig[nev][("R1", KUSZOB_SZORZO)]
        ok = (c_t != NINCS) & (c_f != NINCS)
        otsu_sor.append({"sorozat": nev, "napok": int(ok.sum()),
                         "napi_ertek_elter_nap": int(np.sum(v != sp["napi"])),
                         "jelzes_teljes_otsu": int((c_f[ok] != 0).sum()),
                         "jelzes_junjul_otsu": int((c_t[ok] != 0).sum()),
                         "elter_nap": int((c_t[ok] != c_f[ok]).sum())})
    otsu_df = pd.DataFrame(otsu_sor)
    otsu_df.to_csv(args.ki / "otsu_tanulo.csv", index=False, encoding="utf-8")
    print("Megrakottsagi Otsu-kuszob: teljes idoszak "
          + ", ".join(f"{k} {v:.4f}" for k, v in kusz_f.items())
          + f"; csak {TANULO_VEG}-ig "
          + ", ".join(f"{k} {v:.4f}" for k, v in kusz_t.items()))
    print(otsu_df.to_string(index=False))

    # ===== 3-4. SZABALYVALTOZATOK + INJEKTALAS ================================
    print("\n=== 3-4. Szabalyvaltozatok, szintetikus esemeny-injektalas ===")
    kozos = {}
    for nev, res in orig.items():
        ok = np.ones(len(naptar), bool)
        for k in FO_SZABALYOK + [("R1", k) for k in K_ROC] + [("R4", h) for h in CUSUM_H_RACS]:
            if k in res:
                ok &= res[k] != NINCS
        kozos[nev] = ok

    rek = []
    t_inj = time.time()
    db_inj = 0
    for nev, sp in sorozat.items():
        res0 = orig[nev]
        barmely = np.zeros(len(naptar), bool)
        for c in res0.values():
            barmely |= c != NINCS
        for st in np.flatnonzero(barmely):
            for L in INJ_L:
                t1 = st + L + UTOABLAK
                if t1 > len(naptar):
                    continue
                for m in INJ_M:
                    for irany in (1, -1):
                        mod = sp["napi"].copy()
                        mod[st:st + L] = mod[st:st + L] * (1 + irany * m)
                        if sp["egesz"]:
                            mod[st:st + L] = np.round(mod[st:st + L])
                        init = allap[nev][:, :, st]
                        res, _ = futtat(mod, sp["gordulo"], sp["r3"], veg_i, st, t1,
                                        cusum_init=(init[0], init[1]))
                        db_inj += 1
                        for k, c in res.items():
                            if res0[k][st] == NINCS:
                                continue
                            o = res0[k][st:t1]
                            hit = np.flatnonzero((c[st:t1] == irany) & (o != irany))
                            rek.append((nev, k[0], k[1], st, L, m, irany,
                                        int(hit[0]) if len(hit) else -1, bool(kozos[nev][st])))
    inj = pd.DataFrame(rek, columns=["sorozat", "csalad", "param", "kezd_i", "L", "m",
                                     "irany", "keses", "kozos"])
    inj["eszlelt"] = inj["keses"] >= 0
    print(f"Injektalt esemenyek: {db_inj:,} (sorozat x kezdonap x L x m x irany), "
          f"{len(inj):,} szabaly-kimenet, {time.time() - t_inj:.0f} mp")

    # teves riasztas a modositatlan adaton, sajat es kozos ablakon
    fa = []
    kiel_kornyek = np.array([d in KIEL_KORNYEK for d in naptar])
    for nev, res in orig.items():
        for k, c in res.items():
            sajat_nap = np.flatnonzero(c != NINCS)
            for ablak, napok in [("sajat", sajat_nap), ("kozos", np.flatnonzero(kozos[nev]))]:
                nn, jj, f30 = teves_riasztas(c, napok)
                f30k = teves_riasztas(c, napok[~kiel_kornyek[napok]])[2]
                fa.append({"sorozat": nev, "csalad": k[0], "param": k[1], "ablak": ablak,
                           "napok": nn, "jelzett": jj, "fa30": f30, "fa30_kiel_nelkul": f30k,
                           "elso_nap": naptar[napok[0]] if len(napok) else ""})
    fa = pd.DataFrame(fa)

    def osszesit(df, csop):
        g = df.groupby(csop)
        o = g.agg(n=("eszlelt", "size"), eszlelt=("eszlelt", "sum")).reset_index()
        o["arany"] = o["eszlelt"] / o["n"]
        kes = df[df.eszlelt].groupby(csop)["keses"].agg(["min", "median", "max"]).reset_index()
        kes.columns = list(csop) + ["keses_min", "keses_median", "keses_max"]
        return o.merge(kes, on=csop, how="left")

    csop = ["sorozat", "csalad", "param", "irany", "m", "L"]
    inj_t = pd.concat([osszesit(inj, csop).assign(ablak="sajat"),
                       osszesit(inj[inj.kozos], csop).assign(ablak="kozos")])
    inj_t["szabaly"] = [szabaly_nev((a, b)) for a, b in zip(inj_t.csalad, inj_t.param)]
    inj_t.round(4).to_csv(args.ki / "injektalas.csv", index=False, encoding="utf-8")

    # fo osszevetesi tabla (kozos ablak): FA/30, Kiel-eset, 30% atlag, gyenge eset
    fo = []
    for nev in sorozat:
        for k in FO_SZABALYOK:
            if k not in orig[nev]:
                continue
            for ablak in ("kozos", "sajat"):
                d = inj[(inj.sorozat == nev) & (inj.csalad == k[0]) & (inj.param == k[1])]
                if ablak == "kozos":
                    d = d[d.kozos]
                f = fa[(fa.sorozat == nev) & (fa.csalad == k[0]) & (fa.param == k[1])
                       & (fa.ablak == ablak)].iloc[0]
                kie = d[(d.L == KIEL_L) & np.isclose(d.m, KIEL_M)]
                m30 = d[np.isclose(d.m, 0.3)]
                gy = d[(d.L == GYENGE_L) & np.isclose(d.m, GYENGE_M)]
                fo.append({"sorozat": nev, "szabaly": szabaly_nev(k), "ablak": ablak,
                           "napok": f.napok, "elso_nap": f.elso_nap, "fa30": f.fa30,
                           "fa30_kiel_nelkul": f.fa30_kiel_nelkul,
                           "kiel_eset_eszl": kie.eszlelt.mean(),
                           "kiel_eset_n": len(kie),
                           "kiel_eset_keses_median": kie.loc[kie.eszlelt, "keses"].median(),
                           "m30_eszl": m30.eszlelt.mean(),
                           "gyenge_eszl": gy.eszlelt.mean(),
                           "osszes_eszl": d.eszlelt.mean()})
    fo = pd.DataFrame(fo)
    fo.round(4).to_csv(args.ki / "szabalyok.csv", index=False, encoding="utf-8")
    print("\nSzabalyvaltozatok a kozos ertekelesi ablakon (walk-forward):")
    print(fo[fo.ablak == "kozos"].drop(columns=["ablak", "kiel_eset_n"]).round(3)
          .to_string(index=False))

    # R0 fo eredmenytabla: m x L, iranyonkent, sajat ablak, a harom kapu-sorozat
    r0 = inj[(inj.csalad == "R1") & (inj.param == KUSZOB_SZORZO)]
    r0t = osszesit(r0, ["sorozat", "irany", "m", "L"])
    print("\nR0 (walk-forward, k = 2) eszlelesi arany, sajat ablak (sorozat x irany x m x L):")
    piv = r0t.pivot_table(index=["sorozat", "irany", "L"], columns="m", values="arany")
    print(piv.round(2).to_string())

    # ROC (kozos ablak)
    roc = []
    for nev in sorozat:
        for cs, params in [("R1", K_ROC), ("R3", K_ROC), ("R4", CUSUM_H_RACS)]:
            for p in params:
                if (cs, p) not in orig[nev]:
                    continue
                d = inj[(inj.sorozat == nev) & (inj.csalad == cs) & (inj.param == p) & inj.kozos]
                f = fa[(fa.sorozat == nev) & (fa.csalad == cs) & (fa.param == p)
                       & (fa.ablak == "kozos")].iloc[0]
                roc.append({"sorozat": nev, "csalad": cs, "param": p, "fa30": f.fa30,
                            "eszl_kiel": d[(d.L == KIEL_L) & np.isclose(d.m, KIEL_M)].eszlelt.mean(),
                            "eszl_gyenge": d[(d.L == GYENGE_L)
                                             & np.isclose(d.m, GYENGE_M)].eszlelt.mean(),
                            "eszl_m30": d[np.isclose(d.m, 0.3)].eszlelt.mean(),
                            "eszl_osszes": d.eszlelt.mean()})
    roc = pd.DataFrame(roc)
    roc.round(4).to_csv(args.ki / "roc.csv", index=False, encoding="utf-8")

    # ajanlott munkapont: R1 csalad, SAJAT ablak (tobb adat), legnagyobb k,
    # amely a Kiel-esetet >= CEL_ESZLELES aranyban eszleli
    ajanl = []
    for nev in sorozat:
        best = None
        for k in K_ROC:
            d = inj[(inj.sorozat == nev) & (inj.csalad == "R1") & (inj.param == k)
                    & (inj.L == KIEL_L) & np.isclose(inj.m, KIEL_M)]
            f = fa[(fa.sorozat == nev) & (fa.csalad == "R1") & (fa.param == k)
                   & (fa.ablak == "sajat")].iloc[0]
            if d.eszlelt.mean() >= CEL_ESZLELES:
                best = {"sorozat": nev, "ajanlott_k": k, "kiel_eset_eszl": d.eszlelt.mean(),
                        "fa30": f.fa30}
        r0f = fa[(fa.sorozat == nev) & (fa.csalad == "R1") & (fa.param == KUSZOB_SZORZO)
                 & (fa.ablak == "sajat")].iloc[0]
        r0d = inj[(inj.sorozat == nev) & (inj.csalad == "R1") & (inj.param == KUSZOB_SZORZO)
                  & (inj.L == KIEL_L) & np.isclose(inj.m, KIEL_M)]
        sor = {"sorozat": nev, "ajanlott_k": np.nan, "kiel_eset_eszl": np.nan, "fa30": np.nan}
        sor.update(best or {})
        sor.update({"k2_kiel_eset_eszl": r0d.eszlelt.mean(), "k2_fa30": r0f.fa30})
        ajanl.append(sor)
    ajanl = pd.DataFrame(ajanl)
    ajanl.round(4).to_csv(args.ki / "munkapont.csv", index=False, encoding="utf-8")
    print(f"\nAjanlott munkapont (R1 csalad, sajat ablak; a legnagyobb k, amelynel a "
          f"{KIEL_L} napos ±{KIEL_M:.0%} eset eszlelese >= {CEL_ESZLELES:.0%}):")
    print(ajanl.round(3).to_string(index=False))

    # ===== 5. PLACEBO ========================================================
    print("\n=== 5. Placebo-teszt a Kiel-ablakra ===")
    plac = {}
    for nev, sp in sorozat.items():
        ki, p = placebo(ertekek(sp["napi"], sp["gordulo"]), naptar, kiel_i, "AIS 2026-06-01 -")
        plac[nev] = (ki, p)
    pw = pd.read_csv(args.portwatch, dtype={"date": str})
    print(f"PortWatch: {len(pw):,} sor beolvasva, {pw.portname.nunique()} chokepoint; "
          f"dan szoros: {sorted(n for n in pw.portname.unique() if 'resund' in n or 'Belt' in n)}")
    o = pw[pw.portname == PW_NEV].sort_values("date").set_index("date")
    pw_naptar = pd.date_range(o.index.min(), o.index.max()).strftime("%Y-%m-%d").tolist()
    pw_tot = o["n_total"].reindex(pw_naptar).to_numpy(dtype=float)
    ki, p = placebo(pw_tot, pw_naptar, pw_naptar.index(KIEL[0]),
                    f"PortWatch {pw_naptar[0]} -")
    plac["PortWatch Øresund (2019–)"] = (ki, p)
    pl = pd.DataFrame([dict(sorozat=n, **v[0]) for n, v in plac.items()])
    pl.round(4).to_csv(args.ki / "placebo.csv", index=False, encoding="utf-8")
    print(pl.round(3).to_string(index=False))

    # ===== 6. PORTWATCH-EGYEZES ===============================================
    print("\n=== 6. Kulso referencia: PortWatch Oresund ===")
    ker = tabla[(tabla.kapu == "Øresund") & (tabla.csoport == "Tanker")] \
        .groupby("datum")["atkeles"].sum()
    kozos_nap = [d for d in naptar if d in set(o.index)]
    pw_eredm = []
    for par, sajat_s, pw_osz in [("kereskedelmi vs n_total", s["Øresund"], "n_total"),
                                 ("tanker vs n_tanker", ker, "n_tanker")]:
        a = sajat_s.reindex(kozos_nap).fillna(0).to_numpy(float)
        b = o[pw_osz].reindex(kozos_nap).to_numpy(float)
        for mod in ("retrospektiv", "walk-forward"):
            if mod == "retrospektiv":
                ca, ea, _, ka = retro(a)
                cb, eb, _, kb = retro(b)
            else:
                ea, _ = elteres(a)
                eb, _ = elteres(b)
                ka = KUSZOB_SZORZO * MAD_SKALA * mad_palya(ea)
                kb = KUSZOB_SZORZO * MAD_SKALA * mad_palya(eb)
                ca, cb = osztalyoz(ea, ka), osztalyoz(eb, kb)
                ka, kb = np.nanmean(ka), np.nanmean(kb)
            ok = (ca != NINCS) & (cb != NINCS)
            po3, k3 = kappa(ca[ok], cb[ok])
            po2, k2 = kappa(ca[ok] != 0, cb[ok] != 0)
            pw_eredm.append({"par": par, "mod": mod, "napok": int(ok.sum()),
                             "elso": kozos_nap[np.flatnonzero(ok)[0]], "utolso": kozos_nap[-1],
                             "kuszob_sajat": ka, "kuszob_pw": kb,
                             "jelzes_sajat": int((ca[ok] != 0).sum()),
                             "jelzes_pw": int((cb[ok] != 0).sum()),
                             "mindketto": int(((ca[ok] != 0) & (cb[ok] != 0)).sum()),
                             "egyezes_3oszt": po3, "kappa_3oszt": k3,
                             "egyezes_jelez": po2, "kappa_jelez": k2,
                             "r_elteres": float(np.corrcoef(ea[ok], eb[ok])[0, 1]),
                             "kiel_sajat": " ".join(f"{ea[kozos_nap.index(d)]:+.3f}" for d in KIEL),
                             "kiel_pw": " ".join(f"{eb[kozos_nap.index(d)]:+.3f}" for d in KIEL)})
    pw_eredm = pd.DataFrame(pw_eredm)
    pw_eredm.round(4).to_csv(args.ki / "portwatch_egyezes.csv", index=False, encoding="utf-8")
    print(pw_eredm.round(3).to_string(index=False))
    print("(Nagy-Balti-öv / Storebaelt a PortWatch-ban nincs, ld. a fenti listat.)")

    # ===== 7. BLOKK-BOOTSTRAP ================================================
    print(f"\n=== 7. Heti blokk-bootstrap (R0 walk-forward, sajat ablak, B = {args.bootstrap}) ===")
    het = np.array([date.fromisoformat(d).isocalendar()[1] for d in naptar])
    bs = []
    for nev in sorozat:
        c = orig[nev][("R1", KUSZOB_SZORZO)]
        napok = np.flatnonzero(c != NINCS)
        _, jj, f30 = teves_riasztas(c, napok)
        lo, hi, nb = heti_bootstrap(het[napok], (c[napok] != 0).astype(float),
                                    np.ones(len(napok)), rng, args.bootstrap, 30.0)
        bs.append({"sorozat": nev, "mutato": "teves riasztas / 30 nap", "ertek": f30,
                   "ci_also": lo, "ci_felso": hi, "blokkok": nb, "n": len(napok)})
        d = r0[(r0.sorozat == nev)]
        for cim, dd in [("eszleles, m = 30% (minden L, mindket irany)", d[np.isclose(d.m, 0.3)]),
                        (f"eszleles, Kiel-eset ({KIEL_L} nap, ±{KIEL_M:.0%})",
                         d[(d.L == KIEL_L) & np.isclose(d.m, KIEL_M)])]:
            lo, hi, nb = heti_bootstrap(het[dd.kezd_i.to_numpy()], dd.eszlelt.astype(float),
                                        np.ones(len(dd)), rng, args.bootstrap)
            bs.append({"sorozat": nev, "mutato": cim, "ertek": dd.eszlelt.mean(),
                       "ci_also": lo, "ci_felso": hi, "blokkok": nb, "n": len(dd)})
    bs = pd.DataFrame(bs)
    bs.round(4).to_csv(args.ki / "bootstrap.csv", index=False, encoding="utf-8")
    print(bs.round(3).to_string(index=False))

    # ===== Abrak ============================================================
    abra_kuszob(palya, args.ki / "kuszob_palya.png")
    abra_roc(roc, ajanl, args.ki / "roc.png")
    abra_keses(r0[r0.sorozat.isin(KAPU_SOROZATOK)], args.ki / "keses.png")
    abra_placebo(plac, args.ki / "placebo.png")

    # ===== 8. Osszefoglalo ===================================================
    print("\n=== Osszefoglalo ===")
    print(f"Feldolgozva: {len(naptar)} naptari nap ({naptar[0]} - {naptar[-1]}), "
          f"{len(sorozat)} sorozat ({len(KAPU_SOROZATOK)} kapu + "
          f"{len(sorozat) - len(KAPU_SOROZATOK)} megrakottsagi), "
          f"{db_inj:,} injektalt esemeny; PortWatch Oresund {len(pw_naptar)} nap.")
    print(f"Reprodukcio + motor-ellenorzes: {int(pd.to_numeric(rep.barmely_mezo_elteres).sum())} elteres "
          f"{len(rep)} ellenorzesben.")
    fo_r0 = fo[(fo.ablak == "sajat") & (fo.szabaly == "R0 (k=2)")]
    print("R0 (walk-forward, sajat ablak):")
    print(fo_r0[["sorozat", "napok", "elso_nap", "fa30", "fa30_kiel_nelkul", "kiel_eset_eszl",
                 "m30_eszl",
                 "gyenge_eszl"]].round(3).to_string(index=False))
    print(f"\n-> {args.ki} (reprodukcio, walkforward, kuszob_palya, otsu_tanulo, szabalyok, "
          f"injektalas, roc, munkapont, placebo, portwatch_egyezes, bootstrap .csv; 4 PNG)")
    print(f"Futasi ido: {time.time() - ido0:.0f} mp")
    return 0


if __name__ == "__main__":
    sys.exit(main())
