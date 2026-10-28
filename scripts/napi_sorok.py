"""
Az eles uzem napi sorszamai a GitHub Actions futasnaploibol.

A napi futas (napi_futas.py -> pipeline.py) a Parquet-fajlt a futtaton
torli (--parquet-torol), igy a 2026-10-07 utani napok nyers es deduplikalt
sorszama, Parquet- es ZIP-merete csak a futasnaplokban marad meg. A GitHub
ezeket 90 napig orzi; ez a szkript a lementett naplokbol (futasnaplok/<id>.txt,
gh run view <id> --log) egy CSV-be gyujti oket.

A naplo napi blokkja (pipeline.py, 2026-10-22-i allapot):
  === 2026-10-19 (1/1) ===
    aisdk-2026-10-19.zip: kesz (578.2 MB)          <- letoltes.py; az ertek MiB
    sorszamlalas (kozvetlen ZIP): 0 MiB, 16,677,275 sor (9.3 mp)
    Parquet: 130.4 MiB (59.7 mp) | nyers 16,677,275 -> dedup. 10,314,516 (...) | VALIDALT

A letoltes.py a meretet 1 048 576-tal osztja, de "MB"-t ir ki: a zip_mib
oszlop ezert MiB. Csak a VALIDALT napok kerulnek a kimenetbe; egy nap tobbszor
is szerepelhet (pl. 2026-07-15: ket eroforras-meresi futas), run_id-vel.

Ellenorzes (--tarolo): ahol a nap a helyi Parquet-taroloban is megvan, ott
DuckDB-vel SUM(dup_db) (= nyers sor) es count(*) (= dedup. sor), valamint a
fajlmeret; ha van, a helyi pipeline_napok.csv ZIP-merete is. Az elteres a
kimenetben marad, nem igazitjuk ki.

Hasznalat:
    python napi_sorok.py
    python napi_sorok.py --letolt            # a hianyzo naplokat gh-val lementi
    python napi_sorok.py --naplok outputs/eles_uzem/futasnaplok --ki napi_sorok.csv
"""

import argparse
import csv
import re
import subprocess
import sys
from pathlib import Path

import duckdb

from utak import KIMENET

ELES = KIMENET / "eles_uzem"

# A napi blokk sorai (pipeline.py / letoltes.py kiirasa). Ha a kiiras formatuma
# valtozik, ezeket kell igazitani; a nem illeszkedo naplo 0 napot ad, es ez az
# osszefoglaloban latszik.
NAP_RE = re.compile(r"=== (\d{4}-\d{2}-\d{2}) \(\d+/\d+\) ===")
ZIP_RE = re.compile(r"aisdk-(\d{4}-\d{2}-\d{2})\.zip: kesz \(([\d.]+) MB\)")
SZAML_RE = re.compile(r"sorszamlalas \(kozvetlen ZIP\): .*?([\d,]+) sor")
PARQUET_RE = re.compile(r"Parquet: ([\d.]+) MiB \(.*?\) \| nyers ([\d,]+) -> dedup\. ([\d,]+) .*\| (\S+)\s*$")

# A naplo a Parquet-meretet egy tizedesre kerekiti, ezert a helyi fajlmerettel
# valo osszevetesnel 0,05 MiB a kerekitesi hatar; ennel nagyobb elteres
# valodi kulonbseg.
MIB_TURES = 0.05

OSZLOPOK = ["nap", "nyers_sor", "dedup_sor", "parquet_mib", "zip_mib", "run_id"]


def szam(s: str) -> int:
    return int(s.replace(",", ""))


def letolt(futasok: Path, naplok: Path) -> None:
    naplok.mkdir(parents=True, exist_ok=True)
    with open(futasok, encoding="utf-8") as f:
        idk = [r["databaseId"] for r in csv.DictReader(f)]
    for rid in idk:
        cel = naplok / f"{rid}.txt"
        if cel.exists() and cel.stat().st_size > 0:
            continue
        ki = subprocess.run(["gh", "run", "view", rid, "--log"], capture_output=True)
        if ki.returncode != 0:
            print(f"  HIBA {rid}: {ki.stderr.decode(errors='replace').strip()}")
            continue
        cel.write_bytes(ki.stdout)
        print(f"  lementve: {cel.name} ({len(ki.stdout):,} bajt)")


def naplo_feldolgoz(ut: Path):
    """Egy naplo VALIDALT napjai (soronkent olvasva)."""
    sorok, nem_valid, olvasott = [], [], 0
    nap = zip_mib = szaml = None
    with open(ut, encoding="utf-8-sig", errors="replace") as f:
        for sor in f:
            olvasott += 1
            if m := NAP_RE.search(sor):
                nap, zip_mib, szaml = m.group(1), None, None
            elif nap and (m := ZIP_RE.search(sor)) and m.group(1) == nap:
                zip_mib = float(m.group(2))
            elif nap and (m := SZAML_RE.search(sor)):
                szaml = szam(m.group(1))
            elif nap and (m := PARQUET_RE.search(sor)):
                if m.group(4) != "VALIDALT":
                    nem_valid.append((nap, m.group(4)))
                else:
                    nyers = szam(m.group(2))
                    if szaml is not None and szaml != nyers:
                        print(f"  FIGYELEM {ut.stem} {nap}: ZIP-sorszamlalas {szaml:,} != nyers {nyers:,}")
                    sorok.append({"nap": nap, "nyers_sor": nyers, "dedup_sor": szam(m.group(3)),
                                  "parquet_mib": float(m.group(1)), "zip_mib": zip_mib,
                                  "run_id": ut.stem})
                nap = None
    return sorok, nem_valid, olvasott


