"""
A tarolasi sorrend haszna a lekerdezett terulet meretenek fuggvenyeben.

A h3_tarolas.py egyetlen kis teruleten mert kb. 5x-os gyorsulast a H3 szerint
rendezett Parqueten. Varhato, hogy a nyereseg a terulet novelesevel csokken:
egy nagy teruleten a sorcsoportok nagy resze amugy is tartalmaz talalatot,
igy keveset lehet atugrani. Ez a szkript ugyanazt a lekerdezest futtatja
egyre nagyobb, azonos kozeppontu teruleteken, a h3_tarolas.py altal irt
valtozatokon (ujraszamolas nelkul).

Hasznalat:
    python h3_teruletmeret.py
    python h3_teruletmeret.py --ismetles 7
"""

import argparse
import csv
import math
import statistics
import sys
import time
from pathlib import Path

import duckdb
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from utak import KIMENET

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except AttributeError:
    pass

ALAP_DIR = KIMENET / "h3_parquet"
TO = "aisdk-2026-07-15_teljes"
VALTOZATOK = ["alap", "h3_rendezett", "ido_rendezett"]

# Kozeppont: a Nagy-Balti-hid kornyeke (ugyanaz, mint a h3_tarolas.py-ban)
KOZEP_LAT, KOZEP_LON = 55.34, 11.00

# Fel-magassag fokban. A hosszusagi kiterjedes ennek 1/cos(lat)-szorosa, igy a
# teruletek km-ben kozelitoleg negyzetesek.
FEL_MAGASSAGOK = [0.01, 0.025, 0.05, 0.1, 0.2, 0.4, 0.8]

# A vizsgalt teljes terulet - a nagy negyzetek ide vagodnak
BBOX_LAT, BBOX_LON = (54.5, 56.5), (10.0, 13.0)

ISMETLES = 5
KM_PER_FOK = 111.32


def median_ms(con, sql, n):
    idok, r0 = [], None
    for _ in range(n):
        t0 = time.perf_counter()
        r = con.execute(sql).fetchall()
        idok.append(time.perf_counter() - t0)
        if r0 is None:
            r0 = r
    return statistics.median(idok) * 1000, r0


