"""
A v7-es dolgozatvaltozat negy uj abraja.

  terkep_attekinto   a vizsgalati terulet, a kapuk es egy nap (2026-07-15) hajopoziciói
  h3_racs            8-as felbontasu H3-cellak a Nagy-Balti-hid kornyeken, a 3.2-es
                     lekerdezesi teglalappal es a Nagy-Balti-ov kapufolyosojaval
  tanker_suruseg     tankerjelenlet (hajo-ora / nap) 7-es H3-cellankent, a negy
                     Hormuz-ablakban (76 mintanap)
  ket_szoros_tanker  a Hormuzi-szoros (IMF PortWatch) es a dan szorosok (sajat meres) napi
                     tankerforgalma egymas alatt, kozos idotengelyen
  h1_idosor          a megrakott, kifele halado tanker-atkelesek napi szama (H1)
                     2025-ben es 2026-ban, az A/B ablakokkal

Bemenetek (alapertelmezes szerint a kodtar outputs/ mappajabol):
  tarolo/ev=2026/ho=07/aisdk-2026-07-15.parquet, tarolo_hormuz/**.parquet,
  hormuz/mintanap_mutatok.csv, hormuz/kiterjesztett/mintanap_mutatok.csv,
  scripts/kapuk.json, valamint a Natural Earth 10m szarazfoldi poligonjai
  (ne_10m_land.geojson, https://github.com/nvkelso/natural-earth-vector).

Hasznalat:
    python abrak_v7.py --outputs ../outputs --kapuk kapuk.json --land ne_10m_land.geojson --ki ../outputs/abrak_v7
"""

import argparse
import json
from pathlib import Path

import duckdb
import h3
import matplotlib
import numpy as np
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.collections import PolyCollection  # noqa: E402
from matplotlib.colors import LogNorm  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402

KERESK = "#2a78d6"      # kategoria 1
SZEMELY = "#eb6834"     # kategoria 2
EGYEB = "#a8a7a2"       # osszevont "egyeb"
SZARAZ = "#e9e7e1"
PART = "#b9b6ad"
TINTA = "#2b2b29"
MASOD = "#52514e"

plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 9, "axes.titlesize": 9.5,
    "axes.edgecolor": "#8a8984", "axes.linewidth": 0.6, "xtick.color": MASOD,
    "ytick.color": MASOD, "axes.labelcolor": MASOD, "figure.dpi": 100,
})

CIM = {"A25": "jan. 12. – febr. 27.", "B25": "márc. 9. – máj. 29.",
       "A26": "jan. 12. – febr. 27.", "B26": "márc. 9. – máj. 29."}
ABLAKOK = {"A25": ("2025-01-12", "2025-02-27"), "B25": ("2025-03-09", "2025-05-29"),
           "A26": ("2026-01-12", "2026-02-27"), "B26": ("2026-03-09", "2026-05-29")}


def szarazfold(ax, land, kiterjedes):
    lo0, lo1, la0, la1 = kiterjedes
    polik = []
    for f in land["features"]:
        g = f["geometry"]
        reszek = g["coordinates"] if g["type"] == "MultiPolygon" else [g["coordinates"]]
        for p in reszek:
            gyuru = np.asarray(p[0])
            if (gyuru[:, 0].max() < lo0 - 1 or gyuru[:, 0].min() > lo1 + 1
                    or gyuru[:, 1].max() < la0 - 1 or gyuru[:, 1].min() > la1 + 1):
                continue
            polik.append(gyuru)
    ax.add_collection(PolyCollection(polik, facecolor=SZARAZ, edgecolor=PART,
                                     linewidth=0.4, zorder=1))


def keret(ax, kiterjedes, dx=0.5, dy=0.5):
    lo0, lo1, la0, la1 = kiterjedes
    ax.set_xlim(lo0, lo1)
    ax.set_ylim(la0, la1)
    ax.set_aspect(1 / np.cos(np.radians((la0 + la1) / 2)), adjustable="box")
    ax.set_facecolor("white")
    ax.tick_params(labelsize=7.5, length=2)
    tx = np.arange(np.ceil(lo0 / dx) * dx, lo1 + 1e-9, dx)
    ty = np.arange(np.ceil(la0 / dy) * dy, la1 + 1e-9, dy)
    ax.set_xticks(tx)
    ax.set_yticks(ty)
    nx = 2 if dx < 0.1 else 1
    ny = 2 if dy < 0.1 else 1
    ax.set_xticklabels([f"{v:.{nx}f}° K".replace(".", ",") for v in tx])
    ax.set_yticklabels([f"{v:.{ny}f}° É".replace(".", ",") for v in ty])


