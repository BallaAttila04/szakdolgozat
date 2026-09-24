"""
H3 terbeli index hatasa a Parquet tarolasra es lekerdezesre.

Kerdes: ha a pozicios adatot H3-cella szerint rendezve taroljuk, mennyivel
gyorsul egy terbeli lekerdezes, mennyibe kerul ez az idobeli lekerdezeseknel,
es hogyan valtozik a fajlmeret?

A mechanizmus: a Parquet sorcsoportonkent min/max statisztikat tarol minden
oszloprol. Ha a terben kozeli pontok egy sorcsoportba kerulnek, egy kis
teruletre szuro lekerdezes a statisztikak alapjan a sorcsoportok nagy reszet
be sem olvassa. Az eredeti (hajo, ido) sorrendben egy hajo egesz napi palyaja
egy blokkban van, ezert minden sorcsoport szinte a teljes teruletet lefedi.

Valtozatok (azonos adat, azonos kodek, azonos sorcsoport-meret):
  alap          az eredeti sorrend (MMSI, ido), h3 oszlop nelkul
  alap_h3       ugyanaz + h3 oszlop       -> magaba az oszlopba mibe kerul
  h3_rendezett  h3 oszlop, (h3, ido) szerint rendezve
  ido_rendezett ido szerint rendezve, h3 oszlop nelkul

Lekerdezesek (mindegyik N-szer, median; az eredmenynek minden valtozatban
azonosnak kell lennie, kulonben a szkript leall):
  terbeli   egyedi hajo + sorszam egy kis teruleten (Nagy-Balti-hid)
  idobeli   sorszam egy orara (09:00-10:00)
  orankent  orankenti egyedi hajoszam (a forgalmi kiertekeles metrikaja)

A terbeli lekerdezes a h3 oszlopos valtozatokon ket formaban is fut: sima
lat/lon szuressel, es h3-cellalistaval + pontos lat/lon szuressel (a
cellalista a teruletet ERINTO osszes cella, igy az eredmeny pontosan
ugyanaz, mint a sima szuresnel).

Hasznalat:
    python h3_tarolas.py
    python h3_tarolas.py --be outputs/tomorites_parquet/aisdk-2026-07-15_teljes.parquet
    python h3_tarolas.py --felbontas 7 --ismetles 7
"""

import argparse
import csv
import statistics
import sys
import time
from pathlib import Path

import duckdb
import h3
import numpy as np

from utak import KIMENET

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except AttributeError:
    pass

# --- Parameterek ----------------------------------------------------------

ALAP_BE = KIMENET / "tomorites_parquet" / "aisdk-2026-07-15_teljes.parquet"
ALAP_KI = KIMENET / "h3_parquet"

# 8-as felbontas: ~0,74 km2/cella. Hajoutvonalakhoz a szokasos 7-8-as savban
# van; eleg finom ahhoz, hogy egy szoros keresztmetszete tobb cella legyen.
FELBONTAS = 8

# Sorcsoport-meret: minden valtozatnal azonos, hogy csak a sorrend hatasat
# merjuk. 100 000 sor ~110 sorcsoportot ad a napra - ennyi kell ahhoz, hogy
# a statisztika alapu atugras egyaltalan merheto legyen.
SORCSOPORT = 100_000

ISMETLES = 5

# Kis vizsgalati terulet: a Nagy-Balti-hid (Storebaelt) kornyeke
TER_LAT = (55.28, 55.40)
TER_LON = (10.85, 11.15)

IDO_TOL, IDO_IG = "2026-07-15 09:00:00", "2026-07-15 10:00:00"


def h3_oszlop(lat, lon, res):
    """H3-cellaazonosito (int64) minden pontra."""
    ki = np.empty(len(lat), dtype=np.int64)
    fn = h3.latlng_to_cell
    s2i = h3.str_to_int
    t0 = time.perf_counter()
    for i in range(len(lat)):
        ki[i] = s2i(fn(lat[i], lon[i], res))
        if i and i % 2_000_000 == 0:
            print(f"    {i:>12,} pont  ({time.perf_counter()-t0:.0f} mp)", end="\r")
    print()
    return ki


def terulet_cellai(res):
    """A vizsgalati teruletet ERINTO osszes H3-cella (int)."""
    (la0, la1), (lo0, lo1) = TER_LAT, TER_LON
    poly = h3.LatLngPoly([(la0, lo0), (la0, lo1), (la1, lo1), (la1, lo0)])
    cellak = h3.polygon_to_cells_experimental(poly, res, contain="overlap")
    return sorted(h3.str_to_int(c) for c in cellak)


