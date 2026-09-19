"""
AIS napi adatfajlok letoltese. Az AIS-rendszer uzemeltetese a DMA-tol
atkerult a Dan Katasztrofavedelmi Hatosaghoz (Beredskabsstyrelsen); a
korabban hasznalt web.ais.dk cim lejart/rossz tanusitvanyt ad (ld.
naplo.md, 2026-09-18 21:50 es 22:05-os bejegyzes).

Forras es fajlnev-mintazat ellenorizve (2026-09-18, a hallgato altal, a
sajat bongeszojeben - valodi konyvtarlistazas, tobb honapnyi napi ZIP-pel):
    http://aisdata.ais.dk/aisdk-YYYY-MM-DD.zip
peldaul: http://aisdata.ais.dk/aisdk-2026-09-05.zip
Figyelem: http, nem https - a szerver nem szolgaltat TLS-t ezen a cimen.

Hasznalat:
    # argumentum nelkul: a megbeszelt csucsforgalmi ablak toltodik le
    # (2026-07-15 - 2026-07-16, ld. naplo.md 2026-09-18 21:20-as bejegyzes -
    # Kiel-csatorna tervezett teljes lezarasa, a hajok Danian at kerulik meg)
    python letoltes.py

    # egyetlen nap
    python letoltes.py 2026-09-05

    # datumtartomany (mindket vegpont zarolag)
    python letoltes.py 2026-09-01 2026-09-07

    # celkonyvtar megadasa (alapertelmezett: ./data)
    python letoltes.py 2026-09-05 --cel data

Fuggosegek: requests
    pip install requests
"""

import argparse
import sys
import time
import zipfile
from datetime import date, timedelta
from pathlib import Path

import requests

from utak import ADAT

# --- Parameterek ---------------------------------------------------------

BASE_URL = "http://aisdata.ais.dk"
FILENAME_FORMAT = "aisdk-{date}.zip"  # date = ISO YYYY-MM-DD

# A DMA szerver nagy fajlokat szolgal ki (tobb szaz MB naponta) - streamelve,
# darabokban irjuk lemezre, hogy ne kelljen az egeszet memoriaba tolteni.
CHUNK_BYTES = 1024 * 1024  # 1 MB

MAX_KISERLET = 3
KISERLET_VARAKOZAS_MP = 5

TIMEOUT_MP = 60

# Alapertelmezett letoltesi ablak, ha nem adunk meg datumot: a Kiel-csatorna
# 2026.07.15 17:00 - 07.16 09:00 kozotti tervezett teljes lezarasa, amikor a
# hajok varhatoan Danian at (Great Belt / Fehmarnbelt) kerultek at - ld.
# naplo.md, 2026-09-18 21:20-as bejegyzes.
ALAP_KEZDO_DATUM = date(2026, 7, 15)
ALAP_VEG_DATUM = date(2026, 7, 16)


# --- Segedfuggvenyek -------------------------------------------------------

def datum_tartomany(kezdo: date, veg: date):
    """Napi datumok kezdo..veg kozott, mindket vegponttal zarolag."""
    if veg < kezdo:
        sys.exit(f"A veg datum ({veg}) korabbi, mint a kezdo datum ({kezdo}).")
    napok = (veg - kezdo).days
    for i in range(napok + 1):
        yield kezdo + timedelta(days=i)


def ellenoriz_zip(path: Path) -> bool:
    """True, ha a ZIP nem serult (CRC ellenorzes)."""
    try:
        with zipfile.ZipFile(path) as zf:
            return zf.testzip() is None
    except zipfile.BadZipFile:
        return False


