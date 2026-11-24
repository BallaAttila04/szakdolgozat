"""
A v9-es dolgozatba kerulo uj abrak (Ati 2026-11-24-i jegyzetei alapjan).

Bemenet: a 2026-07-15-i napi DMA-fajl Parquet-kivonata (nap.parquet: ts, tom, mmsi, lat, lon,
st, nev, dr, dest; a teljes, 36 650 571 soros fajlbol), a Natural Earth 10m szarazfold
(ne_10m_land.geojson) es a kapuk.json.

Kimenet (--ki):
  vetel_lefedettseg.png   bazisallomasok es a pozicioval lefedett terulet (H3, 5-os szint)
  h3_ket_szint.png        a H3 hierarchia ket szintje a dan szorosoknal (5-os es 6-os)
  parquet_felepites.png   a Parquet-fajl szerkezete (sematikus)
  tarolas_meret.png       ugyanaz a nap kulonbozo tarolasi formakban (4. tablazat ertekei)
  h3_racs.png             a regi 3. abra 20%-kal nagyobb kivagassal
  minta_sor.csv           egy valodi sor mind a 26 mezovel (a tablazathoz)
"""
import argparse
import json
import sys
from pathlib import Path

import duckdb
import h3
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import abrak_v7 as a7  # noqa: E402
from abrak_v7 import plt, PolyCollection, LogNorm, Line2D, SZARAZ, PART, TINTA, MASOD, DOBOZ  # noqa: E402

KEK = "#2a78d6"


def poli(c):
    return np.array(h3.cell_to_boundary(c))[:, ::-1]


def vetel_lefedettseg(con, nap, land, ki):
    kit = (3.0, 17.5, 53.0, 59.5)
    df = con.sql(f"""
        SELECT lat, lon, mmsi FROM '{nap}'
        WHERE tom IN ('Class A', 'Class B') AND lat BETWEEN {kit[2]} AND {kit[3]}
          AND lon BETWEEN {kit[0]} AND {kit[1]}
        GROUP BY ALL""").df()
    df["c"] = [h3.latlng_to_cell(la, lo, 5) for la, lo in zip(df.lat, df.lon)]
    agg = df.groupby("c").mmsi.nunique()
    bs = con.sql(f"""
        SELECT mmsi, median(lat) lat, median(lon) lon, count(*) n FROM '{nap}'
        WHERE tom = 'Base Station' AND lat BETWEEN -90 AND 90 AND lon BETWEEN -180 AND 180
        GROUP BY mmsi""").df()
    bs_ki = bs[(bs.lat.between(kit[2], kit[3])) & (bs.lon.between(kit[0], kit[1]))]
    fig, ax = plt.subplots(figsize=(6.3, 5.6))
    a7.szarazfold(ax, land, kit)
    pc = PolyCollection([poli(c) for c in agg.index], array=agg.to_numpy(), cmap="Blues",
                        norm=LogNorm(1, agg.max()), edgecolor="none", alpha=0.9, zorder=2)
    ax.add_collection(pc)
    ax.scatter(bs_ki.lon, bs_ki.lat, marker="^", s=16, color="#e34948", edgecolor="white",
               linewidth=0.4, zorder=5)
    ax.add_patch(plt.Rectangle((10.0, 54.5), 3.0, 2.0, fill=False, ls=(0, (4, 3)), lw=1.0,
                               ec=TINTA, zorder=6))
    ax.text(10.05, 56.55, "vizsgálati terület", fontsize=7, color=TINTA, zorder=7, bbox=DOBOZ)
    a7.keret(ax, kit, 2.0, 1.0)
    cb = fig.colorbar(pc, ax=ax, shrink=0.75, pad=0.02)
    cb.set_label("különböző hajók a cellában (H3, 5-ös szint)", fontsize=7.5)
    cb.ax.tick_params(labelsize=7)
    ax.legend(handles=[Line2D([], [], marker="^", ls="none", color="#e34948", markersize=5,
                              label=f"AIS-bázisállomás ({len(bs_ki)} db)")],
              loc="upper right", fontsize=7, framealpha=0.92, edgecolor="#cccccc")
    fig.tight_layout()
    fig.savefig(ki / "vetel_lefedettseg.png", dpi=300, bbox_inches="tight")
    plt.close(fig)
    return {"cella": len(agg), "hajo_osszes": int(df.mmsi.nunique()), "bazis_osszes": len(bs),
            "bazis_kivagasban": len(bs_ki)}


