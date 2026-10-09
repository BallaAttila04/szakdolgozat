"""
AIS adattarolas benchmark: CSV vs Parquet vs natic DuckDB tabla.

Kontextus (ld. naplo.md, 2026-09-18 22:35-os bejegyzes): a konzulenssel
(2026-09-17-i konzultacio) megbeszelt uj hangsuly a nagy AIS-adathalmaz
modern tarolasi/feldolgozasi modszereinek vizsgalata. Ez a szkript a
harom felmerult megoldas kozul az elsot meri szamszeruen: CSV -> Parquet
es/vagy DuckDB, meret / beolvasasi ido / lekerdezesi ido szerint. (A H3
terbeli index es a Spark meg nincs ebbe a szkriptbe integralva - ld.
naplo.md nyitott kerdesek.)

Modszertan (fontos, mert nem szimmetrikus a negy "motor" kozott):
  - pandas_csv: EGY chunkolt vegigolvasas a nyers CSV-n, ami kozben mind
    a negy mutatot egyszerre szamolja - ez a realisztikus hasznalat
    (egy kompetens szkript nem olvasna at negyszer ugyanazt a tobb GB-os
    fajlt negy kulon lekerdezeshez).
  - duckdb_csv / duckdb_parquet / duckdb_tabla: NEGY KULON, fuggetlen
    SQL lekerdezes lefuttatva, mert ez a realisztikus DuckDB-hasznalat -
    es pont ez az, amiben a Parquet/natic tabla elonye (oszlop- es
    sor-csoport-szures) megmutatkozhat a nyers CSV-hez kepest.
  Emiatt a "pandas_csv" egyetlen sora a negy lekerdezes OSSZESITETT
  idejet mutatja, a DuckDB motorok soronkent a lekerdezesenkenti idot -
  ez szandekos, ne hasonlitsd ossze lekerdezesenkent pandas vs DuckDB-t,
  csak a negy lekerdezes OSSZIDEJET a "pandas_csv_osszes" sorban.

Hasznalat:
    pip install duckdb
    python tarolas_benchmark.py data/aisdk-2026-07-15.zip data/aisdk-2026-07-16.zip

    # ha a CSV mar ki van csomagolva, ZIP helyett CSV utvonal is mehet
    python tarolas_benchmark.py data/aisdk-2026-07-15.csv

    # munkakonyvtar a kicsomagolt CSV-knek, Parquet-eknek, .duckdb fajlnak
    python tarolas_benchmark.py data/*.zip --munka bench_workdir

Fuggosegek: pandas, duckdb
    pip install duckdb
"""

import argparse
import shutil
import sys
import time
import zipfile
from pathlib import Path

import pandas as pd

from utak import KIMENET

try:
    import duckdb
except ImportError:
    duckdb = None

# --- Parameterek ----------------------------------------------------------

LAT_MIN, LAT_MAX = 54.5, 56.5
LON_MIN, LON_MAX = 10.0, 13.0

CHUNK = 500_000
TS_OSZLOP = "# Timestamp"
MMSI_OSZLOP = "MMSI"
LAT_OSZLOP = "Latitude"
LON_OSZLOP = "Longitude"


# --- Kicsomagolas -----------------------------------------------------------

def csv_utvonal(bemenet: Path, munka_dir: Path) -> Path:
    """ZIP eseten kicsomagolja az elso CSV/TXT/DAT tagot a munka_dir-be
    (ha meg nincs ott), es visszaadja az utvonalat. Mar CSV bemenetnel
    valtozatlanul visszaadja."""
    if bemenet.suffix.lower() != ".zip":
        return bemenet

    with zipfile.ZipFile(bemenet) as zf:
        members = [
            n for n in zf.namelist()
            if n.lower().endswith((".csv", ".txt", ".dat"))
        ]
        if not members:
            sys.exit(f"Nincs CSV/TXT/DAT a ZIP-ben: {bemenet}")
        member = members[0]
        cel = munka_dir / Path(member).name
        if cel.exists():
            print(f"  {cel.name}: mar ki van csomagolva, ujrahasznalom")
            return cel

        print(f"  kicsomagolas: {member} -> {cel}")
        with zf.open(member) as src, open(cel, "wb") as dst:
            shutil.copyfileobj(src, dst, length=1024 * 1024)
        return cel


