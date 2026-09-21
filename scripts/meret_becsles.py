"""
Mekkora helyet foglalna egy hosszabb idoszak AIS-adata?

Ket dolgot rak ossze:

  1. A LETOLTENDO meretet MERI, nem becsli: HTTP HEAD keressel lekeri a napi
     ZIP-ek Content-Length ertekét a szerverrol. Ez pontos szam.

  2. A TAROLT meretet a sajat benchmarkunk aranyaibol szamolja. Ezek ket
     valodi napon mert ertekek (2026-07-15 es 07-16), ZIP-merethez
     viszonyitva. Ez mar becsles - a napok osszetetele elter, ezert a
     szkript a ket nap aranyabol also-felso savot is kiir.

MIT NE OLVASS KI BELOLE: a dead reckoning sora NEM ugyanarra az adatra
vonatkozik, mint a tobbi. Az bounding boxra szurt (a sorok ~29,6%-a) es csak
6 oszlopot tart meg. Ezert kisebb nagysagrenddel - de nem ugyanazt tarolja.
A sor ettol nem hamis, csak mast mer, es ezt a kiiras is kimondja.

Hasznalat:
    python meret_becsles.py 2026-07-01 2026-07-31
    python meret_becsles.py 2026-07-01 2026-07-31 --bajt 23860254786
"""

import argparse
import sys
from datetime import date, timedelta

import requests

# A Windows-konzol kodlapja nem birja a magyar ekezeteket
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except AttributeError:
    pass

BASE_URL = "http://aisdata.ais.dk"

# --- Mert horgonypontok (ld. szamok.md, "Adattarolas-benchmark") -----------
# (nap, ZIP bajt, CSV MiB, Parquet MiB snappy, DuckDB MiB)
HORGONY = [
    ("2026-07-15", 1002076005, 6248.0, 1061.2, 1537.3),
    ("2026-07-16", 1036257489, 6137.7, 1059.5, 1507.8),
]

# Trajektoria-tomorites, CSAK a 2026-07-15 napon merve:
# bounding box + 6 oszlop + zstd. Nem vetheto ossze a fenti sorokkal.
DR_NAP_ZIP = 1002076005
DR_TELJES_MIB = 84.3      # tomoritetlen, de mar bbox + 6 oszlop + zstd
DR_50M_MIB = 13.2         # dead reckoning, 50 m garantalt hibakorlat

MIB = 1048576
GIB = 1073741824


def aranyok():
    """Tarolasi forma -> (min arany, max arany) a ZIP merethez viszonyitva."""
    ki = {}
    for cimke, idx in [("Kicsomagolt CSV", 2), ("Parquet (snappy)", 3),
                       ("DuckDB natív tábla", 4)]:
        ertekek = [h[idx] * MIB / h[1] for h in HORGONY]
        ki[cimke] = (min(ertekek), max(ertekek))
    return ki


def napok(tol: date, ig: date):
    d = tol
    while d <= ig:
        yield d
        d += timedelta(days=1)


def zip_meretek(tol: date, ig: date):
    """HTTP HEAD minden napra. Visszaad: {datum: bajt}, es a hianyzok listaja."""
    meretek, hianyzo = {}, []
    munkamenet = requests.Session()
    for d in napok(tol, ig):
        nev = f"aisdk-{d.isoformat()}.zip"
        try:
            v = munkamenet.head(f"{BASE_URL}/{nev}", timeout=20,
                                allow_redirects=True)
            hossz = v.headers.get("Content-Length")
            if v.status_code == 200 and hossz:
                meretek[d] = int(hossz)
                print(f"  {d}  {int(hossz)/MIB:>9,.1f} MiB")
            else:
                hianyzo.append(d)
                print(f"  {d}  nincs meg (HTTP {v.status_code})")
        except requests.RequestException as e:
            hianyzo.append(d)
            print(f"  {d}  hiba: {type(e).__name__}")
    return meretek, hianyzo


def sav(bajt, also, felso, egyseg=GIB, mertek="GiB"):
    a, f = bajt * also / egyseg, bajt * felso / egyseg
    if abs(f - a) < 0.05:
        return f"{a:,.1f} {mertek}"
    return f"{a:,.1f} – {f:,.1f} {mertek}"


