"""
Abra a trajektoria-tomorites tradeoff-gorbejerol.

A `trajektoria_tomorites.py` altal kiirt CSV-bol dolgozik, igy az abra
ujrageneralasahoz nem kell ujra lefuttatni a merest.

Hasznalat:
    python abra_tomorites.py
    python abra_tomorites.py --be trajektoria_tomorites.csv --ki tomorites_tradeoff.png
"""

import argparse

import pandas as pd
import matplotlib.pyplot as plt

from utak import KIMENET

# Szinek: egyetlen adatsor, ezert egyetlen hue (kek) + visszafogott kromja.
SZIN_ADAT = "#2a78d6"
SZIN_REFERENCIA = "#898781"
TINTA_ELSO = "#0b0b0b"
TINTA_MASODIK = "#52514e"
TINTA_HALVANY = "#898781"
RACS = "#e1e0d9"
HATTER = "#fcfcfb"


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--be", default=KIMENET / "trajektoria_tomorites.csv")
    ap.add_argument("--ki", default=KIMENET / "tomorites_tradeoff.png")
    args = ap.parse_args()

    df = pd.read_csv(args.be).sort_values("kuszob_m")
    nap = df["nap"].iloc[0]
    teljes_mb = float(df["teljes_parquet_mb"].iloc[0])

    fig, ax = plt.subplots(figsize=(9, 5.6))
    fig.patch.set_facecolor(HATTER)
    ax.set_facecolor(HATTER)

    # Referenciavonal: tomorites nelkuli meret
    ax.axhline(teljes_mb, color=SZIN_REFERENCIA, linestyle="--", linewidth=1.5,
               zorder=1)
    ax.text(11, teljes_mb * 1.03,
            f"trajektória-tömörítés nélkül: {teljes_mb:.1f} MB",
            color=TINTA_MASODIK, fontsize=10, va="bottom")

    ax.plot(df["kuszob_m"], df["tomoritett_parquet_mb"],
            color=SZIN_ADAT, linewidth=2.0, marker="o", markersize=8,
            markeredgecolor=HATTER, markeredgewidth=1.5, zorder=3)

    # Pontonkenti cimke (6 pont, mindegyik elfer)
    eltolas = {10: (0, 14), 25: (0, -20), 50: (0, 12), 100: (0, -20),
               250: (0, 12), 500: (0, -20)}
    for _, s in df.iterrows():
        dx, dy = eltolas.get(int(s["kuszob_m"]), (0, 12))
        ax.annotate(f"{s['tomoritett_parquet_mb']:.1f} MB",
                    xy=(s["kuszob_m"], s["tomoritett_parquet_mb"]),
                    xytext=(dx, dy), textcoords="offset points",
                    ha="center", fontsize=10, color=TINTA_ELSO)

    ax.set_xscale("log")
    ax.set_xticks(df["kuszob_m"])
    ax.set_xticklabels([f"{int(k)}" for k in df["kuszob_m"]])
    ax.set_ylim(0, teljes_mb * 1.18)

    ax.set_xlabel("Garantált maximális pozícióhiba (méter, logaritmikus skála)",
                  color=TINTA_MASODIK, fontsize=11)
    ax.set_ylabel("Tárolt méret (MB, Parquet + zstd)",
                  color=TINTA_MASODIK, fontsize=11)
    pontok = f"{int(df['osszes_pont'].iloc[0]):,}".replace(",", " ")
    ax.set_title(
        "Trajektória-tömörítés: mennyi helyet spórol, mennyi pontosságért cserébe\n"
        f"AIS, dán szorosok, {nap[6:]} – {pontok} pozíció, dead reckoning",
        color=TINTA_ELSO, fontsize=12.5, pad=14, loc="left")

    ax.grid(True, color=RACS, linewidth=0.8, zorder=0)
    ax.set_axisbelow(True)
    for oldal in ("top", "right"):
        ax.spines[oldal].set_visible(False)
    for oldal in ("left", "bottom"):
        ax.spines[oldal].set_color("#c3c2b7")
    ax.tick_params(colors=TINTA_HALVANY, labelsize=10)

    fig.tight_layout()
    fig.savefig(args.ki, dpi=150, facecolor=HATTER, bbox_inches="tight")
    print(f"-> {args.ki} kiirva")


if __name__ == "__main__":
    main()