def h3_ket_szint(land, ki):
    kit = (9.6, 13.4, 54.4, 56.6)
    kozep = (55.40, 10.98)          # a Nagy-Balti-ov kapu kozepe
    durva = h3.latlng_to_cell(*kozep, 5)
    # a kivagast lefedo 5-os cellak
    poly = h3.LatLngPoly([(kit[2], kit[0]), (kit[2], kit[1]), (kit[3], kit[1]), (kit[3], kit[0])])
    c5 = set(h3.polygon_to_cells(poly, 5))
    c5 |= {n for c in list(c5) for n in h3.grid_disk(c, 1)}
    gyerek = h3.cell_to_children(durva, 6)
    fig, ax = plt.subplots(figsize=(6.3, 4.9))
    a7.szarazfold(ax, land, kit)
    ax.add_collection(PolyCollection([poli(c) for c in c5], facecolor="none", edgecolor="#6b8fb8",
                                     linewidth=0.6, zorder=3))
    ax.add_collection(PolyCollection([poli(c) for c in gyerek], facecolor="#2a78d6", alpha=0.25,
                                     edgecolor="#1f4e79", linewidth=0.5, zorder=4))
    ax.add_collection(PolyCollection([poli(durva)], facecolor="none", edgecolor="#e34948",
                                     linewidth=1.6, zorder=5))
    ax.plot([10.60, 11.35], [55.40, 55.40], color="#111", lw=1.4, zorder=6)
    ax.text(11.38, 55.40, "Nagy-Balti-öv kapu", fontsize=7, va="center", color=TINTA, zorder=7,
            bbox=DOBOZ)
    a7.keret(ax, kit, 1.0, 0.5)
    ter5 = h3.average_hexagon_area(5, "km^2")
    ter6 = h3.average_hexagon_area(6, "km^2")
    ax.legend(handles=[
        Line2D([], [], color="#6b8fb8", lw=0.8, label=f"5-ös szintű cellák (átlag {ter5:.0f} km²)".replace(".", ",")),
        Line2D([], [], color="#e34948", lw=1.6, label="egy 5-ös cella"),
        plt.Rectangle((0, 0), 1, 1, fc="#2a78d6", alpha=0.25, ec="#1f4e79",
                      label=f"ennek 6-os szintű gyermekei ({len(gyerek)} db, átlag {ter6:.0f} km²)".replace(".", ","))],
        loc="lower left", fontsize=7, framealpha=0.95, edgecolor="#cccccc")
    fig.tight_layout()
    fig.savefig(ki / "h3_ket_szint.png", dpi=300, bbox_inches="tight")
    plt.close(fig)
    return {"gyerek": len(gyerek), "ter5": round(ter5, 1), "ter6": round(ter6, 1)}


