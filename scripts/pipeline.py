"""
Napi AIS-adat feldolgozo lanca (az artefaktum magja).

A lepesek sorrendje a modszertani resz szerint:
    letoltes -> ellenorzes -> Parquet -> deduplikalas -> tomorites
    -> H3-rendezes -> (mutatokepzes: kapuvonal.py / monitor.py)

Naponkent:
  1. Letoltes a letoltes.py logikajaval (ha a ZIP meg nincs meg).
  2. A ZIP-bol kicsomagolt CSV sorainak megszamolasa (ez a "ZIP-sorszam").
  3. CSV -> Parquet (zstd) DuckDB-vel. A bitre azonos sorokat (mind a 26
     oszlop szovegesen egyezik) egy sorra vonjuk ossze, es a `dup_db` oszlop
     tarolja, hany peldanyban szerepelt a forrasban. Igy a deduplikalt adat
     veszteseg nelkul visszaadja a nyers sorszamot: SUM(dup_db).
     H3-cella (8-as felbontas) oszlop, (h3, ts) szerinti rendezes.
  4. Validalas a kiirt fajlbol visszaolvasva: SUM(dup_db) == ZIP-sorszam,
     es a DuckDB H3-kiegeszitoje egy mintan ugyanazt a cellat adja, mint a
     `h3` Python-csomag (amivel a korabbi meresek keszultek).
  5. Szarmaztatott reteg: dead reckoning 50 m-es kuszobbel a deduplikalt
     adaton (trajektoria_tomorites.dead_reckoning_maszk), kulon mappaban,
     a teljes reteg MELLETT.
  6. --torol-zip: a ZIP-et csak sikeres validalas utan torli.

Kimenet:
  outputs/tarolo/ev=2026/ho=07/aisdk-2026-07-15.parquet       teljes, dedup.
  outputs/tarolo_dr50/ev=2026/ho=07/aisdk-2026-07-15.parquet  dead reckoning
  outputs/pipeline_napok.csv    naponkent egy sor: sorszamok, meretek, ido,
                                memoria, statusz (ebbol latszik, hol tart)

Idempotens: a mar validalt napot kihagyja (--felulir: ujracsinalja).
Megszakadas utan ujrainditva onnan folytatja, ahol abbahagyta.

Hasznalat:
    python pipeline.py --zipbol                     # a data/ osszes ZIP-je
    python pipeline.py 2026-07-15                   # egy nap
    python pipeline.py 2026-06-01 2026-08-31 --torol-zip
    python pipeline.py 2026-07-15 --felulir --dr-kihagy
"""

import argparse
import csv
import os
import shutil
import sys
import threading
import time
import zipfile
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from datetime import date, datetime
from pathlib import Path

import duckdb
import h3
import numpy as np
import psutil

from utak import ADAT, KIMENET
from letoltes import datum_tartomany, ellenoriz_zip, letolt_egy_napot
from h3_tarolas import FELBONTAS, SORCSOPORT
from trajektoria_tomorites import (LAT_MAX, LAT_MIN, LON_MAX, LON_MIN,
                                   dead_reckoning_maszk)

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)
except AttributeError:
    pass

# --- Parameterek ----------------------------------------------------------

TAROLO = KIMENET / "tarolo"
TAROLO_DR = KIMENET / "tarolo_dr50"
NAPLO_CSV = KIMENET / "pipeline_napok.csv"
MUNKA = KIMENET / "tarolo_munka"     # kicsomagolt CSV + DuckDB kiirt lapok

# A megtartott oszlopok: minden, amit a scripts/ valamelyik szkriptje olvas
# (ld. naplo.md, 2026-10-05, "Fazis 1"). A tobbi 10 oszlop (ROT, Heading,
# Cargo type, ETA, A-D, ...) egyik elemzesben sem szerepel.
#   (forras oszlop, cel tipus)
OSZLOPOK = [
    ("Type of mobile", "VARCHAR"),
    ("MMSI", "BIGINT"),
    ("Latitude", "DOUBLE"),
    ("Longitude", "DOUBLE"),
    ("Navigational status", "VARCHAR"),
    ("SOG", "DOUBLE"),
    ("COG", "DOUBLE"),
    ("IMO", "VARCHAR"),
    ("Callsign", "VARCHAR"),
    ("Name", "VARCHAR"),
    ("Ship type", "VARCHAR"),
    ("Width", "DOUBLE"),
    ("Length", "DOUBLE"),
    ("Draught", "DOUBLE"),
    ("Destination", "VARCHAR"),
]
TS_FORRAS = "# Timestamp"
TS_FORMATUM = "%d/%m/%Y %H:%M:%S"

