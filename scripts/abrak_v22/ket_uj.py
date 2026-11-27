"""A 3. es a 6. abra ujrarajzolasa legalabb 10 pontos feliratokkal (6,0 huvelykes megjelenitesre)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import uj_abrak_v9 as u
from abrak_v7 import plt, TINTA, MASOD
FS = 10.4
def parquet_felepites(ki):
    from matplotlib.patches import FancyBboxPatch
    fig = plt.figure(figsize=(6.0, 5.4)); ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, 60); ax.set_ylim(0, 54); ax.axis("off")
    ax.add_patch(FancyBboxPatch((1, 15), 58, 38, boxstyle="round,pad=0.2,rounding_size=0.8", fc="#f7f9fc", ec="#1f4e79", lw=1.0))
    ax.text(2.5, 51, "Parquet-fájl (egy nap)", fontsize=FS + 1, color="#1f4e79", fontweight="bold", va="center")
    oszl = ["MMSI", "idő", "szél.", "hossz.", "…"]
    for g, y0 in enumerate([39.8, 28.8]):
        ax.text(3, y0 + 8.4, f"{g + 1}. sorcsoport (row group, 100 000 sor)", fontsize=FS, color=MASOD, va="center")
        for j, o in enumerate(oszl):
            x = 3 + j * 11.0
            ax.add_patch(FancyBboxPatch((x, y0), 9.8, 7, boxstyle="round,pad=0.2,rounding_size=0.5", fc="#dbe7f5", ec="#1f4e79", lw=0.8))
            ax.text(x + 4.9, y0 + 5.4, o, ha="center", va="center", fontsize=FS, color=TINTA, fontweight="bold")
            for k in range(3):
                ax.add_patch(plt.Rectangle((x + 1.0, y0 + 0.8 + k * 1.2), 7.8, 0.9, fc="#2a78d6", alpha=0.35 + 0.15 * k, ec="none"))
    ax.text(28, 25.6, "⋮", ha="center", va="center", fontsize=14, color=MASOD)
    ax.add_patch(FancyBboxPatch((3, 16.6), 54, 6.4, boxstyle="round,pad=0.2,rounding_size=0.5", fc="#fde9e8", ec="#e34948", lw=0.8))
    ax.text(30, 19.8, "lábléc (metaadat): az oszlopdarabok helye\nés sorcsoportonként a min–max érték", ha="center", va="center", fontsize=FS, color=TINTA)
    ax.text(1.5, 12.6, "Hogyan olvassa a lekérdező motor?", fontsize=FS + 0.6, color="#1f4e79", fontweight="bold", va="center")
    sorok = [("oszlopdarab (column chunk):", "egy oszlop egy sorcsoporton belül; csak a szükséges oszlopot kell beolvasni"),
             ("lap (page):", "a tömörítés és a kódolás egysége (a kis kék sávok)"),
             ("min–max a láblécben:", "ha a keresett érték nem eshet a sorcsoportba, az egész kihagyható")]
    y = 9.6
    for cim, sz in sorok:
        ax.text(1.5, y, cim, fontsize=FS, color=TINTA, fontweight="bold", va="center")
        ax.text(1.5, y - 1.75, sz, fontsize=FS, color=MASOD, va="center")
        y -= 3.7
    fig.savefig(ki / "parquet_felepites.png", dpi=300, bbox_inches="tight", pad_inches=0.05)
    plt.close(fig)
def tarolas_meret(ki):
    adat = [("kicsomagolt CSV", 6248.0), ("DuckDB natív tábla", 1537.3),
            ("Parquet, Snappy, 26 oszlop,\nismétlődő sorokkal", 1061.2), ("letöltött ZIP", 955.7),
            ("Parquet-tároló (Zstandard,\ndeduplikált, 19 oszlop)", 226.8),
            ("holtszámításos réteg,\n50 m (6 oszlop)", 30.7)]
    nevek = [a for a, _ in adat][::-1]; ert = [b for _, b in adat][::-1]
    fig, ax = plt.subplots(figsize=(6.0, 3.9))
    szin = [("#1f4e79" if "tároló" in n else ("#2a78d6" if "holtsz" in n else "#9ab8dc")) for n in nevek]
    ax.barh(nevek, ert, color=szin, height=0.62)
    for i, v in enumerate(ert):
        ax.text(v + 90, i, f"{v:,.1f} MiB".replace(",", " ").replace(".", ","), va="center", fontsize=FS, color=TINTA, bbox=dict(fc="white", ec="none", pad=0.6))
    ax.axvline(955.7, color="#e34948", lw=0.8, ls=(0, (3, 2)))
    ax.text(1050, 5.5, "letöltött ZIP", fontsize=FS, color="#e34948", va="center")
    ax.set_xlim(0, 8200); ax.set_ylim(-0.6, 5.9)
    ax.set_xticks([0, 2000, 4000, 6000, 8000]); ax.set_xticklabels(["0", "2 000", "4 000", "6 000", "8 000"])
    ax.set_xlabel("méret, MiB (1 GiB = 1024 MiB)", fontsize=FS)
    ax.tick_params(labelsize=FS)
    for s in ("top", "right"): ax.spines[s].set_visible(False)
    fig.tight_layout()
    fig.savefig(ki / "tarolas_meret.png", dpi=300, bbox_inches="tight")
    plt.close(fig)
if __name__ == "__main__":
    ki = Path(sys.argv[1]); parquet_felepites(ki); tarolas_meret(ki)