def ellenoriz(sorok, tarolo: Path, pipeline_csv: Path, ki_ut: Path) -> int:
    helyi_zip = {}
    if pipeline_csv.exists():
        with open(pipeline_csv, encoding="utf-8") as f:
            helyi_zip = {r["nap"]: r["zip_mib"] for r in csv.DictReader(f) if r["statusz"] == "validalt"}
    con = duckdb.connect()
    ki, elteres = [], 0
    for s in sorok:
        fajl = tarolo / f"ev={s['nap'][:4]}" / f"ho={s['nap'][5:7]}" / f"aisdk-{s['nap']}.parquet"
        if not fajl.exists():
            continue
        dedup, nyers = con.execute(
            "SELECT count(*), sum(dup_db) FROM read_parquet(?)", [str(fajl)]).fetchone()
        mib = fajl.stat().st_size / 2**20
        hz = float(helyi_zip[s["nap"]]) if s["nap"] in helyi_zip else None
        hibak = []
        if nyers != s["nyers_sor"]:
            hibak.append(f"nyers {nyers - s['nyers_sor']:+,}")
        if dedup != s["dedup_sor"]:
            hibak.append(f"dedup {dedup - s['dedup_sor']:+,}")
        if abs(mib - s["parquet_mib"]) > MIB_TURES:
            hibak.append(f"parquet {mib - s['parquet_mib']:+.2f} MiB")
        if hz is not None and s["zip_mib"] is not None and hz != s["zip_mib"]:
            hibak.append(f"zip {hz - s['zip_mib']:+.1f} MiB")
        elteres += bool(hibak)
        ki.append({"nap": s["nap"], "run_id": s["run_id"],
                   "naplo_nyers": s["nyers_sor"], "helyi_nyers": nyers,
                   "naplo_dedup": s["dedup_sor"], "helyi_dedup": dedup,
                   "naplo_parquet_mib": s["parquet_mib"], "helyi_parquet_mib": round(mib, 3),
                   "naplo_zip_mib": s["zip_mib"], "helyi_zip_mib": hz,
                   "elteres": "; ".join(hibak) or "nincs"})
        print(f"  {s['nap']} run {s['run_id']}: nyers {nyers:,} / {s['nyers_sor']:,}, "
              f"dedup {dedup:,} / {s['dedup_sor']:,}, Parquet {mib:.3f} / {s['parquet_mib']} MiB, "
              f"ZIP {hz} / {s['zip_mib']} MiB -> {'; '.join(hibak) or 'egyezik'}")
    if ki:
        with open(ki_ut, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(ki[0]))
            w.writeheader()
            w.writerows(ki)
        print(f"-> {ki_ut}")
    print(f"Ellenorizve (a helyi taroloban is megvan): {len(ki)} nap-sor, ebbol elteressel: {elteres}")
    return elteres


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--naplok", type=Path, default=ELES / "futasnaplok")
    ap.add_argument("--futasok", type=Path, default=ELES / "futasok.csv",
                    help="a futasok listaja (databaseId oszlop); --letolt-hoz")
    ap.add_argument("--letolt", action="store_true",
                    help="a futasok.csv hianyzo naploit gh run view --log-gal lementi")
    ap.add_argument("--ki", type=Path, default=ELES / "napi_sorok.csv")
    ap.add_argument("--tarolo", type=Path, default=KIMENET / "tarolo")
    ap.add_argument("--pipeline-csv", type=Path, default=KIMENET / "pipeline_napok.csv")
    ap.add_argument("--ellenorzes-ki", type=Path, default=ELES / "napi_sorok_ellenorzes.csv")
    args = ap.parse_args()

    if args.letolt:
        letolt(args.futasok, args.naplok)

    naplok = sorted(args.naplok.glob("*.txt"))
    if not naplok:
        sys.exit(f"Nincs naplo: {args.naplok}")
    sorok, olvasott, ures = [], 0, []
    for ut in naplok:
        s, nv, n = naplo_feldolgoz(ut)
        olvasott += n
        sorok += s
        if not s:
            ures.append(ut.stem)
        for nap, allapot in nv:
            print(f"  NEM VALIDALT: {ut.stem} {nap} {allapot}")
    sorok.sort(key=lambda r: (r["nap"], r["run_id"]))

    with open(args.ki, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=OSZLOPOK)
        w.writeheader()
        w.writerows(sorok)

    napok = [r["nap"] for r in sorok]
    tobbszor = sorted({n for n in napok if napok.count(n) > 1})
    print(f"Naplo: {len(naplok)} fajl, {olvasott:,} sor beolvasva")
    print(f"Validalt nap-sor: {len(sorok)} ({len(set(napok))} kulonbozo nap"
          + (f"; tobbszor: {', '.join(tobbszor)}" if tobbszor else "") + ")")
    print(f"Nap nelkuli naplo (nem dolgozott fel napot): {len(ures)}"
          + (f" ({', '.join(ures)})" if ures else ""))
    if sorok:
        print(f"Idoszak: {sorok[0]['nap']} - {sorok[-1]['nap']}; "
              f"hianyzo ZIP-meret: {sum(r['zip_mib'] is None for r in sorok)}")
    print(f"-> {args.ki}")

    print("\nOsszevetes a helyi taroloval (DuckDB):")
    ellenoriz(sorok, args.tarolo, args.pipeline_csv, args.ellenorzes_ki)


if __name__ == "__main__":
    main()
