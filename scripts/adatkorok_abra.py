"""
Az adatkorok idovonala (v10, 2.2 alfejezet): melyik napkeszlet melyik idoszakba esik,
hany nap, es melyik alfejezet hasznalja. A datumok a dolgozat 2.2 es 4.2 alfejezetebol
es a hormuz_kozos.py ABLAKOK-bol; a 123 nap kezdete (06-22) a monitor jelzesek.csv-bol
(az elso nap, amelyre a hetnaphoz illesztett alapszint letezik).

Hasznalat: python adatkorok_abra.py --ki abra.png
"""
import argparse
from datetime import date, timedelta

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

D = lambda s: date.fromisoformat(s)
ABLAKOK = [("A25", "2025-01-13", "2025-02-28"), ("B25", "2025-03-10", "2025-05-30"),
           ("A26", "2026-01-12", "2026-02-27"), ("B26", "2026-03-09", "2026-05-29")]
TINTA, MASOD, RACS = "#1f2328", "#59636e", "#d0d7de"
HORMUZ, MONITOR, SZURKE = "#c4620c", "#1f6feb", "#afb8c1"


def napok(k, v):
    k, v = D(k), D(v)
    return [k + timedelta(i) for i in range((v - k).days + 1)]


def sav(ax, y, k, v, szin, **kw):
    k, v = D(k), D(v) + timedelta(1)
    ax.barh(y, (v - k).days, left=k, height=0.56, color=szin, edgecolor="white", linewidth=1.2, **kw)


def panel(ax, sorok, xlim, cim, het=False):
    n = len(sorok)
    for j, (nev, napsz, hol, rajzol) in enumerate(sorok):
        y = n - 1 - j
        rajzol(ax, y)
        ax.text(-0.012, y + 0.08, nev, transform=ax.get_yaxis_transform(), ha="right", va="center",
                fontsize=8.6, color=TINTA, fontweight="bold")
        ax.text(-0.012, y - 0.26, napsz, transform=ax.get_yaxis_transform(), ha="right", va="center",
                fontsize=7.6, color=MASOD)
        ax.text(1.012, y, hol, transform=ax.get_yaxis_transform(), ha="left", va="center",
                fontsize=7.8, color=TINTA)
    ax.set_ylim(-0.6, n - 0.4)
    ax.set_xlim(D(xlim[0]), D(xlim[1]))
    ax.set_yticks([])
    for s in ("left", "right", "top"):
        ax.spines[s].set_visible(False)
    ax.spines["bottom"].set_color(RACS)
    ax.tick_params(axis="x", colors=MASOD, labelsize=7.6, length=3, color=RACS)
    ax.grid(axis="x", color=RACS, linewidth=0.6, alpha=0.7)
    ax.set_axisbelow(True)
    ax.text(-0.33, 1.08, cim, transform=ax.transAxes, ha="left", va="bottom", fontsize=9.2, color=TINTA, fontweight="bold")


def hormuz_fo(ax, y):
    for _, k, v in ABLAKOK:
        sav(ax, y, k, v, HORMUZ, alpha=0.16)
        for d in napok(k, v):
            if d.weekday() in (1, 3):
                ax.plot([d, d], [y - 0.26, y + 0.26], color=HORMUZ, linewidth=0.9)


def hormuz_teljes(ax, y):
    for nev, k, v in ABLAKOK:
        sav(ax, y, k, v, HORMUZ)
        ax.text(D(k) + (D(v) - D(k)) / 2, y, nev, ha="center", va="center", fontsize=7.4,
                color="white", fontweight="bold")


def kitoltes(ax, y):
    sav(ax, y, "2025-01-01", "2026-05-31", SZURKE, alpha=0.55)
    for _, k, v in ABLAKOK:
        sav(ax, y, k, v, "white")


def alapminta(ax, y):
    for d in ["2026-07-08", "2026-07-09", "2026-07-15", "2026-07-16", "2026-09-05"]:
        ax.plot([D(d)], [y], marker="o", markersize=5.5, color=MONITOR, markeredgecolor="white",
                markeredgewidth=0.8)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ki", required=True)
    args = ap.parse_args()

    felso = [
        ("Hormuz fő minta", "76 nap, kedd és csütörtök", "fő becslés (4.2–4.5)", hormuz_fo),
        ("Kiterjesztett minta", "258 nap, minden nap", "robusztusság (4.6)", hormuz_teljes),
        ("Kitöltő napok", "további 258 nap", "csak az idősor-ábra (4.1)", kitoltes),
    ]
    also = [
        ("Monitor-idősor", "144 nap", "zajszint, jelzés (3.5–3.7, 5.)",
         lambda ax, y: sav(ax, y, "2026-06-01", "2026-10-22", MONITOR)),
        ("– ebből alapszinttel", "123 nap", "mérőszámok, jelzés (3.5, 3.6)",
         lambda ax, y: sav(ax, y, "2026-06-22", "2026-10-22", MONITOR, alpha=0.6)),
        ("– tárolóablak (laptop)", "128 nap", "tárolás, kapuk (3.2, 3.5, 5.3)",
         lambda ax, y: sav(ax, y, "2026-06-01", "2026-10-06", MONITOR, alpha=0.4)),
        ("– első három hónap", "92 nap", "skálázás, futás (3.2, 3.3, 3.7)",
         lambda ax, y: sav(ax, y, "2026-06-01", "2026-08-31", MONITOR, alpha=0.25)),
        ("– öt tesztnap", "5 nap", "technikai mérések (3.2, 3.3, 3.5)", alapminta),
    ]
    fig, (a1, a2) = plt.subplots(2, 1, figsize=(16 / 2.54, 11.2 / 2.54),
                                 gridspec_kw={"height_ratios": [3, 5], "hspace": 0.62})
    fig.subplots_adjust(left=0.25, right=0.70, top=0.92, bottom=0.07)
    panel(a1, felso, ("2025-01-01", "2026-06-01"), "Hormuz-időszak (4. fejezet): 2025. január 1. – 2026. május 31.")
    a1.axvline(D("2026-02-28"), color=TINTA, linestyle=":", linewidth=0.9)
    a1.text(D("2026-02-28"), -0.58, " Hormuz-zár", fontsize=7.0, color=TINTA, va="bottom")
    a1.xaxis.set_major_locator(mdates.MonthLocator(bymonth=(1, 4, 7, 10)))
    a1.xaxis.set_major_formatter(mdates.DateFormatter("%Y.%m."))
    panel(a2, also, ("2026-05-25", "2026-10-29"), "Monitoridőszak (2., 3. és 5. fejezet): 2026. június 1. – október 22.")
    a2.xaxis.set_major_locator(mdates.MonthLocator())
    a2.xaxis.set_major_formatter(mdates.DateFormatter("%Y.%m."))
    fig.savefig(args.ki, dpi=300)
    print("->", args.ki)


if __name__ == "__main__":
    main()
