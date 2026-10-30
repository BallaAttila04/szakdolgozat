"""
Hormuz-elemzes, 4. fazis: mutatok, kulonbsegek kulonbsege, erzekenyseg.

A dolgozat/hormuz_elozetes_merce.md (es a hormuz_merce_kiegeszites_2026-10-28.md,
hormuz_merce_kiegeszites_2026-10-29.md) szerint, a hormuz_napi.py kimeneteibol:

  H1  napi megrakott, kifele ("észak") halado tanker-atkelesek szama, a ket
      monitorkapu osszege
  H2  a Szuez/Azsia/Kozel-Kelet uticelu atkelesek aranya a kifele halado,
      megrakott tanker-atkelesekben (ablakonkent osszesitett arany)
  H3  a kifele halado tankerek napi volumenindexe (Σ hossz × szelesseg × merules)

Megrakottsag: megrakottsag.py; a max. merules a regi (fagyasztott monitor,
2026-06-01 - 10-22) es az uj minta napi meruleseinek P95-e MMSI-nkent; a
tankerkuszob rogzitett: 0,8148 (ellenorizzuk a fagyasztott parameterfajllal).

Becsles: (B26 - A26) - (B25 - A25); 95% heti blokkos bootstrap (2 000);
Holm-korrekcio H1-H3-ra. Hatas: ha a H1 vagy a H2 Holm-korrigalt intervalluma
nem tartalmazza a nullat.

Kimenet (outputs/hormuz/):
  eredmeny.csv                 H1-H3 fo eredmenye
  erzekenyseg.csv              a ket kiegeszites valtozatai (H1, H2)
  uticel_ertelmezhetoseg.csv   az uticel ertelmezhetosege ablakonkent, a szigoru
                               (fo) es az engedekeny olvasattal (2. kiegeszites)
  uticel_osszetetel.csv        az uticel-kategoriak ablakonkent
  uticel_nem_ertelmezheto.csv  a leggyakoribb nem ertelmezheto szovegek
  mintanap_mutatok.csv         mintanaponkent H1, H2 szamlalo/nevezo, H3
  monitor_ujranyitas.csv       masodlagos, leiro: a 06-18 - 07-08-i
                               ujranyitas a fagyasztott monitorban
  abra_ablakok.png, abra_uticel.png

Hasznalat:
    python hormuz_elemzes.py
    python hormuz_elemzes.py --hormuz outputs/hormuz --fagyasztott outputs/fagyasztas_2026-10-22/monitor
"""

import argparse
import json
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from utak import ADAT, KIMENET
import megrakottsag as mg
from hormuz_kozos import (ABLAKOK, ALFA, BOOTSTRAP_N, HORMUZ, SEED, UJRANYITAS, ablak,
                          ablak_atlagok, blokk, bootstrap_did, bootstrap_p, holm, intervallum)
from kikoto_feloldas import locode_betolt

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)
except AttributeError:
    pass

# --- Parameterek (a merce szerint; NEM az eredmenyek lattan) ------------------

FAGYASZTOTT = KIMENET / "fagyasztas_2026-10-22" / "monitor"

# Tankerkuszob: a fagyasztott allapot Otsu-erteke, rogzitve (merce)
TANKER_KUSZOB = 0.8148
# Erzekenyseg (kiegeszites, 3. pont): +/- 0,05
KUSZOB_VALTOZATOK = (0.7648, 0.8648)

MONITOR_KAPUK = ("Nagy-Balti-öv", "Øresund")
DROGDEN = "Øresund – Drogden"
KIFELE = "észak"          # mindharom erintett kapun ez a kifele irany (kapuk.json)

# Uticel-kategoriak (merce, "Uticel")
EU_EGT_UK = {"AT", "BE", "BG", "HR", "CY", "CZ", "DK", "EE", "FI", "FR", "DE", "GR", "HU",
             "IE", "IT", "LV", "LT", "LU", "MT", "NL", "PL", "PT", "RO", "SK", "SI", "ES",
             "SE", "NO", "IS", "GB", "CH"}