# Dead reckoning kuszob: 50 m (szamok.md, "Trajektoria-tomorites") - itt a
# legjobb a meret/hiba arany, es a garantalt hibakorlat meg kisebb egy hajo
# hosszanal.
DR_KUSZOB_M = 50
DR_OSZLOPOK = ["MMSI", "ts", "Latitude", "Longitude", "SOG", "COG"]

# DuckDB memoriakorlat: 16 GB-os gepen 6 GB-nal a DR-lepes pandas-tablaja
# (~1 GB) es az operacios rendszer is elfer; folotte a DuckDB lemezre lapoz.
# A GitHub-futtato is 16 GB-os (ld. naplo, 6a).
DUCKDB_MEMORIA = "6GB"

# H3-ellenorzes mintamerete: ennyi veletlen sor H3-cellajat szamoljuk ujra
# a Python-csomaggal. Olcso (< 1 mp), es elkapja, ha a kiegeszito eltér.
H3_MINTA = 2000

MERES_IDOKOZ_MP = 0.2

# A tarolo semajanak verzioja. Ha valtozik, a regebbi semaju napokat az
# ujrafuttatas magatol ujracsinalja (nem kell --felulir).
#   1: elso valtozat
#   2: + `sorrend` oszlop (azonos masodpercu sorok forrasbeli sorrendje)
SEMA = 2


# --- Segedfuggvenyek -------------------------------------------------------

def zip_ut(nap: date, adat: Path) -> Path:
    return adat / f"aisdk-{nap.isoformat()}.zip"


def parquet_ut(gyoker: Path, nap: date) -> Path:
    return (gyoker / f"ev={nap.year}" / f"ho={nap.month:02d}"
            / f"aisdk-{nap.isoformat()}.parquet")


def mib(utvonal: Path) -> float:
    return utvonal.stat().st_size / 1_048_576 if utvonal.exists() else 0.0


class Mero:
    """Hatterszal: csucs memoria (a folyamat + gyerekei RSS-e) es csucs
    lemezhasznalat (a szabad hely csokkenese a meres kezdetehez kepest)."""

    def __init__(self, lemez_ut: Path):
        self.lemez_ut = lemez_ut
        self.proc = psutil.Process()
        self.csucs_rss = 0
        self.kezdo_szabad = psutil.disk_usage(str(lemez_ut)).free
        self.min_szabad = self.kezdo_szabad
        self._stop = threading.Event()
        self._szal = threading.Thread(target=self._fut, daemon=True)

    def _fut(self):
        while not self._stop.is_set():
            try:
                rss = self.proc.memory_info().rss
                for gy in self.proc.children(recursive=True):
                    try:
                        rss += gy.memory_info().rss
                    except psutil.Error:
                        pass
                self.csucs_rss = max(self.csucs_rss, rss)
                self.min_szabad = min(self.min_szabad,
                                      psutil.disk_usage(str(self.lemez_ut)).free)
            except psutil.Error:
                pass
            self._stop.wait(MERES_IDOKOZ_MP)

    def __enter__(self):
        self._szal.start()
        return self

    def __exit__(self, *exc):
        self._stop.set()
        self._szal.join()

    @property
    def csucs_mib(self):
        return self.csucs_rss / 1_048_576

    @property
    def lemez_csucs_mib(self):
        return (self.kezdo_szabad - self.min_szabad) / 1_048_576


def kicsomagol(zip_fajl: Path, cel_dir: Path):
    """A ZIP egyetlen CSV-jet kicsomagolja, kozben megszamolja a sorokat
    (sortores-bajtok). Visszaad: (csv ut, adatsorok szama fejlec nelkul)."""
    with zipfile.ZipFile(zip_fajl) as zf:
        tagok = [n for n in zf.namelist() if n.lower().endswith((".csv", ".txt"))]
        if len(tagok) != 1:
            raise RuntimeError(f"{zip_fajl.name}: {len(tagok)} CSV a ZIP-ben (1 kell)")
        cel = cel_dir / Path(tagok[0]).name
        sortores, utolso = 0, b"\n"
        with zf.open(tagok[0]) as be, open(cel, "wb") as ki:
            while True:
                darab = be.read(16 * 1024 * 1024)
                if not darab:
                    break
                sortores += darab.count(b"\n")
                utolso = darab[-1:]
                ki.write(darab)
    sorok = sortores + (0 if utolso == b"\n" else 1)   # zaro sortores nelkul is
    return cel, sorok - 1                               # fejlec nelkul


