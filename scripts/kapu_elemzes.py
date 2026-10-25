"""
Az uj (kiserleti) kapuk elemzese a kapu_kiterjesztes.py kimenetebol.

1. Hajo-koncentracio kapunkent (komp-szures ellenorzese): a top 5 MMSI
   aranya, a Szemelyszallito tipus aranya, az MMSI-napok, amelyeken a hajo
   mindket iranyban atkelt, es a napi >= KOMP_NAPI_ATKELES atkeles.
2. Napi kereskedelmi (teherhajo + tanker) atkeles kapunkent: atlag, szoras,
   robusztus szoras (1,4826 x MAD), hetvege-hatas (hetvegi / hetkoznapi atlag).
3. A monitor jelzesi szabalya (monitor.jelzesek, importalva) az uj
   sorozatokra - kapunkent osszesen es iranyonkent is.
4. Kiel-ablak (2026-07-15 - 07-17): elteres az alapszinttol minden kapun.
5. PortWatch-osszevetes (data/portwatch_chokepoints.csv, Oresund Strait):
   a regi Oresund-kapu, a Drogden-kapu es az atmeno forgalom (Drogden +
   regi Oresund-kapu ugyanazon hajoval, ATMENO_ORA-n belul, azonos iranyban).

Kimenet (outputs/kapuk_kiterjesztes/):
  koncentracio.csv, napi_statisztika.csv, kereskedelmi_napi.csv,
  jelzesek.csv, kiel_ablak.csv, portwatch_osszevetes.csv

Hasznalat:
    python kapu_elemzes.py
    python kapu_elemzes.py --be outputs/kapuk_kiterjesztes --portwatch data/portwatch_chokepoints.csv
"""

import argparse
import contextlib
import io
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from utak import ADAT, KIMENET
with contextlib.redirect_stdout(io.StringIO()):
    from kapuvonal import KAPU_KONFIG, betolt
    from monitor import KERESKEDELMI, MAD_SKALA, jelzesek

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except AttributeError:
    pass

# --- Parameterek ----------------------------------------------------------

# Egy hajo, amely egy nap legalabb ennyiszer kel at ugyanazon a kapun,
# komp/ingazo gyanus: egy atmeno kereskedelmi hajo naponta 1, legfeljebb
# 2 (oda-vissza) atkelest ad; 4 mar legalabb ket teljes fordulo.
KOMP_NAPI_ATKELES = 4

# Atmeno forgalom: ugyanaz a hajo a Drogden-kapun es a regi Oresund-kapun
# (56,07 E) azonos iranyban, legfeljebb ennyi ora kulonbseggel. A ket kapu
# kozott ~60 km; 10 csomoval ~3,5 ora, 12 ora a lassu es a horgonyzo
# hajoknak is bovenel, de egy kikotoi tartozkodast (napok) mar nem hidal at.
ATMENO_ORA = 12

KIEL_NAPOK = ["2026-07-15", "2026-07-16", "2026-07-17"]
PW_KIKOTO = "Oresund Strait"
REGI_ORESUND = "Øresund"
DROGDEN = "Øresund – Drogden"


def koncentracio(atk: pd.DataFrame) -> pd.DataFrame:
    sorok = []
    for kapu, g in atk.groupby("kapu", sort=False):
        md = g.groupby(["datum", "MMSI"]).agg(n=("irany", "size"), ir=("irany", "nunique"))
        top = g["MMSI"].value_counts()
        k = g[g["csoport"].isin(KERESKEDELMI)]
        kmd = k.groupby(["datum", "MMSI"]).agg(n=("irany", "size"), ir=("irany", "nunique"))
        ktop = k["MMSI"].value_counts()
        sorok.append({
            "kapu": kapu, "atkeles": len(g), "hajo": g["MMSI"].nunique(),
            "top5_arany": top.head(5).sum() / len(g),
            "top1_napi_atlag": top.iloc[0] / g["datum"].nunique(),
            "szemelyszallito_arany": (g["csoport"] == "Személyszállító").mean(),
            "mmsi_nap_mindket_irany": int((md["ir"] > 1).sum()),
            "mindket_irany_atkeles_arany": md.loc[md["ir"] > 1, "n"].sum() / len(g),
            f"mmsi_nap_legalabb_{KOMP_NAPI_ATKELES}": int((md["n"] >= KOMP_NAPI_ATKELES).sum()),
            "ker_atkeles": len(k), "ker_hajo": k["MMSI"].nunique(),
            "ker_top5_arany": ktop.head(5).sum() / max(len(k), 1),
            "ker_top1_mmsi": int(ktop.index[0]) if len(k) else None,
            "ker_top1_atkeles": int(ktop.iloc[0]) if len(k) else 0,
            "ker_mmsi_nap_mindket_irany": int((kmd["ir"] > 1).sum()),
            f"ker_mmsi_nap_legalabb_{KOMP_NAPI_ATKELES}": int((kmd["n"] >= KOMP_NAPI_ATKELES).sum()),
        })
    return pd.DataFrame(sorok)


