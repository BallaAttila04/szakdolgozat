"""
AIS trajektoria-tomorites dead reckoning modszerrel.

Otlet (ld. naplo.md): a Parquet/zstd bajtszintu tomorites, ami 2-3x-ot hoz.
A trajektoria-tomorites ezzel szemben SZEMANTIKUS: egy egyenesen, allando
sebesseggel halado hajo majdnem redundans pozicioit eldobjuk, mert azok a
megtartott pontokbol visszaszamolhatok. Az irodalom szerint ez AIS-en
87-97%-os tomoritest ad (Douglas-Peucker valtozatok, dead reckoning).

Dead reckoning elve: az utolso MEGTARTOTT pontbol (horgony) a sajat SOG/COG
ertekevel megjosoljuk, hol kene lennie a hajonak. Ha a tenyleges pozicio a
joslattol a kuszobnel jobban elter, a pontot megtartjuk es az lesz az uj
horgony; kulonben eldobjuk. Az AIS eleve tartalmazza a SOG-ot es COG-ot,
igy a sebessegvektort nem kell becsulni.

FONTOS tulajdonsag: az eldobott pontok visszaszamolasi hibaja konstrukcio
szerint a kuszob ALATT marad - vagyis a kuszob egy GARANTALT felso korlat a
pontossagra, nem atlagos hiba.

Ez vesztesegesen tomorit. A nyers reteget nem helyettesiti, csak szarmaztatott
reteg mellette.

Hasznalat:
    python trajektoria_tomorites.py data/aisdk-2026-07-15.zip
    python trajektoria_tomorites.py data/*.zip --kuszobok 10 50 100

Fuggosegek: pandas, numpy, pyarrow
"""

import argparse
import math
import sys
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd

from utak import KIMENET

# --- Parameterek ----------------------------------------------------------

# Ugyanaz a bounding box, mint a tobbi szkriptben (dan szorosok)
LAT_MIN, LAT_MAX = 54.5, 56.5
LON_MIN, LON_MAX = 10.0, 13.0

# Kuszobertekek meterben: ezek adjak a tradeoff-gorbe pontjait.
# 10 m nagyjabol a GPS-pontossag hatara; 500 m mar csak durva utvonalhoz jo.
ALAP_KUSZOBOK_M = [10, 25, 50, 100, 250, 500]

# Ha ket egymas utani uzenet kozott ennel tobb ido telt el, a joslat
# ertelmetlen (a hajo barmit csinalhatott kozben) - ilyenkor kotelezoen
# megtartjuk a pontot. 10 perc: a horgonyzo hajok ~3 perces adaskozenel
# bovebb, de meg nem enged at hosszu vetelkieseseket.
MAX_IDORES_MP = 600

# AIS "nem elerheto" jelzesek: SOG 102.3 csomo, COG 360 fok.
SOG_ERVENYTELEN = 102.3
COG_ERVENYTELEN = 360.0

# Fok -> meter atvaltas (gombi kozelites, ezeken a szelessegeken eleg pontos)
METER_PER_FOK = 111320.0
CSOMO_PER_MP = 0.514444

CHUNK = 500_000
COLS = ["# Timestamp", "MMSI", "Latitude", "Longitude", "SOG", "COG"]


# --- Betoltes ---------------------------------------------------------------

def betolt(path: Path) -> pd.DataFrame:
    """A bounding boxon beluli pontok, MMSI + ido szerint rendezve."""
    with zipfile.ZipFile(path) as zf:
        tagok = [n for n in zf.namelist()
                 if n.lower().endswith((".csv", ".txt", ".dat"))]
        if not tagok:
            sys.exit(f"Nincs CSV a ZIP-ben: {path}")

        darabok = []
        osszes = 0
        with zf.open(tagok[0]) as raw:
            olvaso = pd.read_csv(
                raw, usecols=lambda c: c.strip() in COLS, chunksize=CHUNK,
                low_memory=False, encoding="utf-8-sig",
            )
            for i, ch in enumerate(olvaso):
                ch.columns = [c.strip() for c in ch.columns]
                osszes += len(ch)
                m = (ch["Latitude"].between(LAT_MIN, LAT_MAX)
                     & ch["Longitude"].between(LON_MIN, LON_MAX))
                ch = ch[m]
                if len(ch):
                    darabok.append(ch)
                print(f"  beolvasas: {osszes:>12,} sor", end="\r")
    print()

    df = pd.concat(darabok, ignore_index=True)
    df["ts"] = pd.to_datetime(df["# Timestamp"], format="%d/%m/%Y %H:%M:%S",
                              errors="coerce")
    df = df.dropna(subset=["ts", "Latitude", "Longitude"])
    df = df.sort_values(["MMSI", "ts"], kind="stable").reset_index(drop=True)
    print(f"  bounding boxban: {len(df):,} pont, "
          f"{df['MMSI'].nunique():,} hajo")
    return df


# --- Dead reckoning ---------------------------------------------------------

