"""
Skalazasi meres: DuckDB vs Polars vs Spark ugyanazon a Parquet-tarolon,
1 nap / 7 nap / 1 honap / 3 honap adaton, plusz a nyers CSV addig, ameddig
az esszeru (ld. CSV_MERETEK).

Minden (motor, adatmeret) par kulon folyamatban fut
(tarolas_benchmark.py --tarolo-meres), igy a csucs memoria - a folyamat es
gyerekei, Sparknal a JVM is - ehhez a parhoz rendelheto. Lekerdezesenkent
ISMETLES ismetles, median. A motoroknak minden adatmereten pontosan ugyanazt
kell visszaadniuk; ha nem, a sor "egyezik=nem" jelolest kap, es a szkript
1-es koddal lep ki.

Kimenet: outputs/skalazas.csv, outputs/skalazas.png

Hasznalat:
    python skalazas.py
    python skalazas.py --meretek 1_nap 7_nap --motorok duckdb_parquet polars_parquet
"""

import argparse
import csv
import json
import shutil
import statistics
import subprocess
import sys
import tempfile
import time
import zipfile
from datetime import date
from pathlib import Path

import psutil

from utak import ADAT, KIMENET
from letoltes import datum_tartomany
from pipeline import TAROLO, parquet_ut

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)
except AttributeError:
    pass

# --- Parameterek ----------------------------------------------------------

MERETEK = {
    "1_nap": ("2026-07-15", "2026-07-15"),
    "7_nap": ("2026-07-15", "2026-07-21"),
    "1_honap": ("2026-07-01", "2026-07-31"),
    "3_honap": ("2026-06-01", "2026-08-31"),
}
MOTOROK = ["duckdb_parquet", "polars_parquet", "spark_parquet"]

# Nyers CSV csak 1 napra: egy nap kicsomagolva 6,1 GiB, a 7 napos keszlet
# ~40 GiB lenne, ami a lemezre nem fer ki a tarolo mellett, es a pandas-ag
# mar 1 napon is ~150 mp/ismetles (szamok.md). Ld. naplo, 4. fazis.
CSV_MERETEK = {"1_nap"}
CSV_MOTOROK = ["duckdb_csv", "pandas_csv"]

ISMETLES = 3
MERES_IDOKOZ_MP = 0.2
IDOKORLAT_MP = 3 * 3600

LEKERDEZESEK = ["sorszam", "egyedi_hajo", "bbox_szures", "oranankenti_bbox"]


def fut_es_mer(parancs):
    """Elinditja a parancsot, es a folyamatfa csucs RSS-et meri."""
    t0 = time.perf_counter()
    p = subprocess.Popen(parancs)
    pp = psutil.Process(p.pid)
    csucs = 0
    while p.poll() is None:
        try:
            rss = pp.memory_info().rss
            for gy in pp.children(recursive=True):
                try:
                    rss += gy.memory_info().rss
                except psutil.Error:
                    pass
            csucs = max(csucs, rss)
        except psutil.Error:
            pass
        if time.perf_counter() - t0 > IDOKORLAT_MP:
            p.kill()
            return -1, csucs, time.perf_counter() - t0
        time.sleep(MERES_IDOKOZ_MP)
    return p.returncode, csucs, time.perf_counter() - t0