SZUEZ_ORSZAG = {"EG", "SA", "AE", "OM", "IN", "PK", "LK", "BD", "CN", "SG", "MY", "ID",
                "TH", "VN", "KR", "JP", "TW", "PH"}
SZUEZ_SZOVEG = ("PORT SAID", "SUEZ", "SINGAPORE", "FUJAIRAH")
KATEGORIAK = ["RU", "EU/EGT/UK", "Szuez/Ázsia/Közel-Kelet", "FOR ORDER", "Egyéb",
              "Nem értelmezhető"]
SZUEZ = "Szuez/Ázsia/Közel-Kelet"

# UN/LOCODE: 2 betus orszagkod + 3 karakteres helykod (betu vagy 2-9); a
# merce szerint a ket resz kozott egy szokoz megengedett
LOCODE_MINTA = re.compile(r"^([A-Z]{2}) ?([A-Z2-9]{3})$")
# Engedekeny olvasat (2. kiegeszites, 6. valtozat): a mezo elso LOCODE-szeru
# resze, elotte-utana nem betu/szamjegy ("BEANR VIA DENOK" -> BEANR)
LOCODE_JELOLT = re.compile(r"(?<![A-Z0-9])([A-Z]{2}) ?([A-Z2-9]{3})(?![A-Z0-9])")

# Masodlagos, leiro ellenorzes (merce): 0-30 napos kesleltetes
KESLELTETESEK = (0, 10, 20, 30)


# --- Uticel ------------------------------------------------------------------------

def kategoria(nyers, kodok) -> str:
    """A merce kategoriai. Sorrend: ervenyes LOCODE (orszag szerint), majd a
    Szuez-szovegek, majd az ORDER; minden mas nem ertelmezheto."""
    if not isinstance(nyers, str) or not nyers.strip():
        return "Nem értelmezhető"
    s = re.sub(r"\s+", " ", nyers.upper().strip())
    m = LOCODE_MINTA.match(s)
    if m and (m.group(1) + m.group(2)) in kodok:
        o = m.group(1)
        if o == "RU":
            return "RU"
        if o in EU_EGT_UK:
            return "EU/EGT/UK"
        if o in SZUEZ_ORSZAG:
            return SZUEZ
        return "Egyéb"
    if any(t in s for t in SZUEZ_SZOVEG):
        return SZUEZ
    if "ORDER" in s:
        return "FOR ORDER"
    return "Nem értelmezhető"


def kategoria_engedekeny(nyers, kodok) -> str:
    """2. kiegeszites, 6. valtozat: az elso LOCODE-szeru resz szamit, ha ervenyes
    kod; kulonben (nincs ilyen resz, vagy az elso nem ervenyes) a fo szabaly a
    teljes mezore. Kesobbi ervenyes kodot nem keresunk."""
    if isinstance(nyers, str):
        m = LOCODE_JELOLT.search(re.sub(r"\s+", " ", nyers.upper().strip()))
        if m and (m.group(1) + m.group(2)) in kodok:
            return kategoria(m.group(1) + m.group(2), kodok)
    return kategoria(nyers, kodok)


# --- Beolvasas ------------------------------------------------------------------------

def kesz_napok(h: Path) -> pd.DataFrame:
    minta = pd.read_csv(h / "mintanapok.csv", dtype={"nap": str})
    a = pd.read_csv(h / "feldolgozas.csv", dtype={"nap": str})
    kesz = set(a.loc[a.statusz == "kesz", "nap"])
    m = minta[minta.nap.isin(kesz)].copy()
    m["blokk"] = m["nap"].map(blokk)
    return m