def duckdb_kapcsolat(munka: Path, memoria: str = DUCKDB_MEMORIA):
    con = duckdb.connect()
    con.execute(f"SET memory_limit = '{memoria}'")
    con.execute(f"SET temp_directory = '{(munka / 'duckdb_tmp').as_posix()}'")
    con.execute("SET preserve_insertion_order = false")
    con.execute("INSTALL h3 FROM community")
    con.execute("LOAD h3")
    return con


def csv_parquetbe(con, csv_fajl: Path, cel: Path):
    """Dedup + tipusok + H3 + rendezes egyetlen DuckDB-lekerdezesben."""
    ervenyes = ("Latitude BETWEEN -90 AND 90 AND Longitude BETWEEN -180 AND 180")
    tipusos = ",\n".join(
        f'TRY_CAST("{o}" AS {t}) AS "{o}"' if t != "VARCHAR" else f'"{o}"'
        for o, t in OSZLOPOK)
    # A `sorrend` oszlop: az azonos (MMSI, ts) parú, de eltero tartalmu sorok
    # forrasbeli sorrendje (1, 2, ...). Egy hajonak ugyanarra a masodpercre
    # lehet ket kulonbozo pozicioja; ha ezek sorrendje elveszik, egy kapuvonal
    # mellett hamis oda-vissza atkeles keletkezik (ld. naplo, 2. fazis). A
    # sorok ~99,9%-anal az ertek 1, ezert a tarolasa gyakorlatilag ingyenes.
    con.execute("SET preserve_insertion_order = true")   # a row_number() miatt
    con.execute(f"""
        COPY (
          WITH szamozott AS (
            SELECT *, row_number() OVER () AS rn
            FROM read_csv('{csv_fajl.as_posix()}', header = true,
                          all_varchar = true, delim = ',', quote = '"')
          ), nyers AS (
            SELECT * EXCLUDE (rn), count(*)::INTEGER AS dup_db, min(rn) AS elso
            FROM szamozott
            GROUP BY ALL
          ), t AS (
            SELECT TRY_STRPTIME("{TS_FORRAS}", '{TS_FORMATUM}') AS ts,
                   {tipusos},
                   dup_db, elso
            FROM nyers
          )
          SELECT ts, * EXCLUDE (ts, dup_db, elso),
                 CASE WHEN {ervenyes}
                      THEN h3_latlng_to_cell(Latitude, Longitude, {FELBONTAS})::BIGINT
                 END AS h3,
                 dup_db,
                 row_number() OVER (PARTITION BY MMSI, ts ORDER BY elso)::SMALLINT AS sorrend
          FROM t
          ORDER BY h3, ts, MMSI, sorrend
        ) TO '{cel.as_posix()}'
        (FORMAT parquet, COMPRESSION zstd, ROW_GROUP_SIZE {SORCSOPORT})""")
    con.execute("SET preserve_insertion_order = false")