def parquet_felepites(ki):
    from matplotlib.patches import FancyBboxPatch
    fig, ax = plt.subplots(figsize=(6.3, 3.6))
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 60)
    ax.axis("off")

    def doboz(x, y, w, h, szoveg, fc, ec="#1f4e79", fs=7.5, bold=False, szin=TINTA):
        ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.3,rounding_size=0.8",
                                    fc=fc, ec=ec, lw=0.8))
        ax.text(x + w / 2, y + h / 2, szoveg, ha="center", va="center", fontsize=fs, color=szin,
                fontweight="bold" if bold else "normal")

    ax.add_patch(FancyBboxPatch((1, 1), 62, 57, boxstyle="round,pad=0.3,rounding_size=1",
                                fc="#f7f9fc", ec="#1f4e79", lw=1.0))
    ax.text(3, 55.5, "Parquet-fájl (egy nap)", fontsize=8.5, color="#1f4e79", fontweight="bold",
            va="center")
    oszl = ["MMSI", "idő", "szél.", "hossz.", "…"]
    for g, y0 in enumerate([37, 20]):
        ax.text(3, y0 + 14.5, f"{g + 1}. sorcsoport (row group, 100 000 sor)", fontsize=7.3,
                color=MASOD, va="center")
        for j, o in enumerate(oszl):
            x = 3 + j * 11.8
            doboz(x, y0, 10.5, 12, "", "#dbe7f5", fs=7)
            ax.text(x + 5.25, y0 + 9.6, o, ha="center", fontsize=7, color=TINTA, fontweight="bold")
            for k in range(3):
                ax.add_patch(plt.Rectangle((x + 1.2, y0 + 1.3 + k * 2.6), 8.1, 2.0, fc="#2a78d6",
                                           alpha=0.35 + 0.15 * k, ec="none"))
    ax.text(32, 16.5, "⋮", ha="center", fontsize=12, color=MASOD)
    doboz(3, 3, 59, 8, "lábléc (metaadat): az oszlopdarabok helye\nés sorcsoportonként a min–max érték",
          "#fde9e8", ec="#e34948", fs=7.0)
    # magyarazatok jobb oldalt
    mx = 67
    ax.text(mx, 52, "Hogyan olvassa a lekérdező motor?", fontsize=8, color="#1f4e79", fontweight="bold")
    sorok = [("oszlopdarab (column chunk)", "egy oszlop egy sorcsoporton belül; csak a szükséges\noszlopokat kell beolvasni"),
             ("lap (page)", "a tömörítés és kódolás egysége\n(a kis kék sávok)"),
             ("min–max a láblécben", "ha a keresett érték nem eshet egy sorcsoportba,\naz egész sorcsoport kihagyható")]
    y = 45
    for cim, szoveg in sorok:
        ax.text(mx, y, cim, fontsize=7.3, color=TINTA, fontweight="bold")
        ax.text(mx, y - 1.5, szoveg, fontsize=6.8, color=MASOD, va="top")
        y -= 13.5
    fig.savefig(ki / "parquet_felepites.png", dpi=300, bbox_inches="tight")
    plt.close(fig)


def tarolas_meret(ki):
    # a 4. tablazat (most 5.) 1 napos oszlopa, MiB (pipeline.py, tarolas_benchmark.py meresei)
    adat = [("kicsomagolt CSV", 6248.0), ("DuckDB natív tábla", 1537.3),
            ("Parquet, Snappy, 26 oszlop, ismétlődő sorokkal", 1061.2), ("letöltött ZIP", 955.7),
            ("Parquet-tároló (Zstandard, deduplikált, 19 oszlop)", 226.8),
            ("dead reckoning réteg, 50 m (6 oszlop)", 30.7)]
    nevek = [a for a, _ in adat][::-1]
    ert = [b for _, b in adat][::-1]
    fig, ax = plt.subplots(figsize=(6.3, 2.9))
    szin = ["#9ab8dc" if "tároló" not in n and "reckoning" not in n else KEK for n in nevek]
    szin = [("#1f4e79" if "tároló" in n else c) for n, c in zip(nevek, szin)]
    ax.barh(nevek, ert, color=szin, height=0.6)
    for i, v in enumerate(ert):
        ax.text(v + 60, i, f"{v:,.1f} MiB".replace(",", " ").replace(".", ","), va="center",
                fontsize=7.2, color=TINTA)
    ax.axvline(955.7, color="#e34948", lw=0.8, ls=(0, (3, 2)))
    ax.text(985, 5.45, "letöltött ZIP", fontsize=6.8, color="#e34948", va="center")
    ax.set_xlim(0, 7300)
    ax.set_xlabel("méret, MiB (1 GiB = 1024 MiB)", fontsize=7.5)
    ax.tick_params(labelsize=7.2)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    fig.tight_layout()
    fig.savefig(ki / "tarolas_meret.png", dpi=300, bbox_inches="tight")
    plt.close(fig)