def olvasando_sorcsoport(con, fajl, lat, lon):
    """Hany sorcsoportot KELL beolvasni (a statisztika alapjan nem ugorhato)."""
    return con.execute(f"""
        WITH m AS (
          SELECT row_group_id, path_in_schema o,
                 TRY_CAST(stats_min AS DOUBLE) mn, TRY_CAST(stats_max AS DOUBLE) mx
          FROM parquet_metadata('{fajl}')
          WHERE path_in_schema IN ('Latitude','Longitude'))
        SELECT count(DISTINCT row_group_id) FILTER (WHERE row_group_id NOT IN (
                 SELECT row_group_id FROM m WHERE
                   (o='Latitude'  AND (mx < {lat[0]} OR mn > {lat[1]})) OR
                   (o='Longitude' AND (mx < {lon[0]} OR mn > {lon[1]})))),
               count(DISTINCT row_group_id)
        FROM m""").fetchone()


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dir", default=ALAP_DIR)
    ap.add_argument("--ismetles", type=int, default=ISMETLES)
    ap.add_argument("--csv", default=KIMENET / "h3_teruletmeret.csv")
    ap.add_argument("--abra", default=KIMENET / "h3_teruletmeret.png")
    args = ap.parse_args()

    fajlok = {v: (Path(args.dir) / f"{TO}_{v}.parquet").as_posix() for v in VALTOZATOK}
    for v, f in fajlok.items():
        if not Path(f).exists():
            sys.exit(f"Hianyzik: {f}\nFuttasd elobb: python scripts/h3_tarolas.py")

    con = duckdb.connect()
    osszes = con.execute(f"SELECT count(*) FROM '{fajlok['alap']}'").fetchone()[0]
    print(f"{osszes:,} sor, {len(FEL_MAGASSAGOK)} teruletmeret, "
          f"{args.ismetles} ismetles/meres\n")

    kozep_cos = math.cos(math.radians(KOZEP_LAT))
    sorok = []
    for h in FEL_MAGASSAGOK:
        w = h / kozep_cos
        lat = (max(KOZEP_LAT - h, BBOX_LAT[0]), min(KOZEP_LAT + h, BBOX_LAT[1]))
        lon = (max(KOZEP_LON - w, BBOX_LON[0]), min(KOZEP_LON + w, BBOX_LON[1]))
        km2 = ((lat[1] - lat[0]) * KM_PER_FOK) * ((lon[1] - lon[0]) * KM_PER_FOK * kozep_cos)
        felt = (f"Latitude BETWEEN {lat[0]} AND {lat[1]} "
                f"AND Longitude BETWEEN {lon[0]} AND {lon[1]}")
        sor = {"fel_magassag_fok": h, "terulet_km2": round(km2, 1)}
        ref = None
        for v, f in fajlok.items():
            ms, r = median_ms(con, f"SELECT count(DISTINCT MMSI), count(*) FROM '{f}' WHERE {felt}",
                              args.ismetles)
            if ref is None:
                ref = r
            elif r != ref:
                sys.exit(f"HIBA: {v} eredmenye elter ({r} vs {ref})")
            olv, ossz_rg = olvasando_sorcsoport(con, f, lat, lon)
            sor[f"{v}_ms"] = round(ms, 1)
            sor[f"{v}_olvasott_rg"] = olv
        sor["sorcsoport"] = ossz_rg
        sor["hajo"], sor["sor"] = ref[0]
        sor["sor_arany_szazalek"] = round(ref[0][1] / osszes * 100, 2)
        sor["h3_gyorsulas"] = round(sor["alap_ms"] / sor["h3_rendezett_ms"], 2)
        sorok.append(sor)
        print(f"  {km2:>8,.0f} km2  {sor['sor_arany_szazalek']:>6.2f}% sor  "
              f"olvasott sorcs. alap/h3/ido: {sor['alap_olvasott_rg']:>3}/"
              f"{sor['h3_rendezett_olvasott_rg']:>3}/{sor['ido_rendezett_olvasott_rg']:>3}  "
              f"ms alap/h3/ido: {sor['alap_ms']:>6}/{sor['h3_rendezett_ms']:>6}/"
              f"{sor['ido_rendezett_ms']:>6}  -> h3 {sor['h3_gyorsulas']}x")

    with Path(args.csv).open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(sorok[0].keys()))
        w.writeheader()
        w.writerows(sorok)
    print(f"\n-> {args.csv}")

    # --- Abra: a beolvasando sorcsoportok aranya a terulet fuggvenyeben ---
    x = [s["sor_arany_szazalek"] for s in sorok]
    fig, ax = plt.subplots(figsize=(7.5, 4.2))
    stilus = {"alap": ("#8a97a1", "eredeti (hajó, idő) sorrend"),
              "h3_rendezett": ("#2a78d6", "H3 szerint rendezve"),
              "ido_rendezett": ("#eb6834", "idő szerint rendezve")}
    for v, (szin, cimke) in stilus.items():
        y = [s[f"{v}_olvasott_rg"] / s["sorcsoport"] * 100 for s in sorok]
        ax.plot(x, y, marker="o", ms=5, lw=2, color=szin, label=cimke)
    ax.set_xscale("log")
    ax.set_xlabel("a lekérdezett terület sorainak aránya a napi adatban (%, log.)")
    ax.set_ylabel("beolvasandó sorcsoportok (%)")
    ax.set_ylim(0, 105)
    ax.grid(alpha=0.25)
    ax.legend(frameon=False, loc="center left")
    ax.set_title("Mennyi adatot kell beolvasni egy térbeli lekérdezéshez?", fontsize=11)
    fig.tight_layout()
    fig.savefig(args.abra, dpi=150)
    print(f"-> {args.abra}")


if __name__ == "__main__":
    main()
