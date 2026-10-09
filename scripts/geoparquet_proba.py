"""
GeoParquet vs sima Parquet (lat/lon oszlopok) egy nap deduplikalt adatan.

A konzulens jegyzeteben szereplo "geopods" valoszinuleg GeoParquet /
GeoPandas. A kerdes: megeri-e a pozicios adatot geometria-oszloppal
(WKB pont, GeoParquet 1.1 bbox-oszloppal) tarolni a ket szamoszlop helyett?

Mindket valtozat ugyanazokat a sorokat, ugyanabban a sorrendben (h3, ts),
ugyanazzal a kodekkel (zstd) es sorcsoport-merettel tarolja; a kulonbseg
csak a pozicio abrazolasa.

Merve (ISMETLES ismetles, median):
  - fajlmeret, iras ideje
  - terbeli lekerdezes a h3_tarolas.py vizsgalati teruleten (egyedi hajo +
    sorszam): DuckDB lat/lon szuressel a sima Parqueten; GeoPandas
    read_parquet(bbox=...) + pontos szures a GeoParqueten; DuckDB a
    GeoParquet bbox-oszlopan.
  - teljes beolvasas memoriaba (pandas vs GeoPandas)
Az eredmenyeknek egyezniuk kell.

Hasznalat:
    python geoparquet_proba.py
    python geoparquet_proba.py --be outputs/tarolo/ev=2026/ho=07/aisdk-2026-07-15.parquet
"""

import argparse
import csv
import statistics
import sys
import time
from pathlib import Path

import duckdb
import geopandas as gpd
import pandas as pd
import pyarrow.parquet as pq

from utak import KIMENET
from h3_tarolas import SORCSOPORT, TER_LAT, TER_LON

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)
except AttributeError:
    pass

ALAP_BE = KIMENET / "tarolo" / "ev=2026" / "ho=07" / "aisdk-2026-07-15.parquet"
ALAP_KI = KIMENET / "geoparquet"
ISMETLES = 5
OSZLOPOK = ["MMSI", "ts", "SOG", "COG", "Ship type", "h3", "dup_db"]