def validal(con, pq: Path, zip_sorok: int) -> dict:
    """A kiirt Parquetbol visszaolvasva ellenoriz. Hibanal RuntimeError."""
    f = pq.as_posix()
    bbox = (f"Latitude BETWEEN {LAT_MIN} AND {LAT_MAX} "
            f"AND Longitude BETWEEN {LON_MIN} AND {LON_MAX}")
    r = con.execute(f"""
        SELECT count(*), sum(dup_db), count(*) FILTER (WHERE ts IS NULL),
               count(*) FILTER (WHERE h3 IS NULL),
               sum(dup_db) FILTER (WHERE {bbox}), count(*) FILTER (WHERE {bbox}),
               count(DISTINCT MMSI)
        FROM read_parquet('{f}')""").fetchone()
    dedup, nyers, ts_null, h3_null, bbox_nyers, bbox_dedup, hajo = r
    if nyers != zip_sorok:
        raise RuntimeError(f"sorszam-elteres: ZIP {zip_sorok:,}, Parquet SUM(dup_db) {nyers:,}")

    minta = con.execute(f"""
        SELECT Latitude, Longitude, h3 FROM read_parquet('{f}')
        WHERE h3 IS NOT NULL USING SAMPLE {H3_MINTA} ROWS""").fetchall()
    rossz = sum(1 for la, lo, c in minta
                if h3.str_to_int(h3.latlng_to_cell(la, lo, FELBONTAS)) != c)
    if rossz:
        raise RuntimeError(f"H3-elteres: {rossz}/{len(minta)} mintasor mas cellat kapott")

    return {"nyers_sor": nyers, "dedup_sor": dedup,
            "dup_arany": round(1 - dedup / nyers, 5),
            "bbox_nyers_sor": bbox_nyers, "bbox_dedup_sor": bbox_dedup,
            "bbox_dup_arany": round(1 - bbox_dedup / max(bbox_nyers, 1), 5),
            "ts_hibas_sor": ts_null, "h3_nelkuli_sor": h3_null,
            "egyedi_mmsi": hajo, "h3_minta_egyezik": len(minta)}


def dr_reteg(con, pq: Path, cel: Path) -> dict:
    """Dead reckoning a deduplikalt, ervenyes pozicioju pontokon."""
    df = con.execute(f"""
        SELECT {', '.join(DR_OSZLOPOK)} FROM read_parquet('{pq.as_posix()}')
        WHERE ts IS NOT NULL AND MMSI IS NOT NULL
          AND Latitude BETWEEN -90 AND 90 AND Longitude BETWEEN -180 AND 180
        ORDER BY MMSI, ts, sorrend""").df()
    # a DuckDB mikroszekundumos, a pandas nanoszekundumos idot adhat: egysegesitjuk
    t_mp = df["ts"].to_numpy().astype("datetime64[ns]").astype(np.int64) / 1e9
    tart, atlag, maxh = dead_reckoning_maszk(
        df["MMSI"].to_numpy(), t_mp,
        df["Latitude"].to_numpy(dtype=float), df["Longitude"].to_numpy(dtype=float),
        df["SOG"].to_numpy(dtype=float), df["COG"].to_numpy(dtype=float), DR_KUSZOB_M)
    kept = df[tart]
    con.register("dr_kept", kept)
    con.execute(f"""COPY (SELECT * FROM dr_kept) TO '{cel.as_posix()}'
                    (FORMAT parquet, COMPRESSION zstd, ROW_GROUP_SIZE {SORCSOPORT})""")
    con.unregister("dr_kept")
    return {"dr_bemenet_sor": len(df), "dr_megtartott_sor": int(tart.sum()),
            "dr_atlag_hiba_m": round(atlag, 2), "dr_max_hiba_m": round(maxh, 2)}


# --- Naplotabla (pipeline_napok.csv) ----------------------------------------

MEZOK = ["nap", "statusz", "sema", "hiba","zip_mib", "csv_mib", "zip_sor", "nyers_sor",
         "dedup_sor", "dup_arany", "bbox_nyers_sor", "bbox_dedup_sor", "bbox_dup_arany",
         "ts_hibas_sor", "h3_nelkuli_sor", "egyedi_mmsi", "h3_minta_egyezik",
         "parquet_mib", "dr_bemenet_sor", "dr_megtartott_sor", "dr_atlag_hiba_m",
         "dr_max_hiba_m", "dr_mib", "letoltes_mp", "kicsomagolas_mp", "parquet_mp",
         "validalas_mp", "dr_mp", "osszes_mp", "csucs_memoria_mib", "csucs_lemez_mib",
         "zip_torolve", "feldolgozva"]


def naplo_olvas(ut: Path) -> dict:
    if not ut.exists():
        return {}
    with ut.open(encoding="utf-8") as fh:
        return {s["nap"]: s for s in csv.DictReader(fh)}


def naplo_ir(ut: Path, sorok: dict):
    ut.parent.mkdir(parents=True, exist_ok=True)
    tmp = ut.with_suffix(".tmp")
    with tmp.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=MEZOK, extrasaction="ignore")
        w.writeheader()
        for nap in sorted(sorok):
            w.writerow(sorok[nap])
    os.replace(tmp, ut)