# --- Idozites segedfuggveny --------------------------------------------------

def idozit(fn, *args, **kwargs):
    t0 = time.perf_counter()
    eredmeny = fn(*args, **kwargs)
    return eredmeny, time.perf_counter() - t0


# --- pandas: egy chunkolt vegigolvasas, mind a negy mutato egyszerre --------

def pandas_osszes_lekerdezes(csv_path: Path) -> dict:
    """Egyetlen chunkolt vegigolvasassal szamolja: sorszam, egyedi hajo,
    bbox-szures talalat, es oranankenti (bbox-on beluli) bontas."""
    sorszam = 0
    mmsi_halmaz = set()
    bbox_talalat = 0
    ora_uzenet = {h: 0 for h in range(24)}
    ora_mmsi = {h: set() for h in range(24)}

    reader = pd.read_csv(
        csv_path, chunksize=CHUNK, low_memory=False, encoding="utf-8-sig",
    )
    for i, chunk in enumerate(reader):
        chunk.columns = [c.strip() for c in chunk.columns]
        sorszam += len(chunk)
        mmsi_halmaz.update(chunk[MMSI_OSZLOP].unique().tolist())

        m = (
            chunk[LAT_OSZLOP].between(LAT_MIN, LAT_MAX)
            & chunk[LON_OSZLOP].between(LON_MIN, LON_MAX)
        )
        bbox_chunk = chunk[m]
        bbox_talalat += len(bbox_chunk)

        if len(bbox_chunk):
            ts = pd.to_datetime(
                bbox_chunk[TS_OSZLOP], format="%d/%m/%Y %H:%M:%S", errors="coerce",
            )
            bbox_chunk = bbox_chunk.assign(ts=ts).dropna(subset=["ts"])
            for h, grp in bbox_chunk.groupby(bbox_chunk["ts"].dt.hour):
                ora_uzenet[int(h)] += len(grp)
                ora_mmsi[int(h)].update(grp[MMSI_OSZLOP].tolist())

        print(f"  pandas chunk {i:>3}: {sorszam:>12,} sor", end="\r")
    print()

    return {
        "sorszam": sorszam,
        "egyedi_hajo": len(mmsi_halmaz),
        "bbox_szures": bbox_talalat,
        "oranankenti_bbox_sorok": sum(1 for h in ora_uzenet if ora_uzenet[h] > 0),
    }


# --- DuckDB: negy fuggetlen lekerdezes --------------------------------------

DUCKDB_LEKERDEZESEK = {
    "sorszam": 'SELECT COUNT(*) FROM {src}',
    "egyedi_hajo": f'SELECT COUNT(DISTINCT "{MMSI_OSZLOP}") FROM {{src}}',
    "bbox_szures": (
        f'SELECT COUNT(*) FROM {{src}} '
        f'WHERE "{LAT_OSZLOP}" BETWEEN {LAT_MIN} AND {LAT_MAX} '
        f'AND "{LON_OSZLOP}" BETWEEN {LON_MIN} AND {LON_MAX}'
    ),
    "oranankenti_bbox": (
        f'SELECT {{ora}} AS ora, '
        f'COUNT(*) AS uzenet, COUNT(DISTINCT "{MMSI_OSZLOP}") AS hajo '
        f'FROM {{src}} '
        f'WHERE "{LAT_OSZLOP}" BETWEEN {LAT_MIN} AND {LAT_MAX} '
        f'AND "{LON_OSZLOP}" BETWEEN {LON_MIN} AND {LON_MAX} '
        f'GROUP BY 1 ORDER BY 1'
    ),
}


def ora_kifejezes(con, src_kifejezes: str) -> str:
    """Az orat kinyero SQL kifejezes a '# Timestamp' oszlop tenyleges
    tipusa szerint. A DuckDB CSV-sniffer (es igy a belole keszult Parquet
    / natic tabla is) TIMESTAMP-kent tipizalja az oszlopot, ilyenkor a
    strptime() hibara fut ('No function matches ... strptime(TIMESTAMP,
    STRING_LITERAL)'). Szoveges oszlopnal viszont kell a strptime."""
    tipus = con.execute(
        f'SELECT typeof("{TS_OSZLOP}") FROM {src_kifejezes} LIMIT 1'
    ).fetchone()[0]
    if tipus.upper().startswith("TIMESTAMP"):
        return f'date_part(\'hour\', "{TS_OSZLOP}")'
    return (
        f'date_part(\'hour\', strptime("{TS_OSZLOP}", \'%d/%m/%Y %H:%M:%S\'))'
    )


