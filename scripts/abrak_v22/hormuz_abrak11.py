import sys
from pathlib import Path
import numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter
sys.path.insert(0, str(Path(__file__).resolve().parent))
import hormuz_elemzes as he
FS = 10.4
H = Path("/mnt/user-data/uploads/Szakdolgozat/outputs/hormuz"); ki = Path(sys.argv[1])
hu = lambda dec: FuncFormatter(lambda v, p: f"{v:,.{dec}f}".replace(",", " ").replace(".", ","))
# 12. abra
d = pd.read_csv(H / "mintanap_mutatok.csv"); d["egy"] = 1
mut = {k.replace("H", "M"): v for k, v in he.MUTATOK.items()}
szin = {"A25": "#9ECAE9", "B25": "#4C78A8", "A26": "#FFBF79", "B26": "#F58518"}
rend = ["A25", "B25", "A26", "B26"]
fig, axs = plt.subplots(3, 1, figsize=(6.0, 6.3))
for ax, (m, (sz, nv, cim)), dec in zip(axs, mut.items(), (0, 2, 0)):
    atl = he.ablak_atlagok(d, sz, nv); ci = [he.ablak_ci(d, sz, nv, a) for a in rend]
    y = [atl[a] for a in rend]
    hib = np.array([[y[i] - ci[i][0] for i in range(4)], [ci[i][1] - y[i] for i in range(4)]])
    ax.bar(rend, y, color=[szin[a] for a in rend], yerr=hib, capsize=4, width=0.6)
    ax.set_title(f"{m}: {cim}", fontsize=FS, loc="left")
    ax.yaxis.set_major_formatter(hu(dec)); ax.tick_params(labelsize=FS)
    ax.spines[["top", "right"]].set_visible(False)
    print(m, {a: round(v, 4) for a, v in zip(rend, y)}, [tuple(round(x, 4) for x in c) for c in ci])
fig.tight_layout(h_pad=1.6)
fig.savefig(ki / "abra_ablakok_M.png", dpi=300)
plt.close(fig)
# 13. abra
oss = pd.read_csv(H / "uticel_osszetetel.csv")
p = oss.pivot(index="ablak", columns="kategoria", values="arany").reindex(index=rend, columns=he.KATEGORIAK).fillna(0)
szinek = ["#E45756", "#4C78A8", "#F58518", "#B279A2", "#72B7B2", "#BAB0AC"]
fig, ax = plt.subplots(figsize=(6.0, 5.0))
alj = np.zeros(len(p))
for k, c in zip(he.KATEGORIAK, szinek):
    ax.bar(p.index, 100 * p[k], bottom=alj, color=c, label=k, width=0.6); alj += 100 * p[k].to_numpy()
ax.set_ylabel("% a megrakott, kifelé haladó\ntanker-átkelések közül", fontsize=FS)
ax.tick_params(labelsize=FS); ax.set_ylim(0, 100)
ax.spines[["top", "right"]].set_visible(False)
ax.legend(fontsize=FS, loc="upper center", bbox_to_anchor=(0.45, -0.09), ncol=2, frameon=False)
fig.tight_layout()
fig.savefig(ki / "abra_uticel.png", dpi=300)
print(p.round(4).to_string())
