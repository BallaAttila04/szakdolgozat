"""
AIS megvalosithatosagi teszt - 1. lepes
Dan Tengereszeti Hatosag (DMA) napi AIS fajl betoltese, szurese, kirajzolasa.

Hasznalat:
    python scripts/ais_teszt.py data/aisdk-2026-07-15.zip
    python scripts/ais_teszt.py <zip> --pillanatkep <csv> --abra <png>

Fuggosegek: pandas, matplotlib
    pip install pandas matplotlib
"""

import argparse
import io
import os
import sys
import zipfile

import pandas as pd
import matplotlib.pyplot as plt

from utak import KIMENET

# --- Parameterek ---------------------------------------------------------

# Dan szorosok (Great Belt / Fehmarn Belt / nyugati Balti)
LAT_MIN, LAT_MAX = 54.5, 56.5
LON_MIN, LON_MAX = 10.0, 13.0

# 10 perces ablak (ezt kesobb a SAR felvetel idobelyegere kell allitani)
TIME_FROM = "12:00:00"
TIME_TO = "12:10:00"

# Csak ezeket az oszlopokat olvassuk be - a tobbi memoriat enne
COLS = [
    "# Timestamp", "MMSI", "Latitude", "Longitude",
    "Navigational status", "SOG", "COG", "Ship type", "Length", "Width",
]

CHUNK = 500_000


# --- Betoltes ------------------------------------------------------------

def _open_reader(path):
    """A CSV vagy ZIP-ben talalhato adatfilebol olvaso iterator."""
    if not os.path.exists(path):
        sys.exit(f"A fajl nem letezik: {path}")

    if path.lower().endswith(".zip"):
        with zipfile.ZipFile(path) as zf:
            members = [
                name for name in zf.namelist()
                if name.lower().endswith((".csv", ".txt", ".dat"))
            ]
            if not members:
                sys.exit(f"A ZIP-ben nem talaltam CSV/TXT adatfajlt: {path}")

            member = members[0]
            payload = zf.read(member)
            return pd.read_csv(
                io.BytesIO(payload),
                usecols=lambda c: c.strip() in COLS,
                chunksize=CHUNK,
                low_memory=False,
                encoding="utf-8-sig",
            )

    return pd.read_csv(
        path,
        usecols=lambda c: c.strip() in COLS,
        chunksize=CHUNK,
        low_memory=False,
        encoding="utf-8-sig",
    )


def load(path):
    """Chunkonkent olvas es mar olvasas kozben szur, hogy elferjen a memoriaban."""
    kept = []
    total_rows = 0

    reader = _open_reader(path)

    for i, chunk in enumerate(reader):
        chunk.columns = [c.strip() for c in chunk.columns]
        total_rows += len(chunk)

        # bounding box szures
        m = (
            chunk["Latitude"].between(LAT_MIN, LAT_MAX)
            & chunk["Longitude"].between(LON_MIN, LON_MAX)
        )
        chunk = chunk[m]

        if len(chunk):
            kept.append(chunk)

        print(f"  chunk {i:>3}: {total_rows:>12,} sor beolvasva, "
              f"{sum(len(k) for k in kept):>9,} megtartva", end="\r")

    print()
    if not kept:
        sys.exit("Nincs talalat a bounding boxban - ellenorizd a koordinatakat.")

    return pd.concat(kept, ignore_index=True)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("bemenet", help="Napi AIS ZIP vagy CSV fajl")
    ap.add_argument("--pillanatkep", default=KIMENET / "ais_pillanatkep.csv",
                    help="A 10 perces ablak hajonkenti pillanatkepe (CSV)")
    ap.add_argument("--abra", default=KIMENET / "ais_teszt.png",
                    help="A kirajzolt terkep (PNG)")
    args = ap.parse_args()

    path = args.bemenet
    print(f"Betoltes: {path}")
    df = load(path)

    # Idobelyeg: a DMA formatuma nap/honap/ev ora:perc:mp
    df["ts"] = pd.to_datetime(
        df["# Timestamp"], format="%d/%m/%Y %H:%M:%S", errors="coerce"
    )
    df = df.dropna(subset=["ts"]).copy()

    if df.empty:
        sys.exit("Nincs ervenyes idobelyeg az AIS adatokban.")

    print(f"\nBounding boxban: {len(df):,} uzenet, "
          f"{df['MMSI'].nunique():,} egyedi hajo (MMSI)")
    print(f"Idointervallum:  {df['ts'].min()} - {df['ts'].max()}")

    # --- 10 perces ablak ---
    day = df["ts"].dt.normalize().iloc[0]
    t0 = day + pd.Timedelta(TIME_FROM)
    t1 = day + pd.Timedelta(TIME_TO)
    win = df[df["ts"].between(t0, t1)]

    print(f"\n{TIME_FROM}-{TIME_TO} kozott: {len(win):,} uzenet, "
          f"{win['MMSI'].nunique():,} hajo")

    # Hajonkent egy pozicio (az ablak elso uzenete) - ez kell a SAR-parositashoz
    snap = win.sort_values("ts").groupby("MMSI").first().reset_index()
    print(f"Pillanatkep:     {len(snap):,} hajo pozicioval\n")
    print(snap[["MMSI", "ts", "Latitude", "Longitude", "SOG", "Ship type", "Length"]].head(10))

    snap.to_csv(args.pillanatkep, index=False)
    print(f"\n-> {args.pillanatkep} kiirva")

    # --- Abra ---
    fig, ax = plt.subplots(figsize=(9, 8))
    ax.scatter(df["Longitude"], df["Latitude"], s=0.05, alpha=0.15,
               color="grey", label="teljes nap")
    ax.scatter(snap["Longitude"], snap["Latitude"], s=28, color="crimson",
               edgecolor="black", linewidth=0.4,
               label=f"{TIME_FROM}-{TIME_TO} ({len(snap)} hajo)")
    ax.set_xlim(LON_MIN, LON_MAX)
    ax.set_ylim(LAT_MIN, LAT_MAX)
    ax.set_xlabel("Hosszusag")
    ax.set_ylabel("Szelesseg")
    ax.set_title("AIS - dan szorosok")
    ax.legend(loc="best", markerscale=2)
    ax.grid(alpha=0.25)
    fig.savefig(args.abra, dpi=150, bbox_inches="tight")
    print(f"-> {args.abra} kiirva")


if __name__ == "__main__":
    main()