DOBOZ = dict(boxstyle="round,pad=0.15", fc="white", ec="none", alpha=0.85)


def kapu_vonal(k):
    if "szelesseg" in k:
        return [k["hosszusag"][0], k["hosszusag"][1]], [k["szelesseg"]] * 2
    return [k["a"][1], k["b"][1]], [k["a"][0], k["b"][0]]


def csoport_sql(oszlop='"Ship type"'):
    return (f"CASE WHEN lower({oszlop}) LIKE '%cargo%' OR lower({oszlop}) LIKE '%tanker%' "
            f"THEN 'k' WHEN lower({oszlop}) LIKE '%passenger%' THEN 's' ELSE 'e' END")


def terkep_attekinto(con, nap, kapuk, land, ki):
    kit = (9.55, 13.25, 54.35, 56.60)
    df = con.sql(f"""
        SELECT Longitude AS lon, Latitude AS lat, {csoport_sql()} AS cs
        FROM (SELECT *, row_number() OVER (PARTITION BY MMSI, time_bucket(INTERVAL 2 MINUTE, ts)
                                           ORDER BY ts) AS rn
              FROM '{nap}'
              WHERE Latitude BETWEEN {kit[2]} AND {kit[3]} AND Longitude BETWEEN {kit[0]} AND {kit[1]})
        WHERE rn = 1""").df()
    fig, ax = plt.subplots(figsize=(6.3, 6.6))
    szarazfold(ax, land, kit)
    for cs, szin, s, z in (("e", EGYEB, 0.25, 2), ("s", SZEMELY, 0.35, 3), ("k", KERESK, 0.35, 4)):
        d = df[df.cs == cs]
        ax.scatter(d.lon, d.lat, s=s, c=szin, linewidths=0, alpha=0.55, zorder=z, rasterized=True)
    ax.add_patch(plt.Rectangle((10.0, 54.5), 3.0, 2.0, fill=False, ls=(0, (4, 3)),
                               lw=0.8, ec=TINTA, zorder=5))
    ax.text(10.04, 56.44, "vizsgálati terület", fontsize=7.5, color=TINTA, zorder=6, bbox=DOBOZ)
    for k in kapuk:
        xs, ys = kapu_vonal(k)
        if k["nev"] == "Skagen":
            continue
        fo = k.get("monitor", False)
        ax.plot(xs, ys, color="#111111" if fo else "#6250d6", lw=2.2 if fo else 1.4,
                solid_capstyle="round", zorder=7)
        cimke = {"Nagy-Balti-öv": (10.60, 55.32, "left"), "Øresund": (12.45, 56.12, "left"),
                 "Øresund – Drogden": (12.62, 55.44, "left"), "Fehmarn-öv": (11.20, 54.66, "left"),
                 "Kadet-rende": (12.20, 54.62, "left"), "Kis-Balti-öv": (9.62, 55.60, "left")}[k["nev"]]
        ax.text(cimke[0], cimke[1], k["nev"], fontsize=7.5 if fo else 7, ha=cimke[2],
                color=TINTA if fo else "#4a3db0", fontweight="bold" if fo else "normal", zorder=8,
                bbox=DOBOZ)
    keret(ax, kit, 0.5, 0.5)
    elemek = [Line2D([], [], ls="", marker="o", ms=4, color=c, label=l) for c, l in
              ((KERESK, "teher- és tankerhajó"), (SZEMELY, "személyszállító (komp)"),
               (EGYEB, "egyéb (kedvtelési, halász, szolgálati stb.)"))]
    elemek += [Line2D([], [], color="#111111", lw=2.2, label="monitorkapu"),
               Line2D([], [], color="#6250d6", lw=1.4, label="kísérleti kapu")]
    fig.legend(handles=elemek, loc="lower center", ncol=3, fontsize=7, frameon=False,
               bbox_to_anchor=(0.5, 0.0))
    fig.tight_layout(rect=(0, 0.07, 1, 1))
    fig.savefig(ki / "terkep_attekinto.png", dpi=300, bbox_inches="tight")
    plt.close(fig)
    return {"pozicio": len(df), "keresk": int((df.cs == "k").sum())}


