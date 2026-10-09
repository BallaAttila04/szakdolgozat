"""
A napi forgalmi monitor egy teljes futasa - ezt hivja az utemezo.

  1. Melyik napok hianyoznak a monitor-tablabol? (az utolso meglevo nap utan,
     legfeljebb a tegnapelott-elotti napig, mert a szerver a napi fajlt kb.
     48 oraval a nap vege utan teszi kozze - ld. naplo, 6a)
  2. pipeline.py ezekre a napokra (letoltes, validalas, Parquet; a ZIP-et
     validalas utan torli)
  3. monitor.py: csak a validalt napok kerulnek a tablaba
  4. oldal_epit.py --csak-monitor: a publikus oldal monitor-szakasza

Hibakezeles: ha a napi fajl meg nincs fenn, vagy a validalas bukik, a
monitor-tabla nem valtozik (a korabbi jo adat marad), es az oldalon latszik,
hogy a legutobbi futas nem frissitett, illetve melyik nap a legutolso.

Hasznalat:
    python napi_futas.py                 # helyben vagy GitHub Actionsben
    python napi_futas.py --parquet-torol # a napi Parquetet a vegen torli (runner)
"""

import argparse
import csv
import json
import subprocess
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from utak import KIMENET, OLDAL

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)
except AttributeError:
    pass

SZKRIPTEK = Path(__file__).resolve().parent
MONITOR = KIMENET / "monitor"

# A szerver a D napi fajlt D+3 00:18-00:24 UTC kozott teszi kozze (14 nap
# Last-Modified fejlece alapjan, ld. naplo 6a). A futas 03:30 UTC-kor
# indul, ekkor a legfrissebb elerheto nap: ma - 3.
KESES_NAP = 3
# Egy futas legfeljebb ennyi hianyzo napot potol (ha az utemezes napokig
# kimaradt). Egy nap ~3-6 perc, igy a 6 oras job-korlat bőven eleg.
MAX_POTLAS = 7


def futtat(*parancs):
    print(f"\n$ {' '.join(str(p) for p in parancs)}", flush=True)
    return subprocess.run([sys.executable, *map(str, parancs)]).returncode


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--ma", help="A futas napja (teszthez), alap: a mai UTC nap")
    ap.add_argument("--parquet-torol", action="store_true",
                    help="A napi Parquetet a monitor utan torli (ideiglenes futtato)")
    ap.add_argument("--oldal", type=Path, default=OLDAL)
    ap.add_argument("--memoria", help="DuckDB memoriakorlat a pipeline.py-nak")
    ap.add_argument("--kozvetlen-zip", action="store_true",
                    help="Szuk lemezu futtatohoz: a CSV-t nem csomagolja ki (ld. naplo 6a)")
    args = ap.parse_args()

    ma = date.fromisoformat(args.ma) if args.ma else datetime.now(timezone.utc).date()
    utolso_elerheto = ma - timedelta(days=KESES_NAP)
    allapot_f = MONITOR / "allapot.json"
    allapot = json.loads(allapot_f.read_text(encoding="utf-8")) if allapot_f.exists() else {}
    utolso = date.fromisoformat(allapot["utolso_nap"]) if allapot.get("utolso_nap") \
        else utolso_elerheto - timedelta(days=1)
    kezdo = max(utolso + timedelta(days=1), utolso_elerheto - timedelta(days=MAX_POTLAS - 1))
    print(f"Futas: {ma}; a monitor utolso napja: {utolso}; "
          f"feldolgozando: {kezdo} - {utolso_elerheto}")

    futas = {"ido_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
             "statusz": "ok", "uzenet": ""}
    if kezdo > utolso_elerheto:
        futas["uzenet"] = "nincs uj nap"
    else:
        extra = (["--memoria", args.memoria] if args.memoria else []) + \
            (["--kozvetlen-zip"] if args.kozvetlen_zip else [])
        futtat(SZKRIPTEK / "pipeline.py", kezdo.isoformat(), utolso_elerheto.isoformat(),
               "--torol-zip", "--dr-kihagy", *extra)
        with (KIMENET / "pipeline_napok.csv").open(encoding="utf-8") as fh:
            napok = {s["nap"]: s for s in csv.DictReader(fh)}
        kert = [(kezdo + timedelta(days=i)).isoformat()
                for i in range((utolso_elerheto - kezdo).days + 1)]
        jo = [d for d in kert if napok.get(d, {}).get("statusz") == "validalt"]
        rossz = [f"{d}: {napok.get(d, {}).get('statusz', 'nem futott')}" for d in kert
                 if d not in jo]
        if jo and futtat(SZKRIPTEK / "monitor.py", "--napok", *jo) != 0:
            futas.update(statusz="hiba", uzenet="a monitor.py hibaval allt le")
        elif rossz:
            futas.update(statusz="hiba" if not jo else "reszleges",
                         uzenet="nem validalt nap(ok): " + "; ".join(rossz))
        else:
            futas["uzenet"] = f"{len(jo)} uj nap"
        if args.parquet_torol:
            for d in jo:
                for p in (KIMENET / "tarolo").rglob(f"aisdk-{d}.parquet"):
                    p.unlink()

    # az utolso futas allapota az allapot.json-ba (a monitor.py felulirhatta)
    allapot = json.loads(allapot_f.read_text(encoding="utf-8")) if allapot_f.exists() else {}
    allapot["utolso_futas"] = futas
    MONITOR.mkdir(parents=True, exist_ok=True)
    allapot_f.write_text(json.dumps(allapot, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\nFutas allapota: {futas['statusz']} - {futas['uzenet']}")

    if allapot.get("utolso_nap"):
        futtat(SZKRIPTEK / "oldal_epit.py", "--csak-monitor", "--oldal", args.oldal)
    # Ha nem volt uj adat, az nem hiba; a validalas bukasa igen (a workflow jelezze).
    return 1 if futas["statusz"] == "hiba" else 0


if __name__ == "__main__":
    sys.exit(main())
