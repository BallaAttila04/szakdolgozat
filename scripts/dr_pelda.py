"""
Szemleltetes: mit tart meg es mit dob el a dead reckoning, egyetlen hajon.

A `trajektoria_tomorites.py` a teljes napra dolgozik es osszesitett szamokat
ad. Ez a szkript EGY hajo egy szakaszat nyomtatja ki sorrol sorra, hogy
lathato legyen, pontosan milyen pontok esnek ki es mekkora hibaval.

Ugyanazt a `dead_reckoning_maszk` fuggvenyt hasznalja, mint az eles szkript -
nem masolat, hanem import. Igy amit itt latsz, az tenyleg az, ami fut.

Hasznalat:
    python dr_pelda.py outputs/tomorites_parquet/aisdk-2026-07-15_teljes.parquet
    python dr_pelda.py <parquet> --mmsi 219000000 --kuszob 50 --sorok 40
    python dr_pelda.py <parquet> --keres kanyar     # kanyarodo hajot keres
"""

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from trajektoria_tomorites import dead_reckoning_maszk

# A tablazat ennyi sort mutat alapbol - annyi, hogy lassz egy mintat, de
# meg elolvashato maradjon.
ALAP_SOROK = 30

# Csak ennel gyorsabban halado hajot valasztunk szemleltetesre (median SOG).
# Kikotott hajon a dead reckoning trivialis, nem mutat semmit.
MIN_SOG_CSOMO = 5.0


def hajot_valaszt(df, mod):
    """Szemleltetesre alkalmas hajot keres.

    egyenes: sok pontja van es a COG alig valtozik -> sok eldobott pont
    kanyar:  sok pontja van es a COG sokat valtozik -> sok megtartott pont
    """
    jeloltek = []
    for mmsi, g in df.groupby("MMSI", sort=False):
        if len(g) < 200:
            continue
        # Csak tenylegesen HALADO hajo szemleltet barmit is. Egy kikotott
        # hajonal a dead reckoning trivialisan mukodik (a joslat "all egy
        # helyben"), abbol nem latszik a modszer lenyege.
        sog = g["SOG"].to_numpy()
        sog_erv = sog[(sog == sog) & (sog < 102.3)]
        if len(sog_erv) < 50 or np.median(sog_erv) < MIN_SOG_CSOMO:
            continue
        cog = g["COG"].to_numpy()
        cog = cog[(cog == cog) & (cog < 360.0)]
        if len(cog) < 50:
            continue
        # Korkoros szorast nezunk, hogy a 359 -> 1 atmenet ne szamitson ugrasnak
        szog = np.radians(cog)
        R = np.hypot(np.mean(np.cos(szog)), np.mean(np.sin(szog)))
        egyenesseg = R                      # 1 = tokeletesen egyenes
        jeloltek.append((mmsi, len(g), egyenesseg))

    if not jeloltek:
        sys.exit("Nem talaltam eleg hosszu palyat a fajlban.")

    if mod == "kanyar":
        jeloltek.sort(key=lambda t: t[2])              # legkisebb egyenesseg
    else:
        jeloltek.sort(key=lambda t: (-t[2], -t[1]))    # legegyenesebb, hosszu
    return jeloltek[0]