def osszevet(a, b):
    """A ket eredmeny kozos kulcsain egyezik-e (a pandas-ag csak harmat ad)."""
    kozos = [k for k in LEKERDEZESEK if k in a and k in b]
    if "oranankenti_bbox" in kozos:
        a = dict(a, oranankenti_bbox=[list(x) for x in a["oranankenti_bbox"]])
        b = dict(b, oranankenti_bbox=[list(x) for x in b["oranankenti_bbox"]])
    return all(a[k] == b[k] for k in kozos), kozos


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--meretek", nargs="+", default=list(MERETEK))
    ap.add_argument("--motorok", nargs="+", default=MOTOROK + CSV_MOTOROK)
    ap.add_argument("--ismetles", type=int, default=ISMETLES)
    ap.add_argument("--tarolo", type=Path, default=TAROLO)
    ap.add_argument("--adat", type=Path, default=ADAT)
    ap.add_argument("--ki", type=Path, default=KIMENET / "skalazas.csv")
    ap.add_argument("--abra", type=Path, default=KIMENET / "skalazas.png")
    args = ap.parse_args()

    benchmark = Path(__file__).with_name("tarolas_benchmark.py")
    napok_csv = {s["nap"]: s for s in csv.DictReader(
        (KIMENET / "pipeline_napok.csv").open(encoding="utf-8"))}
    sorok, hibas = [], False

    for meret in args.meretek:
        k, v = (date.fromisoformat(x) for x in MERETEK[meret])
        napok = list(datum_tartomany(k, v))
        fajlok = [parquet_ut(args.tarolo, n) for n in napok]
        megvan = [f for f, n in zip(fajlok, napok) if f.exists()
                  and napok_csv.get(n.isoformat(), {}).get("statusz") == "validalt"]
        if not megvan:
            print(f"\n{meret}: nincs validalt nap, kihagyva")
            continue
        nyers = sum(int(napok_csv[f.stem.replace("aisdk-", "")]["nyers_sor"]) for f in megvan)
        dedup = sum(int(napok_csv[f.stem.replace("aisdk-", "")]["dedup_sor"]) for f in megvan)
        pq_mib = sum(f.stat().st_size for f in megvan) / 1_048_576
        print(f"\n=== {meret}: {len(megvan)}/{len(napok)} nap, {nyers:,} nyers / "
              f"{dedup:,} tarolt sor, {pq_mib:,.0f} MiB Parquet ===")

        motorok = [m for m in args.motorok if m in MOTOROK]
        csv_dir = None
        if meret in CSV_MERETEK and any(m in CSV_MOTOROK for m in args.motorok):
            zipek = [args.adat / f"aisdk-{n.isoformat()}.zip" for n in napok]
            if all(z.exists() for z in zipek):
                csv_dir = Path(tempfile.mkdtemp(dir=KIMENET, prefix="skalazas_csv_"))
                for z in zipek:
                    with zipfile.ZipFile(z) as zf:
                        tag = zf.namelist()[0]
                        with zf.open(tag) as be, open(csv_dir / Path(tag).name, "wb") as ki:
                            shutil.copyfileobj(be, ki, 16 * 1024 * 1024)
                motorok += [m for m in args.motorok if m in CSV_MOTOROK]
            else:
                print("  a nyers CSV-merés kimarad: hianyzik a ZIP")

        referencia = None
        for motor in motorok:
            bemenet = sorted(csv_dir.glob("*.csv")) if motor in CSV_MOTOROK else megvan
            meret_mib = (sum(f.stat().st_size for f in bemenet) / 1_048_576
                         if motor in CSV_MOTOROK else pq_mib)
            jfajl = Path(tempfile.mktemp(suffix=".json"))
            print(f"  {motor} ...")
            kod, csucs, fal = fut_es_mer(
                [sys.executable, str(benchmark), "--tarolo-meres", "--motor", motor,
                 "--ismetles", str(args.ismetles), "--json", str(jfajl)]
                + [str(f) for f in bemenet])
            sor = {"meret": meret, "napok": len(megvan), "nyers_sor": nyers,
                   "tarolt_sor": dedup, "motor": motor, "bemenet_mib": round(meret_mib, 1),
                   "csucs_memoria_mib": round(csucs / 1_048_576), "fal_ido_mp": round(fal, 1)}
            if kod != 0 or not jfajl.exists():
                sor["egyezik"] = f"HIBA (kilepesi kod {kod})"
                hibas = True
                sorok.append(sor)
                print(f"    HIBA, kilepesi kod {kod}")
                continue
            j = json.loads(jfajl.read_text(encoding="utf-8"))
            jfajl.unlink()
            sor["inditas_mp"] = round(j["inditas_mp"], 2)
            idok = j["idok"]
            for nev in LEKERDEZESEK:
                if idok.get(nev):
                    sor[f"{nev}_mp"] = round(statistics.median(idok[nev]), 3)
            if idok.get("mind_a_negy_egyutt"):
                sor["negy_egyutt_mp"] = round(statistics.median(idok["mind_a_negy_egyutt"]), 2)
            else:
                ossz = [sum(idok[n][i] for n in LEKERDEZESEK) for i in range(args.ismetles)]
                sor["negy_egyutt_mp"] = round(statistics.median(ossz), 3)
            if referencia is None:
                referencia = j["eredmeny"]
                sor["egyezik"] = "referencia"
            else:
                ok, kozos = osszevet(referencia, j["eredmeny"])
                sor["egyezik"] = ("igen" if ok else "NEM") + f" ({len(kozos)} lekerdezes)"
                hibas |= not ok
            sor["eredmeny_sorszam"] = j["eredmeny"].get("sorszam")
            sor["eredmeny_hajo"] = j["eredmeny"].get("egyedi_hajo")
            sor["eredmeny_bbox"] = j["eredmeny"].get("bbox_szures")
            sorok.append(sor)
            print(f"    4 lekerdezes: {sor['negy_egyutt_mp']} mp (median), inditas "
                  f"{sor['inditas_mp']} mp, csucs memoria {sor['csucs_memoria_mib']:,} MiB, "
                  f"egyezik: {sor['egyezik']}")
        if csv_dir:
            shutil.rmtree(csv_dir, ignore_errors=True)

        # minden meret utan kiirjuk, hogy megszakadas eseten se vesszen el
        mezok = list(dict.fromkeys(k for s in sorok for k in s))
        with args.ki.open("w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=mezok)
            w.writeheader()
            w.writerows(sorok)

    abra(sorok, args.abra)
    print(f"\n-> {args.ki}\n-> {args.abra}")
    return 1 if hibas else 0


def abra(sorok, ut):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    nevek = {"duckdb_parquet": "DuckDB + Parquet", "polars_parquet": "Polars + Parquet",
             "spark_parquet": "Spark (helyi mód) + Parquet", "duckdb_csv": "DuckDB + nyers CSV",
             "pandas_csv": "pandas + nyers CSV"}
    fig, ax = plt.subplots(figsize=(8, 5))
    for motor, nev in nevek.items():
        r = [s for s in sorok if s["motor"] == motor and s.get("negy_egyutt_mp")]
        if not r:
            continue
        x = [s["nyers_sor"] / 1e6 for s in r]
        y = [s["negy_egyutt_mp"] for s in r]
        ax.plot(x, y, marker="o", label=nev)
        if motor == "spark_parquet":
            ax.plot(x, [s["negy_egyutt_mp"] + s["inditas_mp"] for s in r], marker="x",
                    linestyle=":", color=ax.lines[-1].get_color(),
                    label=nev + ", session-indulással")
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("adatméret (millió nyers AIS-sor, log)")
    ax.set_ylabel("4 lekérdezés ideje, medián (mp, log)")
    ax.set_title("Lekérdezési idő az adatméret függvényében")
    ax.grid(True, which="both", alpha=0.3)
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(ut, dpi=150)


if __name__ == "__main__":
    sys.exit(main())