def duckdb_lekerdezesek_futtatasa(con, src_kifejezes: str) -> dict:
    """Lefuttatja mind a negy lekerdezest kulon-kulon, visszaadja a
    {lekerdezes_nev: (eredmeny, masodperc)} szotarat."""
    ora_sql = ora_kifejezes(con, src_kifejezes)
    eredmenyek = {}
    for nev, sql_sablon in DUCKDB_LEKERDEZESEK.items():
        sql = sql_sablon.format(src=src_kifejezes, ora=ora_sql)
        eredmeny, mp = idozit(lambda: con.execute(sql).fetchall())
        eredmenyek[nev] = (eredmeny, mp)
    return eredmenyek


# --- Egy nap benchmarkja ----------------------------------------------------

def benchmark_nap(bemenet: Path, munka_dir: Path) -> list:
    print(f"\n=== {bemenet.name} ===")
    csv_path, kicsomagolas_mp = idozit(csv_utvonal, bemenet, munka_dir)
    csv_meret_mb = csv_path.stat().st_size / 1_048_576
    print(f"  CSV meret: {csv_meret_mb:,.1f} MB "
          f"(kicsomagolas: {kicsomagolas_mp:.1f} mp)")

    sorok = []

    # --- pandas baseline: egy osszevont chunkolt vegigolvasas ---
    print("  pandas: chunkolt vegigolvasas, mind a negy mutato egyszerre...")
    pandas_eredmeny, pandas_mp = idozit(pandas_osszes_lekerdezes, csv_path)
    sorok.append({
        "nap": bemenet.stem.split(".")[0], "motor": "pandas_csv_osszes",
        "lekerdezes": "mind_a_negy_egyutt", "masodperc": round(pandas_mp, 2),
        "meret_mb": round(csv_meret_mb, 1), "eredmeny": str(pandas_eredmeny),
    })

    if duckdb is None:
        print("  FIGYELEM: a duckdb csomag nincs telepitve "
              "(pip install duckdb) - a DuckDB/Parquet resz kimarad.")
        return sorok

    con = duckdb.connect()

    # --- DuckDB kozvetlenul a CSV-n ---
    print("  duckdb: lekerdezesek kozvetlenul a CSV-n...")
    csv_src = f"read_csv_auto('{csv_path.as_posix()}')"
    for nev, (eredmeny, mp) in duckdb_lekerdezesek_futtatasa(con, csv_src).items():
        sorok.append({
            "nap": bemenet.stem.split(".")[0], "motor": "duckdb_csv",
            "lekerdezes": nev, "masodperc": round(mp, 3),
            "meret_mb": round(csv_meret_mb, 1), "eredmeny": str(eredmeny),
        })

    # --- CSV -> Parquet konverzio ---
    parquet_path = munka_dir / (csv_path.stem + ".parquet")
    print(f"  konverzio Parquet-te: {parquet_path.name}...")
    _, konverzio_mp = idozit(
        con.execute,
        f"COPY (SELECT * FROM {csv_src}) TO '{parquet_path.as_posix()}' "
        f"(FORMAT PARQUET)",
    )
    parquet_meret_mb = parquet_path.stat().st_size / 1_048_576
    print(f"  Parquet meret: {parquet_meret_mb:,.1f} MB "
          f"(konverzio: {konverzio_mp:.1f} mp, "
          f"aranya a CSV-hez: {parquet_meret_mb / csv_meret_mb:.1%})")
    sorok.append({
        "nap": bemenet.stem.split(".")[0], "motor": "duckdb_parquet_konverzio",
        "lekerdezes": "csv_to_parquet", "masodperc": round(konverzio_mp, 2),
        "meret_mb": round(parquet_meret_mb, 1), "eredmeny": "",
    })

    print("  duckdb: lekerdezesek a Parquet-en...")
    parquet_src = f"read_parquet('{parquet_path.as_posix()}')"
    for nev, (eredmeny, mp) in duckdb_lekerdezesek_futtatasa(con, parquet_src).items():
        sorok.append({
            "nap": bemenet.stem.split(".")[0], "motor": "duckdb_parquet",
            "lekerdezes": nev, "masodperc": round(mp, 3),
            "meret_mb": round(parquet_meret_mb, 1), "eredmeny": str(eredmeny),
        })

    # --- CSV -> natic DuckDB tabla ---
    duckdb_fajl = munka_dir / (csv_path.stem + ".duckdb")
    if duckdb_fajl.exists():
        duckdb_fajl.unlink()
    tabla_con = duckdb.connect(str(duckdb_fajl))
    print(f"  betoltes natic DuckDB tablaba: {duckdb_fajl.name}...")
    _, betoltes_mp = idozit(
        tabla_con.execute, f"CREATE TABLE ais AS SELECT * FROM {csv_src}",
    )
    duckdb_meret_mb = duckdb_fajl.stat().st_size / 1_048_576
    print(f"  .duckdb fajl meret: {duckdb_meret_mb:,.1f} MB "
          f"(betoltes: {betoltes_mp:.1f} mp)")
    sorok.append({
        "nap": bemenet.stem.split(".")[0], "motor": "duckdb_tabla_betoltes",
        "lekerdezes": "csv_to_table", "masodperc": round(betoltes_mp, 2),
        "meret_mb": round(duckdb_meret_mb, 1), "eredmeny": "",
    })

    print("  duckdb: lekerdezesek a natic tablan...")
    for nev, (eredmeny, mp) in duckdb_lekerdezesek_futtatasa(tabla_con, "ais").items():
        sorok.append({
            "nap": bemenet.stem.split(".")[0], "motor": "duckdb_tabla",
            "lekerdezes": nev, "masodperc": round(mp, 3),
            "meret_mb": round(duckdb_meret_mb, 1), "eredmeny": str(eredmeny),
        })
    tabla_con.close()
    con.close()

    return sorok


