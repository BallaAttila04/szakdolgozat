"""
Mely napok erhetok el a dan AIS-szerveren, mekkorak, es mikor jelentek meg?

Napi HTTP HEAD keres (letoltes nelkul): Content-Length es Last-Modified.
A "keses" a nap vegehez (kovetkezo nap 00:00 UTC) kepest eltelt ido a fajl
Last-Modified idejeig. Ebbol jon az utemezett napi futas idopontja (6a).

Hasznalat:
    python szerver_napok.py 2026-06-01 2026-08-31
    python szerver_napok.py --utolso 14 --ki outputs/szerver_keses.csv
"""

import argparse
import csv
import statistics
import sys
from datetime import date, datetime, timedelta, timezone
from email.utils import parsedate_to_datetime

import requests

from utak import KIMENET
from letoltes import BASE_URL, FILENAME_FORMAT, datum_tartomany

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except AttributeError:
    pass

TIMEOUT_MP = 20


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("kezdo", nargs="?")
    ap.add_argument("veg", nargs="?")
    ap.add_argument("--utolso", type=int, help="Az utolso N nap (tegnaptol visszafele)")
    ap.add_argument("--ki", default=KIMENET / "szerver_napok.csv")
    args = ap.parse_args()

    if args.utolso:
        veg = date.today() - timedelta(days=1)
        kezdo = veg - timedelta(days=args.utolso - 1)
    elif args.kezdo:
        kezdo = date.fromisoformat(args.kezdo)
        veg = date.fromisoformat(args.veg) if args.veg else kezdo
    else:
        sys.exit("Adj meg datumot vagy --utolso N-et.")

    s = requests.Session()
    sorok = []
    for nap in datum_tartomany(kezdo, veg):
        url = f"{BASE_URL}/{FILENAME_FORMAT.format(date=nap.isoformat())}"
        sor = {"nap": nap.isoformat(), "http": "", "bajt": "", "last_modified_utc": "",
               "keses_ora": ""}
        try:
            r = s.head(url, timeout=TIMEOUT_MP, allow_redirects=True)
            sor["http"] = r.status_code
            if r.ok:
                sor["bajt"] = int(r.headers.get("Content-Length", 0))
                lm = r.headers.get("Last-Modified")
                if lm:
                    t = parsedate_to_datetime(lm).astimezone(timezone.utc)
                    nap_vege = datetime(nap.year, nap.month, nap.day, tzinfo=timezone.utc) \
                        + timedelta(days=1)
                    sor["last_modified_utc"] = t.isoformat(timespec="seconds")
                    sor["keses_ora"] = round((t - nap_vege).total_seconds() / 3600, 2)
        except requests.RequestException as e:
            sor["http"] = f"hiba: {type(e).__name__}"
        sorok.append(sor)
        print(f"  {sor['nap']}  {sor['http']}  {str(sor['bajt']):>12}  "
              f"{sor['last_modified_utc']:<26} {sor['keses_ora']}")

    with open(args.ki, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(sorok[0]))
        w.writeheader()
        w.writerows(sorok)

    ok = [r for r in sorok if r["http"] == 200]
    hiany = [r["nap"] for r in sorok if r["http"] != 200]
    print(f"\n{len(sorok)} nap lekerdezve, {len(ok)} elerheto, {len(hiany)} hianyzik"
          + (f": {', '.join(hiany)}" if hiany else ""))
    if ok:
        print(f"Osszmeret: {sum(r['bajt'] for r in ok) / 1073741824:.1f} GiB")
    kes = [r["keses_ora"] for r in ok if r["keses_ora"] != ""]
    if kes:
        print(f"Keses a nap vegehez (UTC) kepest: median {statistics.median(kes):.1f} ora, "
              f"min {min(kes):.1f}, max {max(kes):.1f}")
    print(f"-> {args.ki}")


if __name__ == "__main__":
    main()
