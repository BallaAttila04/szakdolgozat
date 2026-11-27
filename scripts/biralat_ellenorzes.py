"""
Utolagos ellenorzesek a bíráló kérdéseire (2026-11-26). Egyik sem resze az
elore rogzitett mercenek; a dolgozat 4.1.5, 4.2.1 (8. abra forrasa) es 4.2.6
alfejezete kozli oket.

  1. 8. abra: a 2026-03-02-i kiugras oka (hajonkenti tobbszoros atkeles)
  2. Hormuz M1: gyanus ballasztos "megrakott" atkelesek nelkul, es
     hajohossz szerinti szukites (DiD, heti blokkos bootstrap, mint a fo elemzes)
  3. Oresund vs. PortWatch: korrelacio a het napja szerinti atlagok kivonasa utan

Futtatas a projekt gyokerebol:  python scripts/biralat_ellenorzes.py
(a 2. ponthoz kell az outputs/tarolo_hormuz/ es a fagyasztott monitorallapot)
"""
import glob, sys
from pathlib import Path
import numpy as np, pandas as pd

GY = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(GY / "scripts"))
import megrakottsag as mg
from hormuz_kozos import ablak, blokk, bootstrap_did, intervallum

O = GY / "outputs"
TANKER_KUSZOB = 0.8148
TL_GYANUS = 0.045          # merules / hossz alatt valoszinuleg ballaszt


def kiugras():
    a = pd.read_csv(O / "hormuz/kitoltes/atkelesek.csv")
    g = a.groupby(["nap", "kapu", "MMSI", "csoport"]).size().rename("n").reset_index()
    t = g[(g.csoport == "Tanker") & (g.n > 2)].sort_values("n", ascending=False)
    print("Tanker hajo-nap-kapu, napi 2-nel tobb atkelessel (516 nap):\n", t.head(10).to_string(index=False))
    x = a[(a.nap == "2026-03-02") & (a.csoport == "Tanker")]
    print("2026-03-02 tanker-atkeles:", len(x), "; a ket hajo nelkul:",
          len(x[~x.MMSI.isin([219034365, 613003614])]))
    f = pd.read_csv(O / "hormuz/atkelesek.csv")
    m = f[f.csoport == "Tanker"].groupby(["nap", "kapu", "MMSI"]).size().max()
    print("76 mintanap: egy tanker legtobb atkelese egy kapun egy nap alatt:", m)


def hormuz():
    H = []
    for f in sorted(glob.glob(str(O / "tarolo_hormuz/ev=*/ho=*/*.parquet"))):
        h = mg.napi_hajoadat(f); h["nap"] = Path(f).stem.split("aisdk-")[1]; H.append(h)
    H = pd.concat(H)
    regi = pd.read_csv(O / "fagyasztas_2026-10-22/monitor/merules_tortenet.csv", dtype={"nap": str})
    hm = mg.hajo_max(pd.concat([regi, H.dropna(subset=["merules"])[["nap", "MMSI", "merules"]]]))
    atk = pd.read_csv(O / "hormuz/atkelesek.csv", dtype={"nap": str})
    a = atk[atk.kapu.isin(["Nagy-Balti-öv", "Øresund"]) & (atk.csoport == "Tanker")]
    a = a.merge(H[["nap", "MMSI", "merules", "hossz", "szelesseg"]], on=["nap", "MMSI"], how="left")
    km = pd.to_numeric(a.merules_m, errors="coerce")
    a["merules"] = np.where(mg.hiheto(km), km, a.merules).round(1)
    t = mg.relativ(a, hm)
    ki = t[t.irany == "észak"].copy()
    ki["megrakott"] = ki.ertekelheto & (ki.rel >= TANKER_KUSZOB)
    print(f"kifele {len(ki)}, ertekelheto {int(ki.ertekelheto.sum())}, megrakott {int(ki.megrakott.sum())} "
          "(a dolgozatban 1 182 / 1 119 / 663)")
    napok = atk[["nap"]].drop_duplicates()
    napok["ablak"] = napok.nap.map(ablak); napok["blokk"] = napok.nap.map(blokk)

    def becs(sel, nev):
        d = napok.copy(); d["h1"] = d.nap.map(sel.groupby("nap").size()).fillna(0); d["egy"] = 1
        p, m = bootstrap_did(d, "h1", "egy"); lo, hi = intervallum(m)
        print(f"{nev:45s} n={len(sel):4d}  DiD={p:+.2f}  95% CI=({lo:+.2f}; {hi:+.2f})")

    mr = ki[ki.megrakott].copy(); mr["TL"] = mr.merules / mr.hossz
    gy = mr.TL < TL_GYANUS
    print(f"gyanus ballaszt (T/L < {TL_GYANUS}): {int(gy.sum())} ({gy.mean():.1%})")
    becs(mr, "fo (reprodukcio)")
    becs(mr[~gy], "gyanus ballaszt nelkul")
    for L in (100, 150, 200):
        becs(mr[mr.hossz >= L], f"legalabb {L} m")


def portwatch():
    pw = pd.read_csv(GY / "data/portwatch_chokepoints_2026-10-25.csv")
    pw = pw[pw.portname == "Oresund Strait"]
    pw = pw.assign(date=pd.to_datetime(pw.date.str[:10])).set_index("date").n_total
    k = pd.read_csv(O / "kapuk_kiterjesztes/kereskedelmi_napi.csv", parse_dates=["datum"]).set_index("datum")
    d = pd.concat([k[["Øresund", "Øresund – Drogden"]], pw.rename("pw")], axis=1, sort=True)
    d = d.loc["2026-06-01":"2026-10-18"].dropna()
    hn = d.index.dayofweek
    for c in ("Øresund", "Øresund – Drogden"):
        a = d[c] - d[c].groupby(hn).transform("mean"); b = d.pw - d.pw.groupby(hn).transform("mean")
        print(f"{c}: r = {d[c].corr(d.pw):.3f}, a het napja nelkul r = {a.corr(b):.3f} ({len(d)} nap)")


if __name__ == "__main__":
    kiugras(); portwatch(); hormuz()