# --- Motorok a pipeline.py Parquet-tarolojan ----------------------------------
#
# Ugyanaz a negy lekerdezes, a deduplikalt tarolohoz igazitva: a tarolo egy
# sora `dup_db` darab nyers sort kepvisel, ezert a sorszamok SUM(dup_db)-kent
# szamolodnak. Igy az eredmeny a nyers CSV-n futo motorokeval is pontosan
# osszevetheto (ugyanannyi uzenet, ugyanannyi hajo).
#
# Minden motor ugyanazt a normalizalt alakot adja vissza:
#   {"sorszam": int, "egyedi_hajo": int, "bbox_szures": int,
#    "oranankenti_bbox": [(ora, uzenet, hajo), ...]}

TAROLO_MOTOROK = ("duckdb_parquet", "polars_parquet", "spark_parquet")
CSV_MOTOROK = ("duckdb_csv", "pandas_csv")


def _duckdb_tarolo(fajlok):
    con = duckdb.connect()
    src = "read_parquet([" + ",".join(f"'{Path(f).as_posix()}'" for f in fajlok) + "])"
    bbox = (f"Latitude BETWEEN {LAT_MIN} AND {LAT_MAX} "
            f"AND Longitude BETWEEN {LON_MIN} AND {LON_MAX}")
    sql = {
        "sorszam": f"SELECT sum(dup_db) FROM {src}",
        "egyedi_hajo": f"SELECT count(DISTINCT MMSI) FROM {src}",
        "bbox_szures": f"SELECT sum(dup_db) FROM {src} WHERE {bbox}",
        "oranankenti_bbox": f"SELECT hour(ts), sum(dup_db), count(DISTINCT MMSI) "
                            f"FROM {src} WHERE {bbox} GROUP BY 1 ORDER BY 1",
    }

    def futtat(nev):
        r = con.execute(sql[nev]).fetchall()
        return [tuple(int(x) for x in s) for s in r] if nev == "oranankenti_bbox" else int(r[0][0])
    return futtat, con.close