def h3_racs_nagyobb(con, nap, kapuk, land, ki):
    regi = (10.78, 11.30, 55.22, 55.47)
    cx, cy = (regi[0] + regi[1]) / 2, (regi[2] + regi[3]) / 2
    hw, hh = (regi[1] - regi[0]) / 2 * 1.2, (regi[3] - regi[2]) / 2 * 1.2
    kit = (round(cx - hw, 3), round(cx + hw, 3), round(cy - hh, 3), round(cy + hh, 3))
    df = con.sql(f"""
        SELECT DISTINCT mmsi AS MMSI, lat AS Latitude, lon AS Longitude FROM '{nap}'
        WHERE lat BETWEEN {kit[2] - 0.03} AND {kit[3] + 0.03}
          AND lon BETWEEN {kit[0] - 0.04} AND {kit[1] + 0.04}""").df()
    df["h3"] = [h3.str_to_int(h3.latlng_to_cell(la, lo, 8)) for la, lo in zip(df.Latitude, df.Longitude)]
    df["dup_db"] = 1
    kis = ki / "_h3_kivonat.parquet"
    df.to_parquet(kis)
    r = a7.h3_racs(con, kis, kapuk, land, ki, kit=kit)
    r["kit"] = kit
    return r


def minta_sor(csv_ut, ki):
    con = duckdb.connect()
    sor = con.sql(f"""
        SELECT * FROM read_csv('{csv_ut}', header=true, all_varchar=true)
        WHERE "Type of mobile" = 'Class A' AND "Ship type" = 'Tanker'
          AND TRY_CAST(Latitude AS DOUBLE) BETWEEN 55.30 AND 55.50
          AND TRY_CAST(Longitude AS DOUBLE) BETWEEN 10.85 AND 11.10
          AND "Navigational status" = 'Under way using engine' AND Draught IS NOT NULL
          AND Destination IS NOT NULL AND Destination <> 'Unknown' AND ETA IS NOT NULL
          AND Name IS NOT NULL AND IMO <> 'Unknown' AND ROT IS NOT NULL AND Heading IS NOT NULL
          AND A IS NOT NULL
        LIMIT 1""").df()
    sor.T.to_csv(ki / "minta_sor.csv", header=["ertek"], index_label="mezo", encoding="utf-8")
    return sor.T


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--nap", type=Path, required=True)
    ap.add_argument("--csv", type=Path, required=True)
    ap.add_argument("--land", type=Path, required=True)
    ap.add_argument("--kapuk", type=Path, required=True)
    ap.add_argument("--ki", type=Path, required=True)
    a = ap.parse_args()
    a.ki.mkdir(parents=True, exist_ok=True)
    land = json.loads(a.land.read_text(encoding="utf-8"))
    kapuk = json.loads(a.kapuk.read_text(encoding="utf-8"))
    kapuk = kapuk["kapuk"] if isinstance(kapuk, dict) else kapuk
    con = duckdb.connect()
    print("vetel", vetel_lefedettseg(con, a.nap, land, a.ki))
    print("h3 ket szint", h3_ket_szint(land, a.ki))
    parquet_felepites(a.ki)
    tarolas_meret(a.ki)
    print("h3 racs", h3_racs_nagyobb(con, a.nap, kapuk, land, a.ki))
    print(minta_sor(a.csv, a.ki).to_string())