def kereskedelmi_sorozat(atk, napok, kapuk, iranyonkent=False):
    k = atk[atk["csoport"].isin(KERESKEDELMI)]
    if iranyonkent:
        k = k.assign(sorozat=k["kapu"] + " | " + k["irany"])
        oszlopok = [f"{kp.nev} | {i}" for kp in kapuk for i in kp.iranyok]
    else:
        k = k.assign(sorozat=k["kapu"])
        oszlopok = [kp.nev for kp in kapuk]
    s = k.pivot_table(index="datum", columns="sorozat", values="MMSI",
                      aggfunc="size", fill_value=0)
    return s.reindex(index=napok, columns=oszlopok, fill_value=0).astype(int)


def statisztika(s: pd.DataFrame) -> pd.DataFrame:
    het = pd.to_datetime(pd.Series(s.index, index=s.index)).dt.dayofweek
    sorok = []
    for nev in s.columns:
        x = s[nev].astype(float)
        mad = float(np.median(np.abs(x - x.median())))
        hk, hv = x[het < 5].mean(), x[het >= 5].mean()
        sorok.append({"sorozat": nev, "napok": len(x), "atlag": x.mean(), "median": x.median(),
                      "szoras": x.std(ddof=1), "rel_szoras": x.std(ddof=1) / x.mean() if x.mean() else np.nan,
                      "robusztus_szoras": MAD_SKALA * mad,
                      "rel_robusztus_szoras": MAD_SKALA * mad / x.median() if x.median() else np.nan,
                      "min": x.min(), "max": x.max(),
                      "hetkoznap_atlag": hk, "hetvege_atlag": hv,
                      "hetvege_per_hetkoznap": hv / hk if hk else np.nan})
    return pd.DataFrame(sorok)


def atmeno(atk: pd.DataFrame) -> pd.DataFrame:
    """Drogden-atkelesek, amelyekhez ATMENO_ORA-n belul azonos iranyu
    atkeles tartozik a regi Oresund-kapun (ugyanaz az MMSI)."""
    d = atk[atk["kapu"] == DROGDEN].copy()
    o = atk[atk["kapu"] == REGI_ORESUND][["MMSI", "irany", "ts"]].rename(columns={"ts": "ts_o"})
    d["ts"] = pd.to_datetime(d["ts"])
    o["ts_o"] = pd.to_datetime(o["ts_o"])
    d = d.reset_index(drop=True).reset_index(names="sor")
    p = d.merge(o, on=["MMSI", "irany"])
    p = p[(p["ts_o"] - p["ts"]).abs() <= pd.Timedelta(hours=ATMENO_ORA)]
    return d[d["sor"].isin(p["sor"])].drop(columns="sor")