def atkeles_tabla(h: Path, valtozat: str, kapuk, hm, kodok, napok) -> pd.DataFrame:
    """Tanker-atkelesek (ts-sel), merules/hossz/szelesseg es uticel-kategoria.
    valtozat: '' (fo), 'drogden', 'nyers', 'sulyozatlan'."""
    sfx = f"_{valtozat}" if valtozat else ""
    atk = pd.read_csv(h / f"atkelesek{sfx}.csv", dtype={"nap": str})
    resz = pd.read_csv(h / f"monitor{sfx}" / "atkelesek_reszletes.csv", dtype={"datum": str})
    # a reszletes tabla merules/hossz/szelesseg mezoi MMSI-nkent es naponkent
    # egyertelmuek (napi median, ld. megrakottsag.napi_frissites); ellenorizzuk
    hajo = resz[["datum", "MMSI", "merules", "hossz", "szelesseg"]].drop_duplicates()
    dup = hajo.duplicated(["datum", "MMSI"]).sum()
    if dup:
        raise RuntimeError(f"{valtozat or 'fo'}: {dup} (nap, MMSI) parnak tobb merules-erteke van")
    atk = atk[atk.kapu.isin(kapuk) & (atk.csoport == "Tanker") & atk.nap.isin(napok)].copy()
    t = atk.merge(hajo.rename(columns={"datum": "nap"}), on=["nap", "MMSI"], how="left")
    if len(t) != len(atk):
        raise RuntimeError("osszekapcsolasi hiba")
    t = mg.relativ(t, hm)
    t["volumen"] = np.where(mg.hiheto(t["merules"]), t["hossz"] * t["szelesseg"] * t["merules"], np.nan)
    u = pd.read_csv(h / "uticel.csv", dtype={"nap": str})
    u["ts"] = pd.to_datetime(u["ts"])
    u = u.drop_duplicates(["nap", "MMSI", "ts"])
    t["ts"] = pd.to_datetime(t["ts"])
    t = t.merge(u[["nap", "MMSI", "ts", "uticel", "uticel_utana"]], on=["nap", "MMSI", "ts"], how="left")
    t["kategoria"] = [kategoria(x, kodok) for x in t["uticel"]]
    return t


def napi_mutatok(t, napok_df, kuszob=TANKER_KUSZOB, for_order_nelkul=False) -> pd.DataFrame:
    """Mintanaponkent H1, a H2 szamlaloja/nevezoje, H3 (0, ha nincs atkeles)."""
    t = t.copy()
    t["megrakott"] = t["ertekelheto"] & (t["rel"] >= kuszob)
    ki = t[t.irany == KIFELE]
    mr = ki[ki.megrakott]
    nev = mr if not for_order_nelkul else mr[mr.kategoria != "FOR ORDER"]
    d = napok_df[["nap", "ablak", "blokk"]].copy().set_index("nap")
    d["h1"] = mr.groupby("nap").size().reindex(d.index, fill_value=0)
    d["h2_szamlalo"] = nev[nev.kategoria == SZUEZ].groupby("nap").size().reindex(d.index, fill_value=0)
    d["h2_nevezo"] = nev.groupby("nap").size().reindex(d.index, fill_value=0)
    d["h3"] = ki.groupby("nap")["volumen"].sum(min_count=1).reindex(d.index).fillna(0)
    d["kifele_tanker"] = ki.groupby("nap").size().reindex(d.index, fill_value=0)
    d["kifele_ertekelheto"] = ki.groupby("nap")["ertekelheto"].sum().reindex(d.index, fill_value=0)
    d["egy"] = 1
    return d.reset_index()


MUTATOK = {"H1": ("h1", "egy", "megrakott kifelé haladó tanker-átkelés / nap"),
           "H2": ("h2_szamlalo", "h2_nevezo", "Szuez/Ázsia-arány a megrakott kifelé haladók között"),
           "H3": ("h3", "egy", "kifelé haladó tankerek volumenindexe / nap (m³)")}


def becsul(d, mutatok=("H1", "H2", "H3")) -> dict:
    ki = {}
    for m in mutatok:
        sz, nv, _ = MUTATOK[m]
        pont, mintak = bootstrap_did(d, sz, nv)
        ki[m] = {"pont": pont, "mintak": mintak, "atlag": ablak_atlagok(d, sz, nv)}
    return ki


# --- Masodlagos: ujranyitas a fagyasztott monitorban -----------------------------------