def kesz(sor, args, nap) -> bool:
    return (sor is not None and sor.get("statusz") == "validalt"
            and str(sor.get("sema")) == str(SEMA)
            and parquet_ut(args.tarolo, nap).exists()
            and (args.dr_kihagy or parquet_ut(args.tarolo_dr, nap).exists()))


# --- Egy nap ---------------------------------------------------------------

def egy_nap(nap: date, args, allapot=None, letoltes_mp=0.0) -> dict:
    """Egy nap feldolgozasa. A main() kulon gyerekfolyamatban hivja: egy
    hosszan futo folyamatban a napi ido a feldolgozott napok szamaval
    linearisan nott (6,5 -> 36,7 mp/millio sor 52 nap alatt; friss
    folyamatban ugyanaz a nap 8x gyorsabb volt - ld. naplo, 3. fazis)."""
    sor = {"nap": nap.isoformat(), "statusz": "hiba", "sema": SEMA, "hiba": "",
           "feldolgozva": datetime.now().isoformat(timespec="seconds")}
    t_kezd = time.perf_counter()
    zf = zip_ut(nap, args.adat)
    pq, dr = parquet_ut(args.tarolo, nap), parquet_ut(args.tarolo_dr, nap)
    munka = args.munka / nap.isoformat()

    with Mero(args.munka.parent) as mero:
        try:
            # 1. letoltes (a szulofolyamat elotolto szalabol, ha volt)
            t0 = time.perf_counter()
            if allapot is None:
                allapot = ("mar_megvan" if zf.exists() and ellenoriz_zip(zf)
                           else letolt_egy_napot(nap, args.adat, False))
            sor["letoltes_mp"] = round(letoltes_mp + time.perf_counter() - t0, 1)
            if allapot == "hiba" or not zf.exists():
                sor["statusz"] = "nincs_adat"
                sor["hiba"] = "a ZIP nem toltheto le (404 vagy halozati hiba)"
                return sor
            sor["zip_mib"] = round(mib(zf), 1)

            # 2. kicsomagolas + sorszamlalas
            if munka.exists():
                shutil.rmtree(munka)
            munka.mkdir(parents=True)
            t0 = time.perf_counter()
            csv_fajl, zip_sorok = kicsomagol(zf, munka)
            sor["kicsomagolas_mp"] = round(time.perf_counter() - t0, 1)
            sor["csv_mib"] = round(mib(csv_fajl), 1)
            sor["zip_sor"] = zip_sorok
            if args.torol_zip_kicsomagolas_utan:
                zf.unlink()
                sor["zip_torolve"] = "kicsomagolas utan"
            print(f"  kicsomagolva: {sor['csv_mib']:,.0f} MiB, {zip_sorok:,} sor "
                  f"({sor['kicsomagolas_mp']} mp)")

            # 3. Parquet (dedup + H3 + rendezes), atmeneti nevre
            con = duckdb_kapcsolat(munka, args.memoria)
            pq.parent.mkdir(parents=True, exist_ok=True)
            pq_tmp = pq.with_suffix(".parquet.tmp")
            t0 = time.perf_counter()
            csv_parquetbe(con, csv_fajl, pq_tmp)
            sor["parquet_mp"] = round(time.perf_counter() - t0, 1)
            csv_fajl.unlink()          # a nagy CSV-t minel elobb eltakaritjuk

            # 4. validalas
            t0 = time.perf_counter()
            sor.update(validal(con, pq_tmp, zip_sorok))
            sor["validalas_mp"] = round(time.perf_counter() - t0, 1)
            os.replace(pq_tmp, pq)
            sor["parquet_mib"] = round(mib(pq), 1)
            print(f"  Parquet: {sor['parquet_mib']:,.1f} MiB ({sor['parquet_mp']} mp) | "
                  f"nyers {sor['nyers_sor']:,} -> dedup. {sor['dedup_sor']:,} "
                  f"(duplikatum {sor['dup_arany']:.1%}; bboxban {sor['bbox_dup_arany']:.1%}) "
                  f"| VALIDALT")

            # 5. dead reckoning reteg
            if not args.dr_kihagy:
                dr.parent.mkdir(parents=True, exist_ok=True)
                dr_tmp = dr.with_suffix(".parquet.tmp")
                t0 = time.perf_counter()
                sor.update(dr_reteg(con, pq, dr_tmp))
                sor["dr_mp"] = round(time.perf_counter() - t0, 1)
                os.replace(dr_tmp, dr)
                sor["dr_mib"] = round(mib(dr), 1)
                print(f"  DR {DR_KUSZOB_M} m: {sor['dr_bemenet_sor']:,} -> "
                      f"{sor['dr_megtartott_sor']:,} pont, {sor['dr_mib']:,.1f} MiB "
                      f"({sor['dr_mp']} mp)")
            con.close()
            sor["statusz"] = "validalt"
        except Exception as e:             # technikai hiba: a nap hibas, megyunk tovabb
            sor["hiba"] = f"{type(e).__name__}: {e}"[:500]
            print(f"  HIBA: {sor['hiba']}")
            for f in (pq.with_suffix(".parquet.tmp"), dr.with_suffix(".parquet.tmp")):
                f.unlink(missing_ok=True)
        finally:
            shutil.rmtree(munka, ignore_errors=True)

    sor["osszes_mp"] = round(time.perf_counter() - t_kezd, 1)
    sor["csucs_memoria_mib"] = round(mero.csucs_mib)
    sor["csucs_lemez_mib"] = round(mero.lemez_csucs_mib)
    return sor