def vonal_cellak(xs, ys, res, gyuru):
    """Ugyanaz, mint a kapuvonal.py folyosoja: a ket vegpont cellai kozotti
    grid_path_cells, plusz ket gyurunyi kornyezet."""
    a = h3.latlng_to_cell(ys[0], xs[0], res)
    b = h3.latlng_to_cell(ys[1], xs[1], res)
    alap = set(h3.grid_path_cells(a, b))
    out = set()
    for c in alap:
        out |= set(h3.grid_disk(c, gyuru))
    return alap, out


def h3_racs(con, nap, kapuk, land, ki):
    kit = (10.78, 11.30, 55.22, 55.47)
    df = con.sql(f"""
        SELECT h3, count(DISTINCT MMSI) AS hajo, sum(dup_db) AS sor FROM '{nap}'
        WHERE Latitude BETWEEN {kit[2] - 0.02} AND {kit[3] + 0.02}
          AND Longitude BETWEEN {kit[0] - 0.03} AND {kit[1] + 0.03} AND h3 IS NOT NULL
        GROUP BY h3""").df()
    nb = next(k for k in kapuk if k["nev"] == "Nagy-Balti-öv")
    xs, ys = kapu_vonal(nb)
    alap, folyoso = vonal_cellak(xs, ys, 8, 2)
    polik, ertek = [], []
    for c, n in zip(df.h3, df.hajo):
        s = h3.int_to_str(int(c))
        b = np.array(h3.cell_to_boundary(s))[:, ::-1]
        polik.append(b)
        ertek.append(n)
    fig, ax = plt.subplots(figsize=(6.3, 4.4))
    szarazfold(ax, land, kit)
    pc = PolyCollection(polik, array=np.array(ertek), cmap="Blues", norm=LogNorm(1, max(ertek)),
                        edgecolor="white", linewidth=0.25, zorder=2)
    ax.add_collection(pc)
    fpolik = [np.array(h3.cell_to_boundary(c))[:, ::-1] for c in folyoso]
    ax.add_collection(PolyCollection(fpolik, facecolor="none", edgecolor="#e34948",
                                     linewidth=0.5, zorder=3))
    ax.plot(xs, ys, color="#111111", lw=1.6, zorder=4)
    ax.text(10.79, 55.41, "Nagy-Balti-öv kapu (É 55,40°)", ha="left", va="bottom",
            fontsize=7.5, color=TINTA, zorder=6, bbox=DOBOZ)
    ax.add_patch(plt.Rectangle((10.85, 55.28), 0.30, 0.12, fill=False, ls=(0, (4, 3)), lw=1.0,
                               ec=TINTA, zorder=5))
    ax.text(10.855, 55.286, "a 3.2 alfejezet lekérdezési területe", fontsize=7, color=TINTA,
            zorder=6, bbox=DOBOZ)
    keret(ax, kit, 0.1, 0.05)
    cb = fig.colorbar(pc, ax=ax, shrink=0.8, pad=0.02)
    cb.set_label("különböző hajók a cellában (2026. július 15.)", fontsize=7.5)
    cb.ax.tick_params(labelsize=7)
    ax.legend(handles=[Line2D([], [], color="#e34948", lw=1, label="a kapu cellái és két cellányi környezetük")],
              loc="lower right", fontsize=7, framealpha=0.92, edgecolor="#cccccc")
    fig.tight_layout()
    fig.savefig(ki / "h3_racs.png", dpi=300, bbox_inches="tight")
    plt.close(fig)
    return {"cella": len(df), "folyoso_cella": len(folyoso), "vonal_cella": len(alap)}


