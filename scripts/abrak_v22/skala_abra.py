import csv, sys
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter, LogLocator
FS = 10.4
sorok = []
for r in csv.DictReader(open(sys.argv[1], encoding="utf-8")):
    for k in ("nyers_sor", "negy_egyutt_mp", "inditas_mp"):
        r[k] = float(r[k]) if r.get(k) not in (None, "") else None
    sorok.append(r)
nevek = {"duckdb_parquet": "DuckDB + Parquet", "polars_parquet": "Polars + Parquet",
         "spark_parquet": "Spark (helyi mód) + Parquet", "duckdb_csv": "DuckDB + nyers CSV",
         "pandas_csv": "pandas + nyers CSV"}
fig, ax = plt.subplots(figsize=(6.0, 5.6))
for motor, nev in nevek.items():
    r = [s for s in sorok if s["motor"] == motor and s.get("negy_egyutt_mp")]
    if not r: continue
    x = [s["nyers_sor"] / 1e6 for s in r]; y = [s["negy_egyutt_mp"] for s in r]
    ax.plot(x, y, marker="o", label=nev)
    if motor == "spark_parquet":
        ax.plot(x, [s["negy_egyutt_mp"] + s["inditas_mp"] for s in r], marker="x", linestyle=":",
                color=ax.lines[-1].get_color(), label=nev + ",\nmunkamenet-indulással")
ax.set_xscale("log"); ax.set_yscale("log")
hu = FuncFormatter(lambda v, p: (f"{v:g}".replace(".", ",")))
ax.xaxis.set_major_formatter(hu); ax.yaxis.set_major_formatter(hu)
ax.set_xlabel("adatméret (millió nyers AIS-sor, log)", fontsize=FS)
ax.set_ylabel("4 lekérdezés ideje, medián (mp, log)", fontsize=FS)
ax.tick_params(labelsize=FS)
ax.grid(True, which="both", alpha=0.3)
ax.legend(fontsize=FS, loc="upper center", bbox_to_anchor=(0.45, -0.16), ncol=2, frameon=False)
fig.tight_layout()
fig.savefig(sys.argv[2], dpi=300)