def ujranyitas(fagy: Path) -> pd.DataFrame:
    t = pd.read_csv(fagy / "megrakottsag_napi.csv", dtype={"datum": str})
    t = t[(t.csoport == "Tanker") & (t.irany == KIFELE) & t.kapu.isin(MONITOR_KAPUK)]
    nap = t.groupby("datum").agg(megrakott=("megrakott", "sum"), ertekelheto=("ertekelheto", "sum"),
                                 atkeles=("atkeles", "sum"), volumenindex=("volumenindex", "sum"))
    nap.index = pd.to_datetime(nap.index)
    sorok = []
    k0, k1 = pd.Timestamp(UJRANYITAS[0]), pd.Timestamp(UJRANYITAS[1])
    for L in KESLELTETESEK:
        eltol = pd.Timedelta(days=L)
        szakaszok = {"előtte (zárva)": (nap.index.min(), k0 + eltol - pd.Timedelta(days=1)),
                     "újranyitás alatt": (k0 + eltol, k1 + eltol),
                     "utána (újra zárva)": (k1 + eltol + pd.Timedelta(days=1), nap.index.max())}
        for sz, (a, b) in szakaszok.items():
            g = nap[(nap.index >= a) & (nap.index <= b)]
            sorok.append({"kesleltetes_nap": L, "szakasz": sz, "kezdet": a.date(), "veg": b.date(),
                          "napok": len(g), "megrakott_kifele_tanker_nap": round(g.megrakott.mean(), 2),
                          "megrakott_arany": round(g.megrakott.sum() / g.ertekelheto.sum(), 4),
                          "kifele_tanker_nap": round(g.atkeles.mean(), 2),
                          "volumenindex_nap": round(g.volumenindex.mean(), 0)})
    return pd.DataFrame(sorok)


# --- Abrak ---------------------------------------------------------------------------

def ablak_ci(d, sz, nv, nev, n=BOOTSTRAP_N, seed=SEED):
    """Egy ablak atlaganak 95%-os heti blokkos bootstrap-intervalluma (az abrahoz)."""
    g = d[d.ablak == nev].groupby("blokk")[[sz, nv]].sum().to_numpy(float)
    rng = np.random.default_rng(seed)
    m = []
    for _ in range(n):
        x = g[rng.integers(0, len(g), len(g))]
        m.append(x[:, 0].sum() / x[:, 1].sum() if x[:, 1].sum() else np.nan)
    return intervallum(np.array(m))


def abra_ablakok(d, ut):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, axs = plt.subplots(1, 3, figsize=(13, 4))
    szin = {"A25": "#9ECAE9", "B25": "#4C78A8", "A26": "#FFBF79", "B26": "#F58518"}
    rend = ["A25", "B25", "A26", "B26"]
    for ax, (m, (sz, nv, cim)) in zip(axs, MUTATOK.items()):
        atl = ablak_atlagok(d, sz, nv)
        ci = [ablak_ci(d, sz, nv, a) for a in rend]
        y = [atl[a] for a in rend]
        hib = np.array([[y[i] - ci[i][0] for i in range(4)], [ci[i][1] - y[i] for i in range(4)]])
        ax.bar(rend, y, color=[szin[a] for a in rend], yerr=hib, capsize=4)
        ax.set_title(f"{m}: {cim}", fontsize=9)
    fig.suptitle("Ablakonkénti átlagok, 95% heti blokkos bootstrap-intervallum (kedd–csütörtöki mintanapok)",
                 fontsize=10)
    fig.tight_layout()
    fig.savefig(ut, dpi=150)
    plt.close(fig)


