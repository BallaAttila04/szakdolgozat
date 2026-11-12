"""
A dan szorosok napi idosoranak kitoltese 2025. januar 1. es 2026. majus 31. kozott
(a 4. abra also paneljehez).

NEM a Hormuz-merce resze: az elemzes (76 nap) es a robusztussagi minta (258 nap)
valtozatlan. Ez a szkript csak azokat a napokat dolgozza fel, amelyek egyik
korabbi futasban sem szerepeltek, ugyanazzal a koddal (hormuz_napi.main()),
de kulon mappaba:
  outputs/hormuz/kitoltes/            napi kimenetek (napi.csv, atkelesek.csv ...)
  outputs/tarolo_hormuz_kitoltes/     szurt Parquet (Tanker, Cargo) - alapbol a nap vegen
                                      torolve, mert a laptopon keves a hely; --szurt-megtart
                                      kapcsoloval megmarad
Sorrend: elobb a 2025. junius - december kozotti res, utana a tobbi hianyzo nap.

Windowson a futas idejere megakadalyozza, hogy a gep alvo allapotba lepjen
(SetThreadExecutionState; a rendszerbeallitasokat nem modositja). A fedel
lecsukasa ettol fuggetlenul altathatja a gepet.

Hasznalat:
    python hormuz_kitoltes.py minta
    python hormuz_kitoltes.py feldolgoz --kozvetlen-zip
    python hormuz_kitoltes.py feldolgoz --kozvetlen-zip --szurt-megtart
    python hormuz_kitoltes.py feldolgoz --osszesito
"""

import sys
from datetime import date, timedelta

import pandas as pd

from utak import KIMENET
from hormuz_kozos import HORMUZ

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)
except AttributeError:
    pass

KI = HORMUZ / "kitoltes"
SZURT = KIMENET / "tarolo_hormuz_kitoltes"
KEZDET, VEG = date(2025, 1, 1), date(2026, 5, 31)
ELSOBBSEG = (date(2025, 6, 1), date(2025, 12, 31))


def kesz_napok():
    kesz = set()
    for ut in (HORMUZ / "feldolgozas.csv", HORMUZ / "kiterjesztett" / "feldolgozas.csv"):
        if ut.exists():
            a = pd.read_csv(ut, dtype={"nap": str})
            kesz |= set(a.loc[a.statusz == "kesz", "nap"])
    return kesz


def minta():
    kesz = kesz_napok()
    sorok = []
    d = KEZDET
    while d <= VEG:
        if d.isoformat() not in kesz:
            elso = ELSOBBSEG[0] <= d <= ELSOBBSEG[1]
            sorok.append({"nap": d.isoformat(), "ablak": "kitoltes", "elsobbseg": 0 if elso else 1})
        d += timedelta(days=1)
    m = pd.DataFrame(sorok).sort_values(["elsobbseg", "nap"])[["nap", "ablak"]]
    KI.mkdir(parents=True, exist_ok=True)
    m.to_csv(KI / "mintanapok.csv", index=False, encoding="utf-8")
    print(f"Mar kesz: {len(kesz)} nap; kitoltendo: {len(m)} nap -> {KI / 'mintanapok.csv'}")
    return 0


def ebren_tart(be: bool):
    if sys.platform != "win32":
        return
    import ctypes
    ES_CONTINUOUS, ES_SYSTEM_REQUIRED = 0x80000000, 0x00000001
    ctypes.windll.kernel32.SetThreadExecutionState(
        ES_CONTINUOUS | (ES_SYSTEM_REQUIRED if be else 0))


def feldolgoz(tovabbi):
    import hormuz_napi as hn
    hn.HORMUZ = KI
    hn.MINTA = KI / "mintanapok.csv"
    hn.ALLAPOT = KI / "feldolgozas.csv"
    hn.PIPELINE_NAPLO = KI / "pipeline_napok.csv"
    hn.SZURT_TAROLO = SZURT
    megtart = "--szurt-megtart" in tovabbi
    tovabbi = [t for t in tovabbi if t != "--szurt-megtart"]
    if not megtart:
        eredeti = hn.utofeldolgozas

        def utofeldolgozas(nap, pq, args, *maradek):
            ki = eredeti(nap, pq, args, *maradek)   # az atkelesek es a validalas valtozatlan
            hn.szurt_ut(args.szurt, nap).unlink(missing_ok=True)
            return ki
        hn.utofeldolgozas = utofeldolgozas
    sys.argv = ["hormuz_napi.py"] + tovabbi
    ebren_tart(True)
    try:
        return hn.main()
    finally:
        ebren_tart(False)


if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] not in ("minta", "feldolgoz"):
        sys.exit(__doc__)
    sys.exit(minta() if sys.argv[1] == "minta" else feldolgoz(sys.argv[2:]))
