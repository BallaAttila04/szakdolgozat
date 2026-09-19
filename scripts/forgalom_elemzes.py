"""
AIS forgalmi profil - csucsnapok vs atlagos nap osszehasonlitasa a dan
szorosok bounding boxaban (Great Belt / Fehmarnbelt / nyugati Balti,
54.5-56.5 N, 10.0-13.0 E).

Hipotezis (ld. naplo.md, 2026-09-18 21:20-as bejegyzes): a Kiel-csatorna
2026.07.15-16-i tervezett teljes lezarasa idejen a dan szorosokban
megnott a hajoforgalom, mert a hajok Danian at kerultek meg. Ez a szkript
oranankenti egyedi hajoszamot (MMSI) es uzenetszamot szamol napi AIS ZIP
fajlokbol, hogy a csucsnapokat egy "atlagos" naphoz lehessen viszonyitani.

Hasznalat:
    python forgalom_elemzes.py \
        --csucs data/aisdk-2026-07-15.zip data/aisdk-2026-07-16.zip \
        --atlag aisdk-2026-09-05.zip

Fuggosegek: pandas, matplotlib
"""

import argparse
import re
import sys
import zipfile
from collections import defaultdict
from pathlib import Path

import pandas as pd
import matplotlib.pyplot as plt

from utak import KIMENET

LAT_MIN, LAT_MAX = 54.5, 56.5
LON_MIN, LON_MAX = 10.0, 13.0

COLS = ["# Timestamp", "MMSI", "Latitude", "Longitude"]
CHUNK = 500_000

DATE_RE = re.compile(r"aisdk-(\d{4}-\d{2}-\d{2})")


def _member_reader(zf: zipfile.ZipFile):
    members = [
        n for n in zf.namelist()
        if n.lower().endswith((".csv", ".txt", ".dat"))
    ]
    if not members:
        sys.exit(f"A ZIP-ben nem talaltam CSV/TXT adatfajlt.")
    # Nem toltjuk memoriaba a teljes tartalmat (zf.read) - a nagy
    # csucsnapi fajlok (>1 GB tomoritve) igy sem futnak ki a memorabol.
    return zf.open(members[0])