def abra_uticel(oss, ut):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    rend = ["A25", "B25", "A26", "B26"]
    # egy ures kategoria (pl. RU: 0 atkeles) a pivotbol kimarad; 0-val potoljuk
    p = (oss.pivot(index="ablak", columns="kategoria", values="arany")
         .reindex(index=rend, columns=KATEGORIAK).fillna(0))
    szin = ["#E45756", "#4C78A8", "#F58518", "#B279A2", "#72B7B2", "#BAB0AC"]
    fig, ax = plt.subplots(figsize=(7, 4.5))
    alj = np.zeros(len(p))
    for k, c in zip(KATEGORIAK, szin):
        ax.bar(p.index, 100 * p[k], bottom=alj, color=c, label=k)
        alj += 100 * p[k].to_numpy()
    ax.set_ylabel("% a megrakott, kifelé haladó tanker-átkelések közül")
    ax.set_title("Úticél-összetétel ablakonként", fontsize=10)
    ax.legend(fontsize=8, bbox_to_anchor=(1.01, 1), loc="upper left")
    fig.tight_layout()
    fig.savefig(ut, dpi=150)
    plt.close(fig)


# --- Fovonal -----------------------------------------------------------------------

def eredmeny_tabla(b, alfa=ALFA, cimke="fő"):
    pk = {m: bootstrap_p(v["mintak"]) for m, v in b.items()}
    ho = holm(pk, alfa)
    sorok = []
    for m, v in b.items():
        a, f = intervallum(v["mintak"])
        ha, hf = intervallum(v["mintak"], ho[m]["szint"])
        sorok.append({"valtozat": cimke, "mutato": m, "leiras": MUTATOK[m][2],
                      **{f"atlag_{k}": v["atlag"][k] for k in ABLAKOK},
                      "did": v["pont"], "ci95_also": a, "ci95_felso": f,
                      "p_bootstrap": pk[m], "holm_rang": ho[m]["rang"], "holm_szint": ho[m]["szint"],
                      "p_holm": ho[m]["p_holm"], "holm_ci_also": ha, "holm_ci_felso": hf,
                      "holm_elvet": ho[m]["elvet"]})
    t = pd.DataFrame(sorok)
    t["bootstrap_n"] = BOOTSTRAP_N
    return t