def main():
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("tol", help="Kezdonap, ev-ho-nap")
    ap.add_argument("ig", help="Utolso nap, ev-ho-nap")
    ap.add_argument("--bajt", type=int, default=None,
                    help="Korabban lemert osszes ZIP bajt - ezzel nem kerdezi "
                         "ujra a szervert")
    ap.add_argument("--napok", type=int, default=None,
                    help="A --bajt-hoz tartozo napok szama")
    args = ap.parse_args()

    try:
        tol, ig = date.fromisoformat(args.tol), date.fromisoformat(args.ig)
    except ValueError as e:
        sys.exit(f"Rossz datum: {e}")
    if ig < tol:
        sys.exit("Az utolso nap korabbi a kezdonapnal.")

    if args.bajt is not None:
        osszes = args.bajt
        n = args.napok or (ig - tol).days + 1
        print(f"Megadott, korabban lemert ertek: {osszes:,} bajt, {n} nap")
        hianyzo = []
    else:
        print(f"Napi ZIP meretek lekerese ({BASE_URL}):")
        meretek, hianyzo = zip_meretek(tol, ig)
        if not meretek:
            sys.exit("Egyetlen napot sem sikerult lekerdezni.")
        osszes = sum(meretek.values())
        n = len(meretek)
        legkisebb = min(meretek.values()) / MIB
        legnagyobb = max(meretek.values()) / MIB
        print(f"\n  {n} nap, napi {legkisebb:,.0f}–{legnagyobb:,.0f} MiB "
              f"(atlag {osszes/n/MIB:,.0f} MiB)")

    print(f"\n{'='*66}")
    print(f"IDOSZAK: {tol} – {ig}   ({n} nap)")
    print(f"{'='*66}\n")

    print(f"LETOLTENDO (mert, pontos):")
    print(f"  Nyers ZIP-ek                {osszes/GIB:>10,.1f} GiB"
          f"   {osszes/n/MIB:>7,.0f} MiB/nap\n")

    print("TAROLT MERET tarolasi forma szerint (a benchmark aranyaibol):")
    for cimke, (also, felso) in aranyok().items():
        napi_a = osszes / n * also / MIB
        napi_f = osszes / n * felso / MIB
        napi = (f"{napi_a:,.0f}" if abs(napi_f - napi_a) < 5
                else f"{napi_a:,.0f}–{napi_f:,.0f}")
        print(f"  {cimke:<26} {sav(osszes, also, felso):>14}"
              f"   {napi:>7} MiB/nap")

    # --- Dead reckoning: kulon blokk, mert mas adatot tarol ---
    dr_teljes = DR_TELJES_MIB * MIB / DR_NAP_ZIP
    dr_50 = DR_50M_MIB * MIB / DR_NAP_ZIP
    print(f"\nCSAK A DAN SZOROSOK (bounding box, 6 oszlop, zstd):")
    print(f"  Parquet, tomorites nelkul   "
          f"{osszes*dr_teljes/GIB:>10,.2f} GiB   "
          f"{osszes/n*dr_teljes/MIB:>7,.0f} MiB/nap")
    print(f"  + dead reckoning (50 m)     "
          f"{osszes*dr_50/GIB:>10,.2f} GiB   "
          f"{osszes/n*dr_50/MIB:>7,.0f} MiB/nap")

    print(f"\n  FIGYELEM: ez a ket sor NEM ugyanazt tarolja, mint a fentiek.")
    print(f"  Bounding boxra szurt (a sorok ~29,6%-a) es 6 oszlopos. Ha a")
    print(f"  teljes lefedettseg vagy a tobbi oszlop kell, ez nem eleg.")

    # --- Atmeneti helyigeny ---
    p_also, p_felso = aranyok()["Parquet (snappy)"]
    egyuttes = osszes * (1 + p_felso)
    print(f"\nATMENETI HELYIGENY a konverzio kozben "
          f"(ZIP + Parquet egyszerre): {egyuttes/GIB:,.1f} GiB")
    print(f"A kicsomagolt CSV-t nem kell megtartani, de a konverziohoz")
    print(f"naponta egyszerre kell a ZIP es a belole keszulo fajl.")

    if hianyzo:
        print(f"\n{len(hianyzo)} nap nem volt lekerdezheto, ezek kimaradtak "
              f"a szamolasbol:")
        print("  " + ", ".join(d.isoformat() for d in hianyzo))

    print(f"\nA becsles alapja ket valodi nap merese (2026-07-15, 07-16).")
    print(f"A napok osszetetele elter, ezert a fenti savok tajekoztatoak.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
