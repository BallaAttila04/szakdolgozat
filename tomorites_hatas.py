"""
A trajektoria-tomorites hatasa: (1) valtozik-e az elemzes EREDMENYE,
(2) mennyivel gyorsul a LEKERDEZES.

Kontextus (ld. naplo.md, 2026-09-19 21:07): a dead reckoning 6,4x kisebb
fajlt ad 50 m-es hibakorlattal. De a tarhelynyereseg ertektelen, ha kozben
az elemzes rossz eredmenyt ad. Ez a szkript a tomoritetlen Parquetet veszi
alapnak, es minden tomoritett valtozatra osszeveti vele az oranankenti
egyedi hajoszamot - azt a metrikat, amire a forgalmi kiertekeles epul.

VARHATO KOCKAZAT: a dead reckoning hajonkent dobja el a pontokat. Ha egy
hajo rovid ideig van jelen egy oraban es kozben egyenesen halad, elofordulhat,
hogy abban az oraban EGYETLEN pontja sem marad meg - ilyenkor a tomoritett
adat alulszamolja az adott ora hajoszamat. A MAX_IDORES_MP = 600 mp-es
kotelezo horgony ezt korlatozza (oranként ~6 horgony egy folyamatosan jelen
levo hajonal), de a rovid atmeno hajoknal nem zarja ki. Ezert kell merni,
nem feltetelezni.

Az idomeres ISMETELVE fut (alapertelmezetten 5x), es a medianot jelenti,
mert a korabbi tarolasi benchmark egyetlen futasanal ~2x szorast lattunk
a fajl-cache allapota miatt.

Hasznalat:
    python tomorites_hatas.py --alap tomorites_out/aisdk-2026-07-15_teljes.parquet \
        --tomoritett tomorites_out/aisdk-2026-07-15_dr*.parquet
"""

import argparse
import re
import statistics
import time
from pathlib import Path

import duckdb
import pandas as pd

# Az a lekerdezes, amire a forgalmi kiertekeles epul: oranankenti egyedi
# hajoszam es uzenetszam.
LEKERDEZES = """
    SELECT date_part('hour', ts) AS ora,
           COUNT(DISTINCT MMSI) AS hajo,
           COUNT(*) AS uzenet
    FROM read_parquet('{path}')
    GROUP BY 1 ORDER BY 1
"""

ISMETLES = 5

KUSZOB_RE = re.compile(r"_dr(\d+)m\.parquet$")


def merj(con, path: Path, ismetles: int):
    """Lefuttatja a lekerdezest `ismetles`-szer, visszaadja az eredmenyt es
    a futasido medianjat. Az elso futas (hideg cache) kulon is megjelenik."""
    idok = []
    df = None
    for _ in range(ismetles):
        t0 = time.perf_counter()
        df = con.execute(LEKERDEZES.format(path=path.as_posix())).df()
        idok.append(time.perf_counter() - t0)
    return df, idok


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--alap", required=True,
                    help="A tomoritetlen Parquet (viszonyitasi alap)")
    ap.add_argument("--tomoritett", nargs="+", required=True,
                    help="A tomoritett Parquet fajlok")
    ap.add_argument("--ismetles", type=int, default=ISMETLES)
    ap.add_argument("--ki", default="tomorites_hatas.csv")
    args = ap.parse_args()

    con = duckdb.connect()
    alap_path = Path(args.alap)

    print(f"=== Alap (tomoritetlen): {alap_path.name} ===")
    alap_df, alap_idok = merj(con, alap_path, args.ismetles)
    alap_med = statistics.median(alap_idok)
    alap_mb = alap_path.stat().st_size / 1_048_576
    alap_hajo = alap_df["hajo"].to_numpy()
    print(f"  {alap_mb:,.1f} MB, lekerdezes mediana {alap_med*1000:,.0f} ms "
          f"(elso futas {alap_idok[0]*1000:,.0f} ms, {args.ismetles} ismetles)")
    print(f"  napi osszes uzenet: {int(alap_df['uzenet'].sum()):,}")

    sorok = [{
        "fajl": alap_path.name, "kuszob_m": 0, "meret_mb": round(alap_mb, 1),
        "lekerdezes_median_ms": round(alap_med * 1000, 1),
        "lekerdezes_elso_ms": round(alap_idok[0] * 1000, 1),
        "gyorsulas": 1.0,
        "max_hajo_elteres": 0, "atlag_hajo_elteres": 0.0,
        "max_relativ_elteres_szazalek": 0.0,
    }]

    for t_str in sorted(args.tomoritett):
        t_path = Path(t_str)
        if not t_path.exists():
            print(f"  FIGYELEM: nem letezik, kihagyva: {t_path}")
            continue

        m = KUSZOB_RE.search(t_path.name)
        kuszob = int(m.group(1)) if m else -1

        df, idok = merj(con, t_path, args.ismetles)
        med = statistics.median(idok)
        mb = t_path.stat().st_size / 1_048_576
        hajo = df["hajo"].to_numpy()

        if len(hajo) != len(alap_hajo):
            print(f"  FIGYELEM: {t_path.name}: elteroszamu ora "
                  f"({len(hajo)} vs {len(alap_hajo)})")
            continue

        elteres = alap_hajo - hajo          # pozitiv = a tomoritett alulszamol
        rel = elteres / alap_hajo * 100.0
        max_el = int(abs(elteres).max())
        atlag_el = float(abs(elteres).mean())
        max_rel = float(abs(rel).max())

        print(f"\n  kuszob {kuszob:>3} m: {mb:,.1f} MB, "
              f"median {med*1000:,.0f} ms ({alap_med/med:.1f}x gyorsabb)")
        print(f"    oranankenti hajoszam elterese az alaptol: "
              f"max {max_el} hajo, atlag {atlag_el:.1f} hajo, "
              f"max relativ {max_rel:.2f}%")

        sorok.append({
            "fajl": t_path.name, "kuszob_m": kuszob, "meret_mb": round(mb, 1),
            "lekerdezes_median_ms": round(med * 1000, 1),
            "lekerdezes_elso_ms": round(idok[0] * 1000, 1),
            "gyorsulas": round(alap_med / med, 2),
            "max_hajo_elteres": max_el,
            "atlag_hajo_elteres": round(atlag_el, 2),
            "max_relativ_elteres_szazalek": round(max_rel, 3),
        })

    eredmeny = pd.DataFrame(sorok)
    eredmeny.to_csv(args.ki, index=False)
    print(f"\n-> {args.ki} kiirva")
    print("\n" + eredmeny.to_string(index=False))


if __name__ == "__main__":
    main()