def tanker_suruseg(con, tarolo, napok, land, ki):
    kit = (10.0, 13.0, 54.5, 56.5)
    fajlok = sorted(str(p) for p in Path(tarolo).rglob("*.parquet"))
    lista = "[" + ",".join(f"'{f}'" for f in fajlok) + "]"
    df = con.sql(f"""
        SELECT CAST(ts AS DATE) AS nap, h3, count(DISTINCT (MMSI, hour(ts))) AS hajo_ora
        FROM read_parquet({lista})
        WHERE lower("Ship type") LIKE '%tanker%' AND h3 IS NOT NULL
          AND Latitude BETWEEN {kit[2]} AND {kit[3]} AND Longitude BETWEEN {kit[0]} AND {kit[1]}
        GROUP BY ALL""").df()
    df["nap"] = pd.to_datetime(df["nap"]).dt.strftime("%Y-%m-%d")
    df = df.merge(napok[["nap", "ablak"]], on="nap", how="inner")
    df["c7"] = [h3.cell_to_parent(h3.int_to_str(int(c)), 7) for c in df.h3]
    # a 8-as cellak hajo-orait 7-es cellara osszegezzuk (egy hajo-ora ket 8-as cellaban
    # is lehet, ez a cella-szinten legfeljebb kis felulszamolast okoz; az ablakok kozott azonos)
    napszam = napok.groupby("ablak").nap.nunique()
    agg = df.groupby(["ablak", "c7"]).hajo_ora.sum().reset_index()
    agg["napi"] = agg.hajo_ora / agg.ablak.map(napszam)
    vmax = agg.napi.quantile(0.995)
    fig, axs = plt.subplots(2, 2, figsize=(6.3, 7.0), layout="constrained")
    for ax, ab in zip(axs.flat, ["A25", "B25", "A26", "B26"]):
        a = agg[agg.ablak == ab]
        polik = [np.array(h3.cell_to_boundary(c))[:, ::-1] for c in a.c7]
        szarazfold(ax, land, kit)
        pc = PolyCollection(polik, array=a.napi.to_numpy(), cmap="Blues",
                            norm=LogNorm(0.5, vmax), edgecolor="none", zorder=2)
        ax.add_collection(pc)
        ax.axhline(55.40, xmin=(10.60 - 10) / 3, xmax=(11.35 - 10) / 3, color="#111", lw=1)
        ax.plot([12.40, 12.85], [56.07, 56.07], color="#111", lw=1)
        keret(ax, kit, 1.0, 0.5)
        ax.set_title(f"{ab}: {ab[1:] and '20' + ab[1:]}. {CIM[ab]} ({napszam[ab]} mintanap)",
                     fontsize=8, color=TINTA)
        ax.tick_params(labelsize=6.5)
    cb = fig.colorbar(pc, ax=axs, shrink=0.7, location="bottom")
    cb.set_label("tankerjelenlét: hajó-óra naponta, 7-es felbontású H3-cellánként (log skála)",
                 fontsize=7.5)
    cb.ax.tick_params(labelsize=7)
    fig.savefig(ki / "tanker_suruseg.png", dpi=300, bbox_inches="tight")
    plt.close(fig)
    osszes = agg.groupby("ablak").hajo_ora.sum() / napszam
    return {"napi_hajo_ora": osszes.round(0).to_dict(), "napok": napszam.to_dict()}


def h1_idosor(fo, kit_csv, ki):
    f = pd.read_csv(fo, parse_dates=["nap"])
    k = pd.read_csv(kit_csv, parse_dates=["nap"])
    fig, axs = plt.subplots(2, 1, figsize=(6.3, 4.6), sharey=True)
    for ax, ev in zip(axs, (2025, 2026)):
        kk = k[k.nap.dt.year == ev]
        ff = f[f.nap.dt.year == ev]
        ax.scatter(kk.nap, kk.h1, s=7, color="#c9c8c2", linewidths=0, zorder=2,
                   label="minden nap (kiterjesztett minta, 258 nap)")
        ax.scatter(ff.nap, ff.h1, s=16, color=KERESK, linewidths=0.6, edgecolors="white",
                   zorder=3, label="kedd és csütörtök (fő minta, 76 nap)")
        for ab in (f"A{str(ev)[2:]}", f"B{str(ev)[2:]}"):
            t0, t1 = pd.Timestamp(ABLAKOK[ab][0]), pd.Timestamp(ABLAKOK[ab][1]) + pd.Timedelta(days=1)
            ax.axvspan(t0, t1, color="#f2f1ec", zorder=0)
            m = ff[ff.ablak == ab].h1.mean()
            ax.plot([t0, t1], [m, m], color=TINTA, lw=1.6, zorder=4)
            ax.text(t0 + pd.Timedelta(days=1), 20.6, f"{ab}  ablakátlag (fő minta): {m:.2f}".replace(".", ","),
                    fontsize=7.5, color=TINTA, va="top")
        if ev == 2026:
            z = pd.Timestamp("2026-02-28")
            ax.axvline(z, color="#e34948", lw=1.1, zorder=4)
            ax.text(z + pd.Timedelta(days=1), 1.0, "febr. 28.: a Hormuzi-szoros forgalma összeomlik",
                    color="#b8302f", fontsize=7.5)
        ax.set_xlim(pd.Timestamp(f"{ev}-01-08"), pd.Timestamp(f"{ev}-06-02"))
        ax.set_ylim(0, 21)
        ax.set_ylabel(f"{ev}\nátkelés / nap", fontsize=8)
        ax.grid(axis="y", color="#ebeae6", lw=0.6)
        ax.spines[["top", "right"]].set_visible(False)
        honapok = pd.date_range(f"{ev}-01-01", f"{ev}-06-01", freq="MS")
        ax.set_xticks(honapok)
        ax.set_xticklabels(["jan.", "febr.", "márc.", "ápr.", "máj.", "jún."], fontsize=7.5)
    axs[0].legend(loc="lower right", fontsize=7, frameon=True, framealpha=0.92, edgecolor="#cccccc")
    fig.tight_layout()
    fig.savefig(ki / "h1_idosor.png", dpi=300)
    plt.close(fig)
    return {ab: round(f[f.ablak == ab].h1.mean(), 3) for ab in ABLAKOK}