def main():
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("parquet")
    ap.add_argument("--mmsi", type=int, default=None,
                    help="Konkret hajo; enelkul automatikusan valaszt")
    ap.add_argument("--keres", choices=["egyenes", "kanyar"], default="egyenes",
                    help="Milyen hajot keressen, ha nincs --mmsi megadva")
    ap.add_argument("--kuszob", type=float, default=50.0,
                    help="Hibakuszob meterben (alap: 50)")
    ap.add_argument("--sorok", type=int, default=ALAP_SOROK,
                    help="Hany sort irjon ki a tablazatbol")
    ap.add_argument("--tol", type=int, default=0,
                    help="Hanyadik ponttol kezdje a kiirast")
    args = ap.parse_args()

    p = Path(args.parquet)
    if not p.exists():
        sys.exit(f"Nem letezik: {p}")

    df = pd.read_parquet(p, columns=["MMSI", "ts", "Latitude", "Longitude",
                                     "SOG", "COG"])
    df = df.sort_values(["MMSI", "ts"], kind="stable")

    if args.mmsi is None:
        mmsi, db, egyenesseg = hajot_valaszt(df, args.keres)
        print(f"Automatikusan valasztott hajo ({args.keres}): MMSI {mmsi}, "
              f"{db:,} pozicio, iranytartas {egyenesseg:.3f} (1 = egyenes)")
    else:
        mmsi = args.mmsi

    g = df[df["MMSI"] == mmsi]
    if g.empty:
        sys.exit(f"Nincs ilyen MMSI a fajlban: {mmsi}")

    t_mp = (g["ts"].astype("int64") // 10**9).to_numpy()
    lat = g["Latitude"].to_numpy(dtype=float)
    lon = g["Longitude"].to_numpy(dtype=float)
    sog = g["SOG"].to_numpy(dtype=float)
    cog = g["COG"].to_numpy(dtype=float)
    m = np.full(len(g), mmsi, dtype=np.int64)

    tart, atlag_hiba, hiba_max = dead_reckoning_maszk(
        m, t_mp, lat, lon, sog, cog, args.kuszob)

    n = len(g)
    megtart = int(tart.sum())
    print(f"\nMMSI {mmsi} — {n:,} pozicio a nap folyaman, "
          f"kuszob {args.kuszob:.0f} m")
    print(f"  megtartva: {megtart:,} ({megtart/n*100:.1f}%)   "
          f"eldobva: {n-megtart:,} ({(n-megtart)/n*100:.1f}%)")
    print(f"  az eldobott pontok visszaszamolasi hibaja: "
          f"atlag {atlag_hiba:.1f} m, maximum {hiba_max:.1f} m "
          f"(a kuszob {args.kuszob:.0f} m)")

    # --- Sorrol sorra ---
    # Ujrajatsszuk a horgonykovetest, hogy a joslatot es a hibat ki tudjuk irni
    print(f"\n{'ido':<9}{'dt':>5}{'SOG':>7}{'COG':>7}"
          f"{'joslat hibaja':>15}  sors")
    print("-" * 56)

    h_lat, h_lon, h_t, h_sog, h_cog = lat[0], lon[0], t_mp[0], sog[0], cog[0]
    from trajektoria_tomorites import (CSOMO_PER_MP, METER_PER_FOK,
                                       MAX_IDORES_MP, SOG_ERVENYTELEN,
                                       COG_ERVENYTELEN)
    import math

    kiirva = 0
    for i in range(n):
        ido = pd.Timestamp(g["ts"].iloc[i]).strftime("%H:%M:%S")
        if i == 0:
            sors, hiba_sz, dt = "HORGONY (elso pont)", "", 0
        else:
            dt = t_mp[i] - h_t
            ervenyes = (h_sog == h_sog and h_cog == h_cog
                        and h_sog < SOG_ERVENYTELEN and h_cog < COG_ERVENYTELEN)
            if dt > MAX_IDORES_MP or not ervenyes:
                sors, hiba_sz = "MEGTART (idores/ervenytelen)", "-"
            else:
                tav = h_sog * CSOMO_PER_MP * dt
                irany = math.radians(h_cog)
                coslat = math.cos(math.radians(h_lat))
                j_lat = h_lat + (tav * math.cos(irany)) / METER_PER_FOK
                j_lon = h_lon + (tav * math.sin(irany)) / (METER_PER_FOK * coslat)
                dy = (lat[i] - j_lat) * METER_PER_FOK
                dx = (lon[i] - j_lon) * METER_PER_FOK * coslat
                hiba = math.hypot(dx, dy)
                hiba_sz = f"{hiba:.1f} m"
                sors = "MEGTART (uj horgony)" if hiba > args.kuszob else "eldob"

        if tart[i]:
            h_lat, h_lon, h_t = lat[i], lon[i], t_mp[i]
            h_sog, h_cog = sog[i], cog[i]

        if i >= args.tol and kiirva < args.sorok:
            print(f"{ido:<9}{dt:>4}s{sog[i]:>7.1f}{cog[i]:>7.1f}"
                  f"{hiba_sz:>15}  {sors}")
            kiirva += 1

    print("\nAmit a tomoritett fajl a kihagyott percekrol tud: a hajo az")
    print("elozo megtartott pontbol, annak sajat SOG/COG erteken haladt.")
    print("Amit NEM tud: a tenyleges kis kitereseket a kuszob alatt.")


if __name__ == "__main__":
    main()