def median_ido(fn, n):
    idok, ref = [], None
    for _ in range(n):
        t0 = time.perf_counter()
        r = fn()
        idok.append(time.perf_counter() - t0)
        if ref is None:
            ref = r
        elif r != ref:
            sys.exit("Ismetlesenkent elter az eredmeny")
    return statistics.median(idok), ref


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--be", type=Path, default=ALAP_BE)
    ap.add_argument("--ki", type=Path, default=ALAP_KI)
    ap.add_argument("--ismetles", type=int, default=ISMETLES)
    ap.add_argument("--csv", type=Path, default=KIMENET / "geoparquet_proba.csv")
    args = ap.parse_args()
    args.ki.mkdir(parents=True, exist_ok=True)

    con = duckdb.connect()
    oszl = ", ".join(f'"{o}"' for o in OSZLOPOK)
    df = con.execute(f"""SELECT {oszl}, Latitude, Longitude FROM read_parquet('{args.be.as_posix()}')
                         WHERE Latitude IS NOT NULL AND Longitude IS NOT NULL
                         ORDER BY h3, ts, MMSI""").df()
    print(f"Bemenet: {args.be.name}, {len(df):,} sor (pozicioval)")

    sima = args.ki / f"{args.be.stem}_latlon.parquet"
    geo = args.ki / f"{args.be.stem}_geo.parquet"

    t0 = time.perf_counter()
    df.to_parquet(sima, index=False, compression="zstd", row_group_size=SORCSOPORT)
    iras_sima = time.perf_counter() - t0

    t0 = time.perf_counter()
    gdf = gpd.GeoDataFrame(df[OSZLOPOK], geometry=gpd.points_from_xy(df["Longitude"], df["Latitude"]),
                           crs="EPSG:4326")
    gdf.to_parquet(geo, index=False, compression="zstd", row_group_size=SORCSOPORT,
                   write_covering_bbox=True, schema_version="1.1.0")
    iras_geo = time.perf_counter() - t0
    del gdf
    m_sima, m_geo = sima.stat().st_size / 1048576, geo.stat().st_size / 1048576
    print(f"Meret: lat/lon {m_sima:.1f} MiB ({iras_sima:.1f} mp iras), "
          f"GeoParquet {m_geo:.1f} MiB ({iras_geo:.1f} mp iras, GeoDataFrame-epitessel)")
    print(f"GeoParquet metaadat: {pq.read_metadata(geo).metadata.get(b'geo', b'')[:120]}...")

    (la0, la1), (lo0, lo1) = TER_LAT, TER_LON
    ll = f"Latitude BETWEEN {la0} AND {la1} AND Longitude BETWEEN {lo0} AND {lo1}"

    def duckdb_sima():
        return tuple(con.execute(f"SELECT count(DISTINCT MMSI), count(*) FROM "
                                 f"read_parquet('{sima.as_posix()}') WHERE {ll}").fetchone())

    def duckdb_geo_bbox():
        # a GeoParquet 1.1 bbox-oszlopa sima struct, terbeli kiegeszito nelkul is szurheto;
        # pontnal xmin = xmax = hosszusag, ymin = ymax = szelesseg
        return tuple(con.execute(
            f"SELECT count(DISTINCT MMSI), count(*) FROM read_parquet('{geo.as_posix()}') "
            f"WHERE bbox.ymin BETWEEN {la0} AND {la1} AND bbox.xmin BETWEEN {lo0} AND {lo1}"
        ).fetchone())

    def geopandas_bbox():
        g = gpd.read_parquet(geo, bbox=(lo0, la0, lo1, la1), columns=["MMSI", "geometry"])
        g = g[g.geometry.y.between(la0, la1) & g.geometry.x.between(lo0, lo1)]
        return (int(g["MMSI"].nunique()), len(g))

    def pandas_teljes():
        return len(pd.read_parquet(sima))

    def geopandas_teljes():
        return len(gpd.read_parquet(geo))

    meresek = [("terbeli", "duckdb_latlon", duckdb_sima),
               ("terbeli", "duckdb_geoparquet_bbox", duckdb_geo_bbox),
               ("terbeli", "geopandas_geoparquet_bbox", geopandas_bbox),
               ("teljes_beolvasas", "pandas_latlon", pandas_teljes),
               ("teljes_beolvasas", "geopandas_geoparquet", geopandas_teljes)]
    sorok, ref = [], {}
    for kerdes, valtozat, fn in meresek:
        mp, r = median_ido(fn, args.ismetles)
        if kerdes in ref and ref[kerdes] != r:
            sys.exit(f"HIBA: {valtozat} eredmenye ({r}) elter: {ref[kerdes]}")
        ref.setdefault(kerdes, r)
        sorok.append({"kerdes": kerdes, "valtozat": valtozat, "median_mp": round(mp, 4),
                      "eredmeny": r,
                      "fajl_mib": round(m_geo if "geo" in valtozat else m_sima, 1)})
        print(f"  {kerdes:<17} {valtozat:<28} {mp * 1000:>9.1f} ms   {r}")

    sorok.append({"kerdes": "iras", "valtozat": "latlon", "median_mp": round(iras_sima, 2),
                  "fajl_mib": round(m_sima, 1)})
    sorok.append({"kerdes": "iras", "valtozat": "geoparquet", "median_mp": round(iras_geo, 2),
                  "fajl_mib": round(m_geo, 1)})
    with args.csv.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["kerdes", "valtozat", "median_mp", "fajl_mib", "eredmeny"])
        w.writeheader()
        w.writerows(sorok)
    print(f"\nEllenorzes: minden valtozat ugyanazt adta ({ref['terbeli']}).")
    print(f"Meretarany GeoParquet / lat-lon: {m_geo / m_sima:.2f}x")
    print(f"-> {args.csv}")


if __name__ == "__main__":
    main()