def ket_szoros(portwatch, napi_fajlok, mintanapok, monitor, ki, veg="2026-10-18"):
    """Felul a Hormuzi-szoros (IMF PortWatch), alul a dan szorosok (sajat AIS-meres)
    napi tankerforgalma, kozos idotengelyen."""
    pw = pd.read_csv(portwatch, usecols=["date", "portname", "n_tanker"], parse_dates=["date"])
    h = pw[pw.portname == "Strait of Hormuz"].set_index("date").n_tanker.sort_index()
    h = h.reindex(pd.date_range("2025-01-01", veg))
    napi = pd.concat([pd.read_csv(f) for f in napi_fajlok if Path(f).exists()])
    assert not napi.duplicated(["nap", "kapu", "csoport"]).any(), "atfedo napok a napi fajlokban"
    d = napi[napi.csoport == "Tanker"].groupby("nap").atkeles.sum()
    m = pd.read_csv(monitor)
    dm = m[m.csoport == "Tanker"].groupby("datum").atkeles.sum()
    dan = pd.concat([d, dm])
    dan.index = pd.to_datetime(dan.index)
    dan = dan.sort_index()[:veg]
    dan = dan.reindex(pd.date_range("2025-01-01", veg))
    ab = pd.read_csv(mintanapok, parse_dates=["nap"])
    hatar = ab.groupby("ablak").nap.agg(["min", "max"])
    ablak_atlag = {k: round(float(dan[r["min"]:r["max"]].mean()), 1) for k, r in hatar.iterrows()}

    fig, axs = plt.subplots(2, 1, figsize=(6.3, 5.6), sharex=True)
    for ax, s, cim in ((axs[0], h, "Hormuzi-szoros, tankerek mindkét irányban (IMF PortWatch)"),
                       (axs[1], dan, "Dán szorosok: Nagy-Balti-öv + Øresund, tanker-átkelések mindkét "
                                     "irányban (saját AIS-mérés)")):
        g = s.rolling(7, min_periods=7).mean()
        for k, r in hatar.iterrows():
            ax.axvspan(r["min"], r["max"] + pd.Timedelta(days=1), color="#f2f1ec", zorder=0)
        ax.plot(s.index, s, color="#c9c8c2", lw=0.6, zorder=2, label="napi érték")
        ax.plot(g.index, g, color=KERESK, lw=1.6, zorder=3, label="7 napos gördülő átlag")
        for nap, felirat in (("2026-02-28", "febr. 28."), ("2026-06-18", "jún. 18."), ("2026-07-08", "júl. 8.")):
            ax.axvline(pd.Timestamp(nap), color="#e34948", lw=0.9, ls=(0, (3, 2)), zorder=4)
        ax.set_title(cim, fontsize=8.5, loc="left", color=TINTA)
        ax.set_ylabel("tanker / nap", fontsize=8)
        ax.set_ylim(bottom=0)
        ax.grid(axis="y", color="#ebeae6", lw=0.6)
        ax.spines[["top", "right"]].set_visible(False)
    y1 = axs[0].get_ylim()[1]
    for nap, felirat in (("2026-02-28", "zár (febr. 28.)"), ("2026-06-18", "részleges újranyitás"),
                         ("2026-07-08", "újra zárva")):
        axs[0].text(pd.Timestamp(nap) + pd.Timedelta(days=3), y1 * 0.97, felirat, fontsize=7,
                    color="#b8302f", va="top", rotation=90)
    for k, r in hatar.iterrows():
        axs[1].text(r["min"] + pd.Timedelta(days=2), axs[1].get_ylim()[1] * 0.97, k, fontsize=7,
                    color=MASOD, va="top")
    hianyzo = dan.isna()
    if hianyzo.any():
        print("figyelem: hianyzo dan napok:", int(hianyzo.sum()))
    # 2026. junius 1-jetol a napi monitor tablajabol jonnek az ertekek (ld. a szoveget)
    axs[1].axvline(pd.Timestamp("2026-06-01"), color=MASOD, lw=0.8, ls=(0, (1, 2)), zorder=4)
    axs[1].text(pd.Timestamp("2026-06-04"), axs[1].get_ylim()[1] * 0.04, "napi monitor →", fontsize=7, zorder=5,
                bbox=dict(facecolor="white", edgecolor="none", pad=1.0),
                color=MASOD, va="bottom")
    axs[1].legend(loc="lower center", fontsize=7, frameon=True, framealpha=0.92, edgecolor="#cccccc",
                  bbox_to_anchor=(0.36, 0.04))
    honapok = pd.date_range("2025-01-01", veg, freq="QS")
    axs[1].set_xticks(honapok)
    axs[1].set_xticklabels([f"{d.year}. {['jan.', 'ápr.', 'júl.', 'okt.'][(d.month - 1) // 3]}" for d in honapok],
                           fontsize=7.5)
    axs[1].set_xlim(pd.Timestamp("2025-01-01"), pd.Timestamp(veg))
    fig.tight_layout()
    fig.savefig(ki / "ket_szoros_tanker.png", dpi=300)
    plt.close(fig)
    return {"ablak_atlag_dan": ablak_atlag, "dan_napok": int(dan.notna().sum()),
            "monitor_atlag": round(float(dm[:veg].mean()), 1)}

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--outputs", type=Path, required=True)
    ap.add_argument("--kapuk", type=Path)
    ap.add_argument("--land", type=Path)
    ap.add_argument("--ki", type=Path, required=True)
    ap.add_argument("--portwatch", type=Path, default=None,
                    help="data/portwatch_chokepoints_2026-10-25.csv (a ket szoros abrahoz)")
    ap.add_argument("--csak", default=None, help="csak ezt az abrat keszitse (pl. ket_szoros)")
    a = ap.parse_args()
    a.ki.mkdir(parents=True, exist_ok=True)
    if a.csak == "ket_szoros":
        print("ket_szoros", ket_szoros(a.portwatch, [a.outputs / "hormuz/napi.csv",
                                                     a.outputs / "hormuz/kiterjesztett/napi.csv",
                                                     a.outputs / "hormuz/kitoltes/napi.csv"],
                                       a.outputs / "hormuz/kiterjesztett/mintanap_mutatok.csv",
                                       a.outputs / "monitor/kapuvonal_napi.csv", a.ki))
        return
    land = json.loads(a.land.read_text(encoding="utf-8"))
    kapuk = json.loads(a.kapuk.read_text(encoding="utf-8"))["kapuk"]
    con = duckdb.connect()
    nap = a.outputs / "tarolo/ev=2026/ho=07/aisdk-2026-07-15.parquet"
    print("attekinto", terkep_attekinto(con, nap, kapuk, land, a.ki))
    print("h3", h3_racs(con, nap, kapuk, land, a.ki))
    napok = pd.read_csv(a.outputs / "hormuz/mintanap_mutatok.csv", dtype={"nap": str})
    print("suruseg", tanker_suruseg(con, a.outputs / "tarolo_hormuz", napok, land, a.ki))
    print("idosor", h1_idosor(a.outputs / "hormuz/mintanap_mutatok.csv",
                               a.outputs / "hormuz/kiterjesztett/mintanap_mutatok.csv", a.ki))


if __name__ == "__main__":
    main()