def dead_reckoning_maszk(mmsi, t_mp, lat, lon, sog, cog, kuszob_m):
    """Melyik pontokat kell megtartani. Visszaadja a maszkot es a hibastatot.

    Hajonkent kulon fut: az elso pont mindig horgony, utana minden pontra
    megjosoljuk a poziciot a horgony SOG/COG ertekebol, es csak akkor tartjuk
    meg, ha a joslat a kuszobnel jobban teved.
    """
    n = len(mmsi)
    tart = np.zeros(n, dtype=bool)

    # Hajonkenti szakaszhatarok a rendezett tombben
    hatarok = np.flatnonzero(np.r_[True, mmsi[1:] != mmsi[:-1], True])

    hiba_osszeg = 0.0
    hiba_max = 0.0
    eldobott = 0

    for gi in range(len(hatarok) - 1):
        a, b = hatarok[gi], hatarok[gi + 1]
        tart[a] = True
        h_lat, h_lon, h_t, h_sog, h_cog = lat[a], lon[a], t_mp[a], sog[a], cog[a]

        for i in range(a + 1, b):
            dt = t_mp[i] - h_t
            ervenyes = (h_sog == h_sog and h_cog == h_cog
                        and h_sog < SOG_ERVENYTELEN and h_cog < COG_ERVENYTELEN)

            if dt > MAX_IDORES_MP or not ervenyes:
                tart[i] = True
                h_lat, h_lon, h_t = lat[i], lon[i], t_mp[i]
                h_sog, h_cog = sog[i], cog[i]
                continue

            tav = h_sog * CSOMO_PER_MP * dt
            irany = math.radians(h_cog)
            coslat = math.cos(math.radians(h_lat))
            j_lat = h_lat + (tav * math.cos(irany)) / METER_PER_FOK
            j_lon = h_lon + (tav * math.sin(irany)) / (METER_PER_FOK * coslat)

            dy = (lat[i] - j_lat) * METER_PER_FOK
            dx = (lon[i] - j_lon) * METER_PER_FOK * coslat
            hiba = math.hypot(dx, dy)

            if hiba > kuszob_m:
                tart[i] = True
                h_lat, h_lon, h_t = lat[i], lon[i], t_mp[i]
                h_sog, h_cog = sog[i], cog[i]
            else:
                eldobott += 1
                hiba_osszeg += hiba
                if hiba > hiba_max:
                    hiba_max = hiba

    atlag_hiba = hiba_osszeg / eldobott if eldobott else 0.0
    return tart, atlag_hiba, hiba_max


# --- Fovonal ----------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("bemenetek", nargs="+", help="Napi AIS ZIP fajlok")
    ap.add_argument("--kuszobok", nargs="+", type=float,
                    default=ALAP_KUSZOBOK_M,
                    help=f"Kuszobertekek meterben (alap: {ALAP_KUSZOBOK_M})")
    ap.add_argument("--ki", default=KIMENET / "trajektoria_tomorites.csv",
                    help="Kimeneti CSV a meresi eredmenyekkel")
    ap.add_argument("--parquet-dir", default=None,
                    help="Ha megadod, ide irja a tomoritett Parquet fajlokat "
                         "is, hogy a tenyleges fajlmeret is merheto legyen")
    args = ap.parse_args()

    sorok = []

    for bemenet_str in args.bemenetek:
        bemenet = Path(bemenet_str)
        if not bemenet.exists():
            sys.exit(f"Nem letezik: {bemenet}")

        print(f"\n=== {bemenet.name} ===")
        df = betolt(bemenet)

        mmsi = df["MMSI"].to_numpy()
        t_mp = df["ts"].astype("int64").to_numpy() / 1_000_000_000.0
        lat = df["Latitude"].to_numpy(dtype=float)
        lon = df["Longitude"].to_numpy(dtype=float)
        sog = df["SOG"].to_numpy(dtype=float)
        cog = df["COG"].to_numpy(dtype=float)
        n = len(df)

        # Viszonyitasi alap: a teljes (tomoritetlen) pontkeszlet Parquetben
        if args.parquet_dir:
            pq_dir = Path(args.parquet_dir)
            pq_dir.mkdir(parents=True, exist_ok=True)
            teljes_pq = pq_dir / f"{bemenet.stem}_teljes.parquet"
            df[["MMSI", "ts", "Latitude", "Longitude", "SOG", "COG"]].to_parquet(
                teljes_pq, index=False, compression="zstd")
            teljes_mb = teljes_pq.stat().st_size / 1_048_576
            print(f"  teljes (tomoritetlen) Parquet: {teljes_mb:,.1f} MB")
        else:
            teljes_mb = float("nan")

        for kuszob in args.kuszobok:
            tart, atlag_hiba, max_hiba = dead_reckoning_maszk(
                mmsi, t_mp, lat, lon, sog, cog, kuszob)
            megtartott = int(tart.sum())
            arany = megtartott / n

            meret_mb = float("nan")
            if args.parquet_dir:
                pq = Path(args.parquet_dir) / f"{bemenet.stem}_dr{int(kuszob)}m.parquet"
                df.loc[tart, ["MMSI", "ts", "Latitude", "Longitude", "SOG", "COG"]] \
                  .to_parquet(pq, index=False, compression="zstd")
                meret_mb = pq.stat().st_size / 1_048_576

            print(f"  kuszob {kuszob:>6.0f} m: {megtartott:>9,} pont megtartva "
                  f"({arany:6.2%}), tomorites {1-arany:6.2%}, "
                  f"atlaghiba {atlag_hiba:5.1f} m, maxhiba {max_hiba:6.1f} m"
                  + (f", {meret_mb:,.1f} MB" if meret_mb == meret_mb else ""))

            sorok.append({
                "nap": bemenet.stem,
                "kuszob_m": kuszob,
                "osszes_pont": n,
                "megtartott_pont": megtartott,
                "megtartott_arany": round(arany, 5),
                "tomorites": round(1 - arany, 5),
                "atlag_hiba_m": round(atlag_hiba, 2),
                "max_hiba_m": round(max_hiba, 2),
                "teljes_parquet_mb": round(teljes_mb, 1) if teljes_mb == teljes_mb else "",
                "tomoritett_parquet_mb": round(meret_mb, 1) if meret_mb == meret_mb else "",
            })

    eredmeny = pd.DataFrame(sorok)
    eredmeny.to_csv(args.ki, index=False)
    print(f"\n-> {args.ki} kiirva ({len(eredmeny)} sor)")
    print("\n" + eredmeny.to_string(index=False))


if __name__ == "__main__":
    main()