def median_ido(con, sql, n):
    idok, eredmeny = [], None
    for _ in range(n):
        t0 = time.perf_counter()
        r = con.execute(sql).fetchall()
        idok.append(time.perf_counter() - t0)
        if eredmeny is None:
            eredmeny = r
        elif r != eredmeny:
            sys.exit(f"Ismetlesenkent elter az eredmeny: {sql[:60]}")
    return statistics.median(idok) * 1000, eredmeny


def atugorhato_sorcsoport(con, fajl, oszlop, also, felso):
    """Hany sorcsoportot lehet a min/max statisztika alapjan atugrani."""
    r = con.execute(f"""
        SELECT count(*) AS osszes,
               count(*) FILTER (WHERE TRY_CAST(stats_max AS DOUBLE) < {also}
                                   OR TRY_CAST(stats_min AS DOUBLE) > {felso})
        FROM parquet_metadata('{fajl}')
        WHERE path_in_schema = '{oszlop}'""").fetchone()
    return r


def atugorhato_ter(con, fajl):
    """Sorcsoport atugorhato, ha lat VAGY lon tartomanya kivul esik."""
    r = con.execute(f"""
        WITH m AS (
          SELECT row_group_id, path_in_schema AS o,
                 TRY_CAST(stats_min AS DOUBLE) AS mn,
                 TRY_CAST(stats_max AS DOUBLE) AS mx
          FROM parquet_metadata('{fajl}')
          WHERE path_in_schema IN ('Latitude','Longitude'))
        SELECT count(DISTINCT row_group_id),
               count(DISTINCT row_group_id) FILTER (WHERE
                 (o='Latitude'  AND (mx < {TER_LAT[0]} OR mn > {TER_LAT[1]})) OR
                 (o='Longitude' AND (mx < {TER_LON[0]} OR mn > {TER_LON[1]})))
        FROM m""").fetchone()
    return r


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--be", default=ALAP_BE)
    ap.add_argument("--kimenet", default=ALAP_KI)
    ap.add_argument("--felbontas", type=int, default=FELBONTAS)
    ap.add_argument("--ismetles", type=int, default=ISMETLES)
    ap.add_argument("--csv", default=KIMENET / "h3_tarolas.csv")
    args = ap.parse_args()

    be = Path(args.be)
    if not be.exists():
        sys.exit(f"Nem letezik: {be}")
    ki_dir = Path(args.kimenet)
    ki_dir.mkdir(parents=True, exist_ok=True)

    con = duckdb.connect()
    print(f"Beolvasas: {be}")
    df = con.execute(f"SELECT * FROM read_parquet('{be.as_posix()}')").df()
    print(f"  {len(df):,} sor, oszlopok: {list(df.columns)}")

    print(f"H3-cellak szamitasa (felbontas {args.felbontas}, "
          f"{h3.average_hexagon_area(args.felbontas, 'km^2'):.2f} km2/cella)...")
    t0 = time.perf_counter()
    df["h3"] = h3_oszlop(df["Latitude"].to_numpy(), df["Longitude"].to_numpy(),
                         args.felbontas)
    h3_ido = time.perf_counter() - t0
    print(f"  kesz: {h3_ido:.1f} mp, {df['h3'].nunique():,} kulonbozo cella")
    con.register("adat", df)

    alap_osz = "MMSI, ts, Latitude, Longitude, SOG, COG"
    valtozatok = {
        "alap":          (alap_osz,          "MMSI, ts"),
        "alap_h3":       (alap_osz + ", h3", "MMSI, ts"),
        "h3_rendezett":  (alap_osz + ", h3", "h3, ts"),
        "ido_rendezett": (alap_osz,          "ts, MMSI"),
    }

    fajlok = {}
    print("\nValtozatok irasa (zstd, sorcsoport = "
          f"{SORCSOPORT:,} sor):")
    for nev, (oszl, rend) in valtozatok.items():
        f = ki_dir / f"{be.stem}_{nev}.parquet"
        t0 = time.perf_counter()
        con.execute(f"""COPY (SELECT {oszl} FROM adat ORDER BY {rend})
                        TO '{f.as_posix()}'
                        (FORMAT parquet, COMPRESSION zstd,
                         ROW_GROUP_SIZE {SORCSOPORT})""")
        fajlok[nev] = f
        print(f"  {nev:<14} {f.stat().st_size/1048576:7.1f} MiB  "
              f"({time.perf_counter()-t0:.1f} mp)")

    cellak = terulet_cellai(args.felbontas)
    cella_lista = ",".join(str(c) for c in cellak)
    print(f"\nVizsgalati terulet: lat {TER_LAT}, lon {TER_LON} "
          f"-> {len(cellak)} erinto H3-cella")

    lat_lon = (f"Latitude BETWEEN {TER_LAT[0]} AND {TER_LAT[1]} "
               f"AND Longitude BETWEEN {TER_LON[0]} AND {TER_LON[1]}")

    def lekerdezesek(f, van_h3):
        q = {
            "terbeli": f"SELECT count(DISTINCT MMSI), count(*) FROM '{f}' WHERE {lat_lon}",
            "idobeli": f"SELECT count(*) FROM '{f}' WHERE ts >= TIMESTAMP '{IDO_TOL}' "
                       f"AND ts < TIMESTAMP '{IDO_IG}'",
            "orankent": f"SELECT date_part('hour', ts) h, count(DISTINCT MMSI) "
                        f"FROM '{f}' GROUP BY 1 ORDER BY 1",
        }
        if van_h3:
            q["terbeli_h3"] = (f"SELECT count(DISTINCT MMSI), count(*) FROM '{f}' "
                               f"WHERE h3 IN ({cella_lista}) AND {lat_lon}")
        return q

    print(f"\nLekerdezesek ({args.ismetles} ismetles, median; meleg cache):")
    sorok, referencia = [], {}
    for nev, f in fajlok.items():
        fp = f.as_posix()
        van_h3 = "h3" in valtozatok[nev][0]
        meret = f.stat().st_size / 1048576
        rg_ter = atugorhato_ter(con, fp)
        rg_ido = con.execute(f"""
            SELECT count(*), count(*) FILTER (WHERE
                stats_max < '{IDO_TOL}' OR stats_min >= '{IDO_IG}')
            FROM parquet_metadata('{fp}') WHERE path_in_schema='ts'""").fetchone()
        eredm = {"valtozat": nev, "meret_mib": round(meret, 1),
                 "sorcsoport": rg_ter[0],
                 "ter_atugorhato": rg_ter[1], "ido_atugorhato": rg_ido[1]}
        for qnev, sql in lekerdezesek(fp, van_h3).items():
            ms, r = median_ido(con, sql, args.ismetles)
            kulcs = "terbeli" if qnev.startswith("terbeli") else qnev
            if kulcs in referencia and referencia[kulcs] != r:
                sys.exit(f"HIBA: {nev}/{qnev} eredmenye elter a tobbitol!")
            referencia.setdefault(kulcs, r)
            eredm[f"{qnev}_ms"] = round(ms, 1)
        sorok.append(eredm)

    # --- Kiiras ---
    print(f"\n{'valtozat':<14}{'MiB':>7}{'sorcs.':>8}{'ter.atug.':>10}"
          f"{'ido.atug.':>10}{'terbeli':>10}{'ter+h3':>9}{'idobeli':>9}{'orankent':>10}")
    for s in sorok:
        print(f"{s['valtozat']:<14}{s['meret_mib']:>7}{s['sorcsoport']:>8}"
              f"{s['ter_atugorhato']:>10}{s['ido_atugorhato']:>10}"
              f"{s['terbeli_ms']:>9}ms{str(s.get('terbeli_h3_ms','-')):>7}"
              f"{'ms' if 'terbeli_h3_ms' in s else '  '}"
              f"{s['idobeli_ms']:>7}ms{s['orankent_ms']:>8}ms")

    t = referencia["terbeli"][0]
    print(f"\nEllenorzes: minden valtozat ugyanazt adta.")
    print(f"  terbeli:  {t[0]:,} egyedi hajo, {t[1]:,} sor a teruleten")
    print(f"  idobeli:  {referencia['idobeli'][0][0]:,} sor 09-10 kozott")
    print(f"  orankent: {len(referencia['orankent'])} ora")

    with Path(args.csv).open("w", newline="", encoding="utf-8") as fh:
        # nem minden valtozatnak van terbeli_h3 mezoje: a mezok unioja kell
        mezok = list(dict.fromkeys(k for s in sorok for k in s))
        w = csv.DictWriter(fh, fieldnames=mezok)
        w.writeheader()
        for s in sorok:
            w.writerow(s)
    print(f"\n-> {args.csv} kiirva")
    print(f"   H3-szamitas ideje: {h3_ido:.1f} mp {len(df):,} pontra")


if __name__ == "__main__":
    main()