def kovetkeztetes(t) -> str:
    e = t[t.mutato.isin(["H1", "H2"]) & t.holm_elvet]
    return "kimutatható" if len(e) else "nem mutatható ki"


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--hormuz", type=Path, default=HORMUZ)
    ap.add_argument("--fagyasztott", type=Path, default=FAGYASZTOTT)
    ap.add_argument("--locode", type=Path, default=ADAT / "unlocode_code-list.csv")
    args = ap.parse_args()
    h = args.hormuz

    # 1. kuszob-ellenorzes
    param = json.loads((args.fagyasztott / "megrakottsag_param.json").read_text(encoding="utf-8"))
    print(f"Tankerkuszob: rogzitett {TANKER_KUSZOB}, fagyasztott param.json {param['kuszob']['Tanker']} "
          f"-> {'EGYEZIK' if param['kuszob']['Tanker'] == TANKER_KUSZOB else 'ELTER'}")
    if param["kuszob"]["Tanker"] != TANKER_KUSZOB:
        sys.exit("A rogzitett kuszob elter a fagyasztott allapottol - megallok.")

    napok = kesz_napok(h)
    print(f"Kesz mintanapok: {len(napok)} -> " +
          ", ".join(f"{a} {int((napok.ablak == a).sum())}" for a in ABLAKOK))

    # max. merules: regi + uj minta
    regi = pd.read_csv(args.fagyasztott / "merules_tortenet.csv", dtype={"nap": str})
    uj = pd.read_csv(h / "monitor" / "merules_tortenet.csv", dtype={"nap": str})
    uj = uj[uj.nap.isin(set(napok.nap))]
    hm = mg.hajo_max(pd.concat([regi, uj], ignore_index=True))
    print(f"Merules-tortenet: regi {len(regi):,} sor ({regi.nap.nunique()} nap), "
          f"uj {len(uj):,} sor ({uj.nap.nunique()} nap) -> {len(hm):,} hajo P95-je")

    kodok, _ = locode_betolt(args.locode)
    nl = set(napok.nap)
    t = atkeles_tabla(h, "", MONITOR_KAPUK, hm, kodok, nl)
    t["ablak"] = t["nap"].map(ablak)
    ki = t[t.irany == KIFELE]
    print(f"Tanker-atkelesek a ket monitorkapun: {len(t):,}, ebbol kifele {len(ki):,}, "
          f"ertekelheto {int(ki.ertekelheto.sum()):,}")

    # 2. uticel: ertelmezhetoseg es osszetetel
    ki = ki.assign(megrakott=ki.ertekelheto & (ki.rel >= TANKER_KUSZOB),
                   kategoria_eng=[kategoria_engedekeny(x, kodok) for x in ki["uticel"]])
    ert = []
    for olvasat, oszl in (("szigorú (fő)", "kategoria"), ("engedékeny (6. változat)", "kategoria_eng")):
        for a in ABLAKOK:
            for kor, g in [("kifelé haladó tanker", ki[ki.ablak == a]),
                           ("megrakott, kifelé haladó tanker (H2 nevezője)", ki[(ki.ablak == a) & ki.megrakott])]:
                ert.append({"olvasat": olvasat, "ablak": a, "kor": kor, "atkeles": len(g),
                            "van_uticel_az_atkeles_elott": int(g.uticel.notna().sum()),
                            "ertelmezheto": int((g[oszl] != "Nem értelmezhető").sum()),
                            "ertelmezheto_arany": round((g[oszl] != "Nem értelmezhető").mean(), 4) if len(g) else np.nan,
                            "csak_utana_van_uticel": int((g.uticel.isna() & g.uticel_utana.notna()).sum())})
    ert = pd.DataFrame(ert)
    ert.to_csv(h / "uticel_ertelmezhetoseg.csv", index=False, encoding="utf-8")
    print("\nUticel ertelmezhetosege ablakonkent:")
    print(ert.to_string(index=False))
    mr = ki[ki.megrakott]
    oss = (mr.groupby(["ablak", "kategoria"]).size().rename("atkeles").reset_index())
    oss["arany"] = (oss["atkeles"] / oss.groupby("ablak")["atkeles"].transform("sum")).round(4)
    oss.to_csv(h / "uticel_osszetetel.csv", index=False, encoding="utf-8")
    print("\nUticel-osszetetel (megrakott, kifele halado tanker-atkelesek):")
    print(oss.pivot(index="kategoria", columns="ablak", values="atkeles").reindex(KATEGORIAK)
          [[a for a in ABLAKOK if a in set(oss.ablak)]].fillna(0).astype(int).to_string())
    ne = ki[ki.kategoria == "Nem értelmezhető"]["uticel"].fillna("(nincs elozmeny aznap)")
    ne.value_counts().head(40).rename_axis("uticel").reset_index(name="atkeles").to_csv(
        h / "uticel_nem_ertelmezheto.csv", index=False, encoding="utf-8")

    # 3. H1-H3
    d = napi_mutatok(t, napok)
    d.drop(columns="egy").to_csv(h / "mintanap_mutatok.csv", index=False, encoding="utf-8")
    b = becsul(d)
    e = eredmeny_tabla(b)
    e.to_csv(h / "eredmeny.csv", index=False, encoding="utf-8")
    pd.set_option("display.width", 250)
    print("\nEredmeny, (B26 - A26) - (B25 - A25):")
    print(e.drop(columns=["leiras", "bootstrap_n"]).round(4).to_string(index=False))
    fo = kovetkeztetes(e)
    print(f"\nKOVETKEZTETES (merce): Hormuz-hatas {fo}")

    # 4. abrak
    abra_ablakok(d, h / "abra_ablakok.png")
    abra_uticel(oss, h / "abra_uticel.png")

    # 5. erzekenyseg (kiegeszites)
    erz = []

    def sor(valt, m, b1, e1):
        r = e1[e1.mutato == m].iloc[0]
        k = "kimutatható" if not (r.ci95_also <= 0 <= r.ci95_felso) else "nem kimutatható"
        kh = "kimutatható" if r.holm_elvet else "nem kimutatható"
        erz.append({"valtozat": valt, "mutato": m, "becsles": r.did, "ci95_also": r.ci95_also,
                    "ci95_felso": r.ci95_felso, "kovetkeztetes_ci95": k,
                    "kovetkeztetes_holm": kh, "fo_kovetkeztetes": kovetkeztetes(e1),
                    "valtozik_a_fo_kovetkeztetes": kovetkeztetes(e1) != fo})

    for m in ("H1", "H2"):
        sor("fő változat", m, b, e)
    valtozatok = []
    td = atkeles_tabla(h, "drogden", (DROGDEN,), hm, kodok, nl)
    tm = t[t.kapu == "Nagy-Balti-öv"].drop(columns="ablak")
    valtozatok.append(("1. mérési hely: Øresund helyett Øresund – Drogden",
                       napi_mutatok(pd.concat([tm, td], ignore_index=True), napok)))
    for v, cim in [("nyers", "2a. duplikátumok: nyers ismétlődések (dup_db-szer ismételt pozíciók)"),
                   ("sulyozatlan", "2b. duplikátumok: tisztán deduplikált (típus és merülés dup_db-súly nélkül)")]:
        valtozatok.append((cim, napi_mutatok(atkeles_tabla(h, v, MONITOR_KAPUK, hm, kodok, nl), napok)))
    for k in KUSZOB_VALTOZATOK:
        valtozatok.append((f"3. megrakottsági küszöb {k}", napi_mutatok(t, napok, kuszob=k)))
    valtozatok.append(("4. FOR ORDER kimarad a H2 nevezőjéből",
                       napi_mutatok(t, napok, for_order_nelkul=True)))
    # 2. kiegeszites; H1 es H3 nem fugg az uticeltol, ezert csak H2
    te = t.assign(kategoria=[kategoria_engedekeny(x, kodok) for x in t["uticel"]])
    valtozatok.append(("6. úticél: engedékeny olvasat (az első UN/LOCODE-szerű rész)",
                       napi_mutatok(te, napok)))
    for cim, dv in valtozatok:
        bv = becsul(dv)
        ev = eredmeny_tabla(bv, cimke=cim)
        for m in (("H2",) if cim.startswith(("4.", "6.")) else ("H1", "H2")):
            sor(cim, m, bv, ev)
        # a 2a valtozat atkelesszama a fo valtozattal (konstrukcio szerint egyezik)
        if cim.startswith("2a"):
            print(f"\n2a: H1 napi osszeg nyers vs fo: {int(dv.h1.sum())} / {int(d.h1.sum())}; "
                  f"kifele tanker-atkeles: {int(dv.kifele_tanker.sum())} / {int(d.kifele_tanker.sum())}")
        if cim.startswith("2b"):
            print(f"2b: H1 napi osszeg sulyozatlan vs fo: {int(dv.h1.sum())} / {int(d.h1.sum())}; "
                  f"kifele tanker-atkeles: {int(dv.kifele_tanker.sum())} / {int(d.kifele_tanker.sum())}")
    for m in ("H1", "H3"):
        sor("5. mérőszám: H1 (darabszám) kontra H3 (volumenindex)", m, b, e)
    erz = pd.DataFrame(erz)
    erz.to_csv(h / "erzekenyseg.csv", index=False, encoding="utf-8")
    print("\nErzekenyseg:")
    print(erz.round(4).to_string(index=False))

    # 6. masodlagos: ujranyitas a fagyasztott monitorban
    u = ujranyitas(args.fagyasztott)
    u.to_csv(h / "monitor_ujranyitas.csv", index=False, encoding="utf-8")
    print("\nMasodlagos (leiro): ujranyitas a fagyasztott monitorban, kifele halado tankerek, ket kapu:")
    print(u.to_string(index=False))

    print(f"\nFeldolgozva: {len(napok)} mintanap, {len(t):,} tanker-atkeles; H1-H3 napi sor: {len(d)}")
    for f in ("eredmeny.csv", "erzekenyseg.csv", "uticel_ertelmezhetoseg.csv", "uticel_osszetetel.csv",
              "uticel_nem_ertelmezheto.csv", "mintanap_mutatok.csv", "monitor_ujranyitas.csv",
              "abra_ablakok.png", "abra_uticel.png"):
        print(f"-> {h / f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