def elemez_nap(path: Path) -> pd.DataFrame:
    """Egy napi AIS ZIP oranankenti forgalmi profilja a bounding boxban.

    Visszateres: DataFrame [hour, messages, unique_ships], 24 sor (0-23).
    """
    ora_uzenet = defaultdict(int)
    ora_mmsi = defaultdict(set)
    total_rows = 0
    kept_rows = 0

    with zipfile.ZipFile(path) as zf:
        with _member_reader(zf) as raw:
            reader = pd.read_csv(
                raw,
                usecols=lambda c: c.strip() in COLS,
                chunksize=CHUNK,
                low_memory=False,
                encoding="utf-8-sig",
            )
            for i, chunk in enumerate(reader):
                chunk.columns = [c.strip() for c in chunk.columns]
                total_rows += len(chunk)

                m = (
                    chunk["Latitude"].between(LAT_MIN, LAT_MAX)
                    & chunk["Longitude"].between(LON_MIN, LON_MAX)
                )
                chunk = chunk[m]

                if len(chunk):
                    ts = pd.to_datetime(
                        chunk["# Timestamp"], format="%d/%m/%Y %H:%M:%S",
                        errors="coerce",
                    )
                    chunk = chunk.assign(ts=ts).dropna(subset=["ts"])
                    kept_rows += len(chunk)

                    for h, grp in chunk.groupby(chunk["ts"].dt.hour):
                        ora_uzenet[h] += len(grp)
                        ora_mmsi[h].update(grp["MMSI"].tolist())

                print(f"  chunk {i:>3}: {total_rows:>12,} sor beolvasva, "
                      f"{kept_rows:>9,} megtartva a bounding boxban", end="\r")

    print()
    if not ora_uzenet:
        sys.exit(f"Nincs talalat a bounding boxban: {path}")

    sorok = []
    for h in range(24):
        sorok.append({
            "hour": h,
            "messages": ora_uzenet.get(h, 0),
            "unique_ships": len(ora_mmsi.get(h, ())),
        })
    return pd.DataFrame(sorok)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--csucs", nargs="+", required=True,
                     help="Csucsforgalmi (Kiel-lezarasi) napok ZIP utvonalai")
    ap.add_argument("--atlag", nargs="+", required=True,
                     help="Atlagos (viszonyitasi) napok ZIP utvonalai")
    ap.add_argument("--kontroll", nargs="*", default=[],
                     help="Kontrollnapok: azonos honap es azonos het napja, "
                          "mint a csucsnapok, de lezaras nelkul - ezek "
                          "valasztjak szet a szezonalitast a lezaras hatasatol")
    args = ap.parse_args()

    napok = (
        [(p, "csucs") for p in args.csucs]
        + [(p, "kontroll") for p in args.kontroll]
        + [(p, "atlag") for p in args.atlag]
    )

    osszesito = []
    profilok = {}

    for path_str, label in napok:
        path = Path(path_str)
        m = DATE_RE.search(path.name)
        datum = m.group(1) if m else path.stem
        print(f"\n=== {datum} ({label}): {path} ===")

        profil = elemez_nap(path)
        profil.insert(0, "date", datum)
        profil.insert(1, "label", label)
        profilok[datum] = profil

        napi_uzenet = profil["messages"].sum()
        csucsora = profil.loc[profil["unique_ships"].idxmax()]
        print(f"Napi osszes uzenet a bounding boxban: {napi_uzenet:,}")
        print(f"Csucs ora: {int(csucsora['hour']):02d}:00, "
              f"{int(csucsora['unique_ships'])} egyedi hajo")

        osszesito.append({
            "date": datum,
            "label": label,
            "total_messages": int(napi_uzenet),
            "peak_hour": int(csucsora["hour"]),
            "peak_hour_ships": int(csucsora["unique_ships"]),
            "avg_hourly_ships": round(profil["unique_ships"].mean(), 1),
        })

    reszletes = pd.concat(profilok.values(), ignore_index=True)
    reszletes.to_csv(KIMENET / "forgalmi_profil_oranankent.csv", index=False)
    print("\n-> forgalmi_profil_oranankent.csv kiirva (oranankenti bontas)")

    osszesito_df = pd.DataFrame(osszesito)
    osszesito_df.to_csv(KIMENET / "forgalmi_osszefoglalo.csv", index=False)
    print("-> forgalmi_osszefoglalo.csv kiirva (napi osszesites)")

    print("\n" + osszesito_df.to_string(index=False))

    # --- Abra: oranankenti egyedi hajoszam napi bontasban ---
    fig, ax = plt.subplots(figsize=(10, 6))
    for datum, profil in profilok.items():
        label = profil["label"].iloc[0]
        stilusok = {
            "csucs": dict(linewidth=2.4, marker="o"),
            "kontroll": dict(linewidth=2.0, linestyle="-.", marker="s",
                             markersize=4),
            "atlag": dict(linewidth=1.4, linestyle="--", marker="."),
        }
        ax.plot(profil["hour"], profil["unique_ships"], label=f"{datum} ({label})",
                **stilusok[label])

    ax.set_xlabel("Ora (nap kozben)")
    ax.set_ylabel("Egyedi hajok szama (MMSI)")
    ax.set_title("AIS forgalom - dan szorosok - csucsnapok vs atlagos nap")
    ax.set_xticks(range(0, 24, 2))
    ax.legend(loc="best")
    ax.grid(alpha=0.3)
    fig.savefig(KIMENET / "forgalmi_profil.png", dpi=150, bbox_inches="tight")
    print("-> forgalmi_profil.png kiirva")


if __name__ == "__main__":
    main()