def letolt_egy_napot(nap: date, celkonyvtar: Path, felulir: bool) -> str:
    """
    Letolti egy nap AIS ZIP-jet. Visszateres: 'kesz', 'mar_megvan' vagy 'hiba'.
    """
    fajlnev = FILENAME_FORMAT.format(date=nap.isoformat())
    url = f"{BASE_URL}/{fajlnev}"
    cel_path = celkonyvtar / fajlnev

    if cel_path.exists() and not felulir:
        if ellenoriz_zip(cel_path):
            print(f"  {fajlnev}: mar megvan, ervenyes ZIP - kihagyva")
            return "mar_megvan"
        print(f"  {fajlnev}: mar megvan, de serult ZIP - ujratoltom")

    for kiserlet in range(1, MAX_KISERLET + 1):
        try:
            with requests.get(url, stream=True, timeout=TIMEOUT_MP) as resp:
                if resp.status_code == 404:
                    print(f"  {fajlnev}: 404 - ehhez a naphoz nincs adat a szerveren")
                    return "hiba"
                resp.raise_for_status()

                ideiglenes = cel_path.with_suffix(".part")
                meret = 0
                with open(ideiglenes, "wb") as f:
                    for darab in resp.iter_content(chunk_size=CHUNK_BYTES):
                        f.write(darab)
                        meret += len(darab)

            if not ellenoriz_zip(ideiglenes):
                raise zipfile.BadZipFile("CRC hiba letoltes utan")

            ideiglenes.rename(cel_path)
            print(f"  {fajlnev}: kesz ({meret / 1_048_576:.1f} MB)")
            return "kesz"

        except (requests.RequestException, zipfile.BadZipFile) as e:
            print(f"  {fajlnev}: hiba a(z) {kiserlet}. kiserletnel: {e}")
            if kiserlet < MAX_KISERLET:
                time.sleep(KISERLET_VARAKOZAS_MP)

    print(f"  {fajlnev}: nem sikerult {MAX_KISERLET} kiserlet utan sem")
    return "hiba"


# --- Fovonal ---------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="AIS napi adatfajlok letoltese a web.ais.dk/aisdata/-rol."
    )
    parser.add_argument(
        "kezdo_datum", nargs="?", default=None,
        help=(
            "Kezdo datum, formatum: YYYY-MM-DD. Ha elmarad, az alapertelmezett "
            f"csucsforgalmi ablak toltodik le: {ALAP_KEZDO_DATUM} - {ALAP_VEG_DATUM}."
        ),
    )
    parser.add_argument(
        "veg_datum", nargs="?", default=None,
        help="Veg datum (ha nincs megadva, csak a kezdo_datum toltodik le)",
    )
    parser.add_argument(
        "--cel", default=ADAT,
        help="Celkonyvtar a letoltott ZIP-eknek (alapertelmezett: ./data)",
    )
    parser.add_argument(
        "--felulir", action="store_true",
        help="Mar letezo, ervenyes fajlok ujratoltese is",
    )
    args = parser.parse_args()

    if args.kezdo_datum is None:
        kezdo, veg = ALAP_KEZDO_DATUM, ALAP_VEG_DATUM
        print(
            f"Nincs datum megadva - alapertelmezett csucsforgalmi ablak: "
            f"{kezdo} - {veg} (Kiel-csatorna lezaras, ld. naplo.md).\n"
        )
    else:
        try:
            kezdo = date.fromisoformat(args.kezdo_datum)
        except ValueError:
            sys.exit(f"Ervenytelen kezdo datum: {args.kezdo_datum} (vart formatum: YYYY-MM-DD)")

        if args.veg_datum:
            try:
                veg = date.fromisoformat(args.veg_datum)
            except ValueError:
                sys.exit(f"Ervenytelen veg datum: {args.veg_datum} (vart formatum: YYYY-MM-DD)")
        else:
            veg = kezdo

    celkonyvtar = Path(args.cel)
    celkonyvtar.mkdir(parents=True, exist_ok=True)

    napok = list(datum_tartomany(kezdo, veg))
    print(f"Letoltendo napok: {len(napok)} ({napok[0]} - {napok[-1]})")
    print(f"Celkonyvtar: {celkonyvtar.resolve()}\n")

    eredmenyek = {"kesz": 0, "mar_megvan": 0, "hiba": 0}
    for nap in napok:
        eredmeny = letolt_egy_napot(nap, celkonyvtar, args.felulir)
        eredmenyek[eredmeny] += 1

    print(
        f"\nOsszesites: {eredmenyek['kesz']} uj letoltes, "
        f"{eredmenyek['mar_megvan']} mar megvolt, "
        f"{eredmenyek['hiba']} hiba "
        f"({len(napok)} nap osszesen)"
    )
    if eredmenyek["hiba"]:
        sys.exit(1)


if __name__ == "__main__":
    main()