def _polars_tarolo(fajlok):
    import polars as pl
    lf = pl.scan_parquet([str(f) for f in fajlok])
    # streaming vegrehajtas: a 3 honapos adaton (1,18 mrd sor) a teljes MMSI-
    # oszlop memoriaba huzasa ~9 GB lenne
    eng = "streaming"
    bbox = (pl.col("Latitude").is_between(LAT_MIN, LAT_MAX)
            & pl.col("Longitude").is_between(LON_MIN, LON_MAX))
    q = {
        "sorszam": lambda: lf.select(pl.col("dup_db").sum()).collect(engine=eng).item(),
        "egyedi_hajo": lambda: lf.select(pl.col("MMSI").drop_nulls().n_unique()).collect(engine=eng).item(),
        "bbox_szures": lambda: lf.filter(bbox).select(pl.col("dup_db").sum()).collect(engine=eng).item(),
        "oranankenti_bbox": lambda: [
            tuple(int(x) for x in s) for s in
            lf.filter(bbox).group_by(pl.col("ts").dt.hour().alias("ora"))
              .agg(pl.col("dup_db").sum(), pl.col("MMSI").drop_nulls().n_unique())
              .sort("ora").collect(engine=eng).rows()],
    }
    return (lambda nev: (lambda r: r if isinstance(r, list) else int(r))(q[nev]())), (lambda: None)


def spark_session(memoria="8g"):
    """Helyi modu Spark-session a felhasznaloi konyvtarba telepitett JDK-val
    (ld. naplo, 4. fazis). A JAVA_HOME-ot, ha nincs beallitva, a ~/jdk alatt
    keresi."""
    import glob
    import os
    if not os.environ.get("JAVA_HOME"):
        jdk = sorted(glob.glob(os.path.expanduser("~/jdk/jdk-21*")))
        if jdk:
            os.environ["JAVA_HOME"] = jdk[-1]
    os.environ.setdefault("PYSPARK_PYTHON", sys.executable)
    from pyspark.sql import SparkSession
    return (SparkSession.builder.master("local[*]").appName("ais_benchmark")
            .config("spark.driver.memory", memoria)
            .config("spark.sql.session.timeZone", "UTC")
            .config("spark.ui.enabled", "false")
            .getOrCreate())


def _spark_tarolo(fajlok, spark):
    from pyspark.sql import functions as F
    df = spark.read.parquet(*[Path(f).as_posix() for f in fajlok])
    bbox = (F.col("Latitude").between(LAT_MIN, LAT_MAX)
            & F.col("Longitude").between(LON_MIN, LON_MAX))
    q = {
        "sorszam": lambda: df.agg(F.sum("dup_db")).collect()[0][0],
        "egyedi_hajo": lambda: df.agg(F.countDistinct("MMSI")).collect()[0][0],
        "bbox_szures": lambda: df.filter(bbox).agg(F.sum("dup_db")).collect()[0][0],
        "oranankenti_bbox": lambda: [
            tuple(int(x) for x in s) for s in
            df.filter(bbox).groupBy(F.hour("ts").alias("ora"))
              .agg(F.sum("dup_db"), F.countDistinct("MMSI")).orderBy("ora").collect()],
    }
    return (lambda nev: (lambda r: r if isinstance(r, list) else int(r))(q[nev]())), (lambda: None)


def _duckdb_csv(csvk):
    con = duckdb.connect()
    src = "read_csv_auto([" + ",".join(f"'{Path(c).as_posix()}'" for c in csvk) + "])"
    ora = ora_kifejezes(con, src)

    def futtat(nev):
        r = con.execute(DUCKDB_LEKERDEZESEK[nev].format(src=src, ora=ora)).fetchall()
        return [tuple(int(x) for x in s) for s in r] if nev == "oranankenti_bbox" else int(r[0][0])
    return futtat, con.close