def zip_torles(nap, sor, args):
    """Csak validalt napnal, es csak ha nincs a megtartandok kozott."""
    zf = zip_ut(nap, args.adat)
    if (args.torol_zip and zf.exists() and sor.get("statusz") == "validalt"
            and nap.isoformat() not in args.megtart):
        zf.unlink()
        sor["zip_torolve"] = "igen"
        print(f"  ZIP torolve: {zf.name}")


# --- Fovonal ----------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("kezdo", nargs="?", help="YYYY-MM-DD")
    ap.add_argument("veg", nargs="?", help="YYYY-MM-DD (alap: = kezdo)")
    ap.add_argument("--zipbol", action="store_true",
                    help="A --adat mappa osszes aisdk-*.zip fajljat dolgozza fel")
    ap.add_argument("--adat", type=Path, default=ADAT)
    ap.add_argument("--tarolo", type=Path, default=TAROLO)
    ap.add_argument("--tarolo-dr", type=Path, default=TAROLO_DR)
    ap.add_argument("--munka", type=Path, default=MUNKA)
    ap.add_argument("--naplo", type=Path, default=NAPLO_CSV)
    ap.add_argument("--felulir", action="store_true", help="A kesz napot is ujracsinalja")
    ap.add_argument("--torol-zip", action="store_true",
                    help="Validalt nap ZIP-jet torli (alapbol NEM torol)")
    ap.add_argument("--megtart", nargs="*", default=[],
                    help="Ezeknek a napoknak a ZIP-jet --torol-zip mellett sem torli")
    ap.add_argument("--dr-kihagy", action="store_true",
                    help="A dead reckoning reteget nem kesziti el")
    ap.add_argument("--memoria", default=DUCKDB_MEMORIA,
                    help=f"DuckDB memoriakorlat (alap: {DUCKDB_MEMORIA}); nagyobb "
                         "ertek kevesebb lemezre lapozast jelent")
    ap.add_argument("--torol-zip-kicsomagolas-utan", action="store_true",
                    help="A ZIP-et mar a kicsomagolas utan torli (szuk lemezu "
                         "futtatohoz; hiba eseten ujra le kell tolteni)")
    ap.add_argument("--nincs-elotoltes", action="store_true",
                    help="Ne toltse le a kovetkezo napot az aktualis feldolgozasa alatt")
    args = ap.parse_args()

    if args.zipbol:
        napok = sorted(date.fromisoformat(p.stem.replace("aisdk-", ""))
                       for p in args.adat.glob("aisdk-*.zip"))
    elif args.kezdo:
        k = date.fromisoformat(args.kezdo)
        napok = list(datum_tartomany(k, date.fromisoformat(args.veg) if args.veg else k))
    else:
        sys.exit("Adj meg datumot vagy --zipbol kapcsolot.")

    args.adat.mkdir(parents=True, exist_ok=True)
    args.munka.mkdir(parents=True, exist_ok=True)
    naplo = naplo_olvas(args.naplo)
    teendo = [n for n in napok if args.felulir or not kesz(naplo.get(n.isoformat()), args, n)]
    print(f"Napok: {len(napok)} ({napok[0]} - {napok[-1]}), ebbol kesz: "
          f"{len(napok) - len(teendo)}, feldolgozando: {len(teendo)}")

    # a mar kesz napok ZIP-je is torolheto, ha validalt
    if args.torol_zip:
        for n in napok:
            if n not in teendo:
                zip_torles(n, naplo[n.isoformat()], args)
        naplo_ir(args.naplo, naplo)

    t_start = time.perf_counter()
    eredmeny = {"validalt": 0, "hiba": 0, "nincs_adat": 0}

    def letolt(n):
        zf = zip_ut(n, args.adat)
        if zf.exists() and ellenoriz_zip(zf):
            return "mar_megvan"
        return letolt_egy_napot(n, args.adat, False)

    with ThreadPoolExecutor(max_workers=1) as pool, \
            ProcessPoolExecutor(max_workers=1, max_tasks_per_child=1) as napi:
        jovo = None
        for i, nap in enumerate(teendo):
            print(f"\n=== {nap} ({i + 1}/{len(teendo)}) ===")
            if jovo is None:
                jovo = pool.submit(letolt, nap)
            # a kovetkezo nap letoltese elindul, mikozben ezt feldolgozzuk
            kov = (pool.submit(letolt, teendo[i + 1])
                   if not args.nincs_elotoltes and i + 1 < len(teendo) else None)
            t0 = time.perf_counter()
            allapot = jovo.result()          # a letoltesre varas a nap idejebe szamit
            # minden nap friss gyerekfolyamatban (max_tasks_per_child=1)
            sor = napi.submit(egy_nap, nap, args, allapot,
                              time.perf_counter() - t0).result()
            zip_torles(nap, sor, args)
            naplo[nap.isoformat()] = sor
            naplo_ir(args.naplo, naplo)
            eredmeny[sor["statusz"]] = eredmeny.get(sor["statusz"], 0) + 1
            print(f"  -> {sor['statusz']}, {sor['osszes_mp']} mp, csucs memoria "
                  f"{sor['csucs_memoria_mib']:,} MiB, csucs lemez {sor['csucs_lemez_mib']:,} MiB")
            jovo = kov

    # --- Osszefoglalo az osszes kert napra ---
    sorok = [naplo[n.isoformat()] for n in napok if n.isoformat() in naplo]
    ok = [s for s in sorok if s.get("statusz") == "validalt"]
    print(f"\n=== Osszefoglalo ({time.perf_counter() - t_start:.0f} mp ebben a futasban) ===")
    print(f"Ebben a futasban: {eredmeny['validalt']} validalt, {eredmeny['hiba']} hiba, "
          f"{eredmeny['nincs_adat']} nincs adat")
    print(f"Validalt napok osszesen: {len(ok)}/{len(napok)}")
    if ok:
        osszeg = lambda k: sum(float(s[k] or 0) for s in ok)
        print(f"  nyers sor:   {osszeg('nyers_sor'):>15,.0f}")
        print(f"  dedup. sor:  {osszeg('dedup_sor'):>15,.0f}  "
              f"(duplikatum {1 - osszeg('dedup_sor') / osszeg('nyers_sor'):.1%})")
        print(f"  ZIP:         {osszeg('zip_mib'):>12,.0f} MiB")
        print(f"  Parquet:     {osszeg('parquet_mib'):>12,.0f} MiB "
              f"({osszeg('parquet_mib') / max(osszeg('zip_mib'), 1):.1%} a ZIP-hez)")
        print(f"  DR 50 m:     {osszeg('dr_mib'):>12,.0f} MiB")
        ido = [float(s["osszes_mp"]) for s in ok if s.get("osszes_mp")]
        mem = [float(s["csucs_memoria_mib"]) for s in ok if s.get("csucs_memoria_mib")]
        if ido:
            print(f"  futasi ido/nap: median {np.median(ido):.0f} mp, max {max(ido):.0f} mp")
        if mem:
            print(f"  csucs memoria: max {max(mem):,.0f} MiB")
    rossz = [s for s in sorok if s.get("statusz") != "validalt"]
    for s in rossz:
        print(f"  NEM VALIDALT: {s['nap']} {s['statusz']} {s.get('hiba', '')}")
    return 1 if rossz else 0


if __name__ == "__main__":
    sys.exit(main())