def pw_osszevet(ais_napi: pd.Series, pw: pd.Series, nev: str, pw_nev: str) -> dict:
    j = pd.concat([ais_napi.rename("ais"), pw.rename("pw")], axis=1, join="inner").dropna()
    j.index = pd.to_datetime(j.index)
    arany = j["ais"] / j["pw"]
    w = j.resample("W-SUN").sum()
    return {"ais_sorozat": nev, "portwatch": pw_nev, "napok": len(j),
            "elso": j.index.min().date().isoformat(), "utolso": j.index.max().date().isoformat(),
            "r_napi": j["ais"].corr(j["pw"]), "spearman_napi": j["ais"].corr(j["pw"], method="spearman"),
            "arany_atlag": arany.mean(), "arany_min": arany.min(), "arany_max": arany.max(),
            "arany_rel_szoras": arany.std(ddof=1) / arany.mean(),
            "hetek": len(w), "r_heti": w["ais"].corr(w["pw"])}


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--be", type=Path, default=KIMENET / "kapuk_kiterjesztes")
    ap.add_argument("--kapuk", type=Path, default=KAPU_KONFIG)
    ap.add_argument("--portwatch", type=Path, default=ADAT / "portwatch_chokepoints.csv")
    args = ap.parse_args()

    kapuk = betolt(args.kapuk)
    atk = pd.read_csv(args.be / "atkelesek.csv", dtype={"datum": str})
    napok = sorted(atk["datum"].unique())
    print(f"Beolvasva: {len(atk):,} atkeles, {len(napok)} nap ({napok[0]} - {napok[-1]}), "
          f"{atk['kapu'].nunique()} kapu")

    # 1. koncentracio
    kc = koncentracio(atk)
    kc.to_csv(args.be / "koncentracio.csv", index=False, encoding="utf-8")
    print("\n1. Hajo-koncentracio (minden tipus | kereskedelmi):")
    for r in kc.itertuples():
        print(f"  {r.kapu:<18} {r.atkeles:>6} atk, top5 {r.top5_arany:5.1%}, szemely "
              f"{r.szemelyszallito_arany:5.1%}, MMSI-nap mindket irany {r.mmsi_nap_mindket_irany:>4} "
              f"({r.mindket_irany_atkeles_arany:5.1%}), >={KOMP_NAPI_ATKELES}/nap "
              f"{getattr(r, f'mmsi_nap_legalabb_{KOMP_NAPI_ATKELES}'):>4} | ker {r.ker_atkeles:>6}, "
              f"top5 {r.ker_top5_arany:5.1%}, top1 {r.ker_top1_mmsi} ({r.ker_top1_atkeles}), "
              f"mindket irany {r.ker_mmsi_nap_mindket_irany}, "
              f">={KOMP_NAPI_ATKELES}/nap {getattr(r, f'ker_mmsi_nap_legalabb_{KOMP_NAPI_ATKELES}')}")

    # 2. napi kereskedelmi sorozatok
    s = kereskedelmi_sorozat(atk, napok, kapuk)
    si = kereskedelmi_sorozat(atk, napok, kapuk, iranyonkent=True)
    pd.concat([s, si], axis=1).to_csv(args.be / "kereskedelmi_napi.csv", encoding="utf-8")
    st = statisztika(pd.concat([s, si], axis=1))
    st.to_csv(args.be / "napi_statisztika.csv", index=False, encoding="utf-8")
    print("\n2. Napi kereskedelmi atkeles:")
    for r in st[st["sorozat"].isin(s.columns)].itertuples():
        print(f"  {r.sorozat:<18} atlag {r.atlag:6.1f}, median {r.median:5.0f}, szoras {r.szoras:5.1f} "
              f"({r.rel_szoras:5.1%}), robusztus {r.robusztus_szoras:5.1f} ({r.rel_robusztus_szoras:5.1%}), "
              f"min-max {r.min:.0f}-{r.max:.0f}, hetvege/hetkoznap {r.hetvege_per_hetkoznap:.2f}")

    # 3. jelzesi szabaly (monitor.jelzesek) az osszes sorozatra
    j, kuszob, zaj = jelzesek(pd.concat([s, si], axis=1))
    j.to_csv(args.be / "jelzesek.csv", index=False, encoding="utf-8")
    print("\n3. monitor.jelzesek(): kuszob (2 x robusztus szoras) es jelzett napok:")
    for nev in s.columns:
        g = j[(j["sorozat"] == nev) & (j["jelzes"] != "nincs alapszint")]
        n_j = int(g["jelzes"].str.startswith("szokatlanul").sum())
        print(f"  {nev:<18} kuszob +/-{kuszob.get(nev, np.nan):6.1%}, {len(g)} nap alapszinttel, "
              f"jelzes {n_j} ({n_j / max(len(g), 1):5.1%})")

    # 4. Kiel-ablak
    j["abs_elteres"] = j["elteres"].abs()
    j["rang"] = j.groupby("sorozat")["abs_elteres"].rank(ascending=False, method="min")
    j["napok_alapszinttel"] = j.groupby("sorozat")["elteres"].transform("count")
    kiel = j[j["datum"].isin(KIEL_NAPOK)].drop(columns="abs_elteres")
    kiel.to_csv(args.be / "kiel_ablak.csv", index=False, encoding="utf-8")
    print("\n4. Kiel-ablak (kereskedelmi, osszesen): ertek / alapszint, elteres, jelzes, |elteres| rangja")
    for nev in s.columns:
        g = kiel[kiel["sorozat"] == nev]
        print(f"  {nev:<18} " + " | ".join(
            f"{r.datum[5:]}: {r.ertek:>3}/{r.alapszint:5.1f} {r.elteres:+6.1%} "
            f"{'JELZ' if str(r.jelzes).startswith('szokatlanul') else 'norm'} "
            f"#{r.rang:.0f}/{r.napok_alapszinttel}" for r in g.itertuples()))
    print("   iranyonkent (kifele = a Balti-tengerbol ki):")
    for kp in kapuk:
        for i in kp.iranyok:
            nev = f"{kp.nev} | {i}"
            g = kiel[kiel["sorozat"] == nev]
            jel = " (kifele)" if i == kp.kifele else ""
            print(f"  {nev + jel:<34} " + " | ".join(
                f"{r.datum[5:]}: {r.ertek:>3}/{r.alapszint:5.1f} {r.elteres:+6.1%} "
                f"{'JELZ' if str(r.jelzes).startswith('szokatlanul') else 'norm'}"
                for r in g.itertuples()))

    # 5. PortWatch
    pw = pd.read_csv(args.portwatch)
    pw = pw[pw["portname"] == PW_KIKOTO].set_index("date")
    ker = atk[atk["csoport"].isin(KERESKEDELMI)]
    at = atmeno(atk)
    at_ker = at[at["csoport"].isin(KERESKEDELMI)]

    def napi(df):
        return df.groupby("datum").size().reindex(napok, fill_value=0)

    sor = []
    for nev, d in ((REGI_ORESUND, ker[ker["kapu"] == REGI_ORESUND]),
                   (DROGDEN, ker[ker["kapu"] == DROGDEN]),
                   (f"{DROGDEN} + {REGI_ORESUND} (atmeno)", at_ker)):
        sor.append(pw_osszevet(napi(d), pw["n_total"], f"{nev}: kereskedelmi", "n_total"))
        sor.append(pw_osszevet(napi(d[d["csoport"] == "Tanker"]), pw["n_tanker"],
                               f"{nev}: tanker", "n_tanker"))
    pwo = pd.DataFrame(sor)
    pwo.to_csv(args.be / "portwatch_osszevetes.csv", index=False, encoding="utf-8")
    print(f"\n5. PortWatch ({PW_KIKOTO}); atmeno: Drogden-atkeles, amelyhez {ATMENO_ORA} oran "
          f"belul azonos iranyu atkeles tartozik a regi Oresund-kapun "
          f"({len(at_ker):,} / {len(ker[ker['kapu'] == DROGDEN]):,} kereskedelmi Drogden-atkeles):")
    for r in pwo.itertuples():
        print(f"  {r.ais_sorozat:<45} vs {r.portwatch:<8} {r.napok} nap ({r.elso} - {r.utolso}): "
              f"r {r.r_napi:.3f} (Spearman {r.spearman_napi:.3f}), arany {r.arany_atlag:.2f} "
              f"[{r.arany_min:.2f}-{r.arany_max:.2f}, rel. szoras {r.arany_rel_szoras:.1%}], "
              f"heti r {r.r_heti:.3f} ({r.hetek} het)")
    print(f"\n-> {args.be}/koncentracio.csv, napi_statisztika.csv, kereskedelmi_napi.csv, "
          f"jelzesek.csv, kiel_ablak.csv, portwatch_osszevetes.csv")
    return 0


if __name__ == "__main__":
    sys.exit(main())