def tarolo_meres(motor, fajlok, ismetles, spark_memoria="8g"):
    """Egy motor, egy adatmeret: `ismetles`-szer mind a negy lekerdezes.
    Visszaad: eredmenyek, lekerdezesenkenti idok, session-inditasi ido."""
    t0 = time.perf_counter()
    spark = None
    if motor == "duckdb_parquet":
        futtat, zar = _duckdb_tarolo(fajlok)
    elif motor == "polars_parquet":
        futtat, zar = _polars_tarolo(fajlok)
    elif motor == "spark_parquet":
        spark = spark_session(spark_memoria)
        futtat, zar = _spark_tarolo(fajlok, spark)
    elif motor == "duckdb_csv":
        futtat, zar = _duckdb_csv(fajlok)
    elif motor == "pandas_csv":
        futtat, zar = None, (lambda: None)   # lent kulon ag: egy vegigolvasas
    else:
        raise ValueError(motor)
    inditas = time.perf_counter() - t0

    eredmeny, idok = {}, {nev: [] for nev in DUCKDB_LEKERDEZESEK}
    if motor == "pandas_csv":
        for _ in range(ismetles):
            t = time.perf_counter()
            r = {}
            for c in fajlok:      # napi CSV-nkent egy chunkolt vegigolvasas
                d = pandas_osszes_lekerdezes(Path(c))
                for k, v in d.items():
                    r[k] = r.get(k, 0) + v
            idok.setdefault("mind_a_negy_egyutt", []).append(time.perf_counter() - t)
            eredmeny = r
        return eredmeny, idok, inditas

    for i in range(ismetles):
        for nev in DUCKDB_LEKERDEZESEK:
            t = time.perf_counter()
            r = futtat(nev)
            idok[nev].append(time.perf_counter() - t)
            if i == 0:
                eredmeny[nev] = r
            elif r != eredmeny[nev]:
                raise RuntimeError(f"{motor}/{nev}: ismetlesenkent mas eredmeny")
    zar()
    if spark is not None:
        spark.stop()
    return eredmeny, idok, inditas


def tarolo_meres_main():
    """Egyetlen meres kulon folyamatban (a skalazas.py hivja), hogy a csucs
    memoria ehhez a motorhoz es adatmerethez legyen rendelheto.

        python tarolas_benchmark.py --tarolo-meres --motor polars_parquet \\
            --ismetles 3 --json ki.json f1.parquet f2.parquet ...
    """
    import json
    ap = argparse.ArgumentParser()
    ap.add_argument("--tarolo-meres", action="store_true")
    ap.add_argument("--motor", required=True, choices=TAROLO_MOTOROK + CSV_MOTOROK)
    ap.add_argument("--ismetles", type=int, default=3)
    ap.add_argument("--spark-memoria", default="8g")
    ap.add_argument("--json", required=True)
    ap.add_argument("fajlok", nargs="+")
    a = ap.parse_args()
    eredmeny, idok, inditas = tarolo_meres(a.motor, a.fajlok, a.ismetles, a.spark_memoria)
    Path(a.json).write_text(json.dumps(
        {"motor": a.motor, "eredmeny": eredmeny, "idok": idok, "inditas_mp": inditas}),
        encoding="utf-8")
    print(f"{a.motor}: inditas {inditas:.1f} mp, " + ", ".join(
        f"{k} {sorted(v)[len(v) // 2]:.3f} mp" for k, v in idok.items() if v))
    return 0


def main():
    if "--tarolo-meres" in sys.argv:
        return tarolo_meres_main()
    ap = argparse.ArgumentParser(description=__doc__,
                                  formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("bemenetek", nargs="+", help="Napi AIS ZIP vagy CSV fajlok")
    ap.add_argument("--munka", default=KIMENET / "bench_workdir",
                     help="Munkakonyvtar kicsomagolt CSV/Parquet/.duckdb fajloknak "
                          "(alapertelmezett: ./bench_workdir)")
    ap.add_argument("--ki", default=KIMENET / "tarolas_benchmark.csv",
                     help="Kimeneti CSV a merest eredmenyekkel")
    args = ap.parse_args()

    if duckdb is None:
        print("FIGYELEM: a 'duckdb' csomag nincs telepitve ebben a "
              "kornyezetben - csak a pandas-agat lehet futtatni.\n"
              "Telepitshez: pip install duckdb\n")

    munka_dir = Path(args.munka)
    munka_dir.mkdir(parents=True, exist_ok=True)

    minden_sor = []
    for bemenet_str in args.bemenetek:
        bemenet = Path(bemenet_str)
        if not bemenet.exists():
            sys.exit(f"Nem letezik: {bemenet}")
        minden_sor.extend(benchmark_nap(bemenet, munka_dir))

    df = pd.DataFrame(minden_sor)
    df.to_csv(args.ki, index=False)
    print(f"\n-> {args.ki} kiirva ({len(df)} sor)")
    print("\n" + df.to_string(index=False))


if __name__ == "__main__":
    main()
