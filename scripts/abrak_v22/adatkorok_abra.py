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
import matplotlib.ticker

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
        ax.text(-0.03, y + 0.28, nev, transform=ax.get_yaxis_transform(), ha="right", va="center",
                fontsize=10.4, color=TINTA, fontweight="bold")
        ax.text(-0.03, y - 0.02, napsz, transform=ax.get_yaxis_transform(), ha="right", va="center",
                fontsize=10.4, color=MASOD)
        ax.text(-0.03, y - 0.32, hol, transform=ax.get_yaxis_transform(), ha="right", va="center",
                fontsize=10.4, color=TINTA, style="italic")
    ax.set_ylim(-0.6, n - 0.4)
    ax.set_xlim(D(xlim[0]), D(xlim[1]))
    ax.set_yticks([])
    for s_ in ("left", "right", "top"):
        ax.spines[s_].set_visible(False)
    ax.spines["bottom"].set_color(RACS)
    ax.tick_params(axis="x", colors=MASOD, labelsize=10.4, length=3, color=RACS)
    ax.grid(axis="x", color=RACS, linewidth=0.6, alpha=0.7)
    ax.set_axisbelow(True)
    ax.text(-0.77, 1.04, cim, transform=ax.transAxes, ha="left", va="bottom", fontsize=11, color=TINTA, fontweight="bold")


def hormuz_fo(ax, y):
    for _, k, v in ABLAKOK:
        sav(ax, y, k, v, HORMUZ, alpha=0.16)
        for d in napok(k, v):
            if d.weekday() in (1, 3):
                ax.plot([d, d], [y - 0.26, y + 0.26], color=HORMUZ, linewidth=0.9)


def hormuz_teljes(ax, y):
    for nev, k, v in ABLAKOK:
        sav(ax, y, k, v, HORMUZ)
        ax.text(D(k) + (D(v) - D(k)) / 2, y + 0.30, nev, ha="center", va="bottom", fontsize=10.4,
                color=HORMUZ, fontweight="bold")


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
        ("Hormuz fő minta", "76 nap, kedd és csütörtök", "fő becslés (4.2.2–4.2.5)", hormuz_fo),
        ("Kiterjesztett minta", "258 nap, minden nap", "robusztusság (4.2.6)", hormuz_teljes),
        ("Kitöltő napok", "további 258 nap", "idősor-ábra (4.2.1)", kitoltes),
    ]
    also = [
        ("Monitor-idősor", "144 nap", "tároló, jelzés, kapuk (4.1, 4.3)",
         lambda ax, y: sav(ax, y, "2026-06-01", "2026-10-22", MONITOR)),
        ("– ebből alapszinttel", "123 nap", "mérőszámok, jelzés (4.1.5, 4.1.6)",
         lambda ax, y: sav(ax, y, "2026-06-22", "2026-10-22", MONITOR, alpha=0.6)),
        ("– első három hónap", "92 nap", "skálázás (4.1.2, 4.1.3, 4.1.7)",
         lambda ax, y: sav(ax, y, "2026-06-01", "2026-08-31", MONITOR, alpha=0.25)),
        ("– öt tesztnap", "5 nap", "mérések (4.1.2, 4.1.3, 4.1.5)", alapminta),
    ]
    fig, (a1, a2) = plt.subplots(2, 1, figsize=(6.0, 6.9),
                                 gridspec_kw={"height_ratios": [3, 4], "hspace": 0.55})
    fig.subplots_adjust(left=0.43, right=0.97, top=0.90, bottom=0.05)
    panel(a1, felso, ("2025-01-01", "2026-06-01"), "Hormuz-időszak (4.2 alfejezet):\n2025. január 1. – 2026. május 31.")
    a1.axvline(D("2026-02-28"), color=TINTA, linestyle=":", linewidth=0.9)
    a1.text(D("2026-02-28"), -0.58, " zár", fontsize=10.4, color=TINTA, va="bottom")
    a1.xaxis.set_major_locator(mdates.MonthLocator(bymonth=(1, 7)))
    a1.xaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda x, p: (lambda d: f"{d.year}. {'jan.' if d.month == 1 else 'júl.'}")(mdates.num2date(x))))
    panel(a2, also, ("2026-05-25", "2026-10-29"), "Monitoridőszak (3. fejezet, 4.1 és 4.3):\n2026. június 1. – október 22.")
    a2.xaxis.set_major_locator(mdates.MonthLocator())
    a2.xaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda x, p: ["jan.", "febr.", "márc.", "ápr.", "máj.", "jún.", "júl.", "aug.", "szept.", "okt.", "nov.", "dec."][mdates.num2date(x).month - 1]))
    fig.savefig(args.ki, dpi=300)
    print("->", args.ki)


if __name__ == "__main__":
    main()
