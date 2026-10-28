"""
Hormuz-elemzes, 2-3. fazis: a mintanapok letoltese es feldolgozasa,
napról napra, szuk lemezen.

Naponkent (outputs/hormuz/mintanapok.csv, ld. hormuz_minta.py):
  1. pipeline.py KULON taroloba (outputs/tarolo_hormuz_tmp), DR-reteg nelkul,
     a ZIP a validalas utan torolve; a napi sor az outputs/hormuz/
     pipeline_napok.csv-be kerul. Validalas: SUM(dup_db) == ZIP-sorszam
     (a pipeline.py-ban, es itt meg egyszer, a kesz fajlbol visszaolvasva).
  2. kapuvonal.py a ket monitorkapura (fo valtozat) es kulon hivasban az
     "Øresund – Drogden" kapura (a merce kiegeszitese, 1. pont; kulon hivas,
     hogy a monitorkapuk tipus-szavazasa ne valtozzon, ld. kapuvonal.feldolgoz).
  3. A kiegeszites 2. pontja (duplikatumszures) ket valtozata:
       nyers        - a poziciok dup_db-szer ismetelve, ahogy a forrasban
                      voltak; a tipus-szavazas es a merules-median sulyozott
                      (mint a fo valtozatban)
       sulyozatlan  - deduplikalt pontok, a tipus-szavazas es a merules-
                      median dup_db-suly NELKUL (tisztan deduplikalt adat)
  4. megrakottsag.napi_frissites: hajonkenti napi merules (merules_tortenet)
     es az atkelesek reszletes tablaja (merules, hossz, szelesseg)
     valtozatonkent kulon mappaban.
  5. Uticel atkelesenkent: a hajo utolso nem ures Destination-erteke az
     atkeles elott (merce: 24 oran belul; itt csak az aznapi adat van meg,
     ld. naplo). Diagnosztikanak az atkeles utani elso erteket is eltesszuk.
  6. Szurt Parquet: csak a Ship type in {Tanker, Cargo} sorok, minden
     oszloppal: outputs/tarolo_hormuz/ev=YYYY/ho=MM/aisdk-YYYY-MM-DD.parquet
  7. A teljes napi Parquet torlese a tmp-tarolobol.
  8. Meres: letoltesi es feldolgozasi ido, szurt meret, csucs lemezhasznalat,
     szabad hely -> outputs/hormuz/feldolgozas.csv

Idempotens: a kesz napot kihagyja; megszakadas utan folytathato. Technikai
hibanal egy napot legfeljebb MAX_KISERLET-szer probal. Hibas napot nem
potolunk masik nappal (merce).

Hasznalat:
    python hormuz_napi.py --elso 2          # proba: az elso ket mintanap
    python hormuz_napi.py                   # a teljes minta
    python hormuz_napi.py --napok 2026-01-13 2025-03-11
    python hormuz_napi.py --osszesito       # csak az ablakonkenti allapot
"""

import argparse
import shutil
import subprocess
import sys
import threading
import time
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd

from utak import GYOKER, KIMENET, SABLONOK
import kapuvonal as kv
import megrakottsag as mg
from hajo_statisztika import tisztit
from hormuz_kozos import ABLAKOK, HORMUZ
from kikoto_feloldas import URES as UTICEL_URES

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)
except AttributeError:
    pass

# --- Parameterek ----------------------------------------------------------

TMP_TAROLO = KIMENET / "tarolo_hormuz_tmp"
SZURT_TAROLO = KIMENET / "tarolo_hormuz"
MINTA = HORMUZ / "mintanapok.csv"
ALLAPOT = HORMUZ / "feldolgozas.csv"
PIPELINE_NAPLO = HORMUZ / "pipeline_napok.csv"

# A szurt taroloba kerulo hajotipusok (feladat, 2. fazis): a megrakottsag es
# az uticel csak tanker es teherhajo (Cargo) eseten kell.
SZURT_TIPUSOK = ("Tanker", "Cargo")

DROGDEN = "Øresund – Drogden"

# Ha a szabad hely ez ala esik, megallunk (feladat: 6 GB).
MIN_SZABAD_GB = 6.0

# Technikai hiba eseten ennyiszer probalunk egy napot (feladat: max. 3).
MAX_KISERLET = 3

MERES_MP = 0.5


# --- Segedfuggvenyek -------------------------------------------------------

def szabad_gb(ut=GYOKER) -> float:
    return shutil.disk_usage(ut).free / 1024 ** 3


class LemezMero:
    """Hatterszal: a szabad hely minimuma a nap teljes ideje alatt."""
    def __init__(self):
        self.kezdo = szabad_gb()
        self.minimum = self.kezdo
        self._stop = threading.Event()

    def __enter__(self):
        def fut():
            while not self._stop.is_set():
                self.minimum = min(self.minimum, szabad_gb())
                self._stop.wait(MERES_MP)
        self._t = threading.Thread(target=fut, daemon=True)
        self._t.start()
        return self

    def __exit__(self, *a):
        self._stop.set()
        self._t.join()

    @property
    def csucs_gb(self):
        return self.kezdo - self.minimum


def hozzafuz(ut: Path, uj: pd.DataFrame, nap: str, kulcs="nap"):
    """Idempotens hozzafuzes: a nap korabbi sorait lecsereli."""
    if ut.exists():
        regi = pd.read_csv(ut, dtype={kulcs: str})
        uj = pd.concat([regi[regi[kulcs] != nap], uj], ignore_index=True)
    uj = uj.sort_values([kulcs]).reset_index(drop=True)
    tmp = ut.with_suffix(".tmp")
    uj.to_csv(tmp, index=False, encoding="utf-8")
    tmp.replace(ut)


def allapot_olvas() -> pd.DataFrame:
    if ALLAPOT.exists():
        return pd.read_csv(ALLAPOT, dtype={"nap": str})
    return pd.DataFrame(columns=["nap", "statusz", "kiserlet"])


def allapot_ir(sor: dict):
    hozzafuz(ALLAPOT, pd.DataFrame([sor]), sor["nap"])


# --- Atkelesek -------------------------------------------------------------

def atk_formaz(atk: pd.DataFrame, nap: str) -> pd.DataFrame:
    """A kapuvonal.py CLI kimenetenek oszlopai."""
    if atk.empty:
        return pd.DataFrame(columns=["nap", "kapu", "ts", "MMSI", "irany", "csoport", "merules_m"])
    a = atk.copy()
    a["nap"] = nap
    return a[["nap", "kapu", "ts", "MMSI", "irany", "csoport", "merules_m"]]


def valtozatok(pq: Path, kapuk: dict, folyosok: dict):
    """A merce kiegeszitesenek 2. pontja. Ugyanaz a lekerdezes, mint a
    kapuvonal.feldolgoz_parquet()-ben; ket valtozat:
      nyers       - minden pozicio dup_db-szer (a forras ismetlodesei);
                    tipus/merules sulyozott, mint a fo valtozatban
      sulyozatlan - deduplikalt pontok; tipus/merules suly nelkul"""
    f = Path(pq).as_posix()
    con = duckdb.connect()
    gy_ny = {k: [] for k in kapuk}
    gy_s = {k: [] for k in kapuk}
    tip_w, mer_w = defaultdict(Counter), defaultdict(list)
    tip_1, mer_1 = defaultdict(Counter), defaultdict(list)
    for nev, k in kapuk.items():
        la0, la1, lo0, lo1 = k.bbox()
        sav = con.execute(f"""
            SELECT ts, MMSI, Latitude, Longitude, "Ship type", Draught, dup_db, h3
            FROM read_parquet('{f}')
            WHERE Latitude BETWEEN {la0} AND {la1}
              AND Longitude BETWEEN {lo0} AND {lo1}
            ORDER BY MMSI, ts, sorrend""").df()
        sav = sav[np.isin(sav["h3"].to_numpy(), list(folyosok[nev]))]
        if sav.empty:
            continue
        for mm, st, dr, db in zip(sav["MMSI"], sav["Ship type"], sav["Draught"], sav["dup_db"]):
            s = tisztit(st)
            if s:
                tip_w[mm][s] += int(db)
                tip_1[mm][s] += 1
            if dr == dr and dr > 0:
                mer_w[mm].extend([float(dr)] * int(db))
                mer_1[mm].append(float(dr))
        pont = sav[["ts", "MMSI", "Latitude", "Longitude"]]
        gy_s[nev].append(pont)
        gy_ny[nev].append(pont.loc[pont.index.repeat(sav["dup_db"].astype(int))])
    con.close()
    return (kv.osszesit(gy_ny, tip_w, mer_w, kapuk, ts_kesz=True),
            kv.osszesit(gy_s, tip_1, mer_1, kapuk, ts_kesz=True))


def uticelok(pq: Path, atk: pd.DataFrame) -> pd.DataFrame:
    """Atkelesenkent (MMSI, ts) a hajo utolso nem ures Destination-erteke az
    atkeles elott (ASOF JOIN), es diagnosztikanak az elso utana. "Ures": a
    kikoto_feloldas.URES halmaz (UNKNOWN, NONE stb.) normalizalt alakban."""
    c = atk[["MMSI", "ts"]].drop_duplicates().copy()
    if c.empty:
        return pd.DataFrame(columns=["MMSI", "ts", "uticel", "uticel_ts",
                                     "uticel_utana", "uticel_utana_ts"])
    c["ts"] = pd.to_datetime(c["ts"]).astype("datetime64[us]")
    f = Path(pq).as_posix()
    ures = ", ".join("'" + u + "'" for u in sorted(UTICEL_URES))
    con = duckdb.connect()
    con.register("c", c)
    con.execute(f"""
        CREATE TEMP TABLE d AS
        SELECT MMSI, ts, Destination FROM read_parquet('{f}')
        WHERE Destination IS NOT NULL
          AND regexp_replace(upper(Destination), '[^A-Z0-9]', '', 'g') NOT IN ({ures})""")
    elotte = con.execute("""
        SELECT c.MMSI, c.ts, d.Destination AS uticel, d.ts AS uticel_ts
        FROM c ASOF LEFT JOIN d ON c.MMSI = d.MMSI AND c.ts >= d.ts""").df()
    utana = con.execute("""
        SELECT c.MMSI, c.ts, d.Destination AS uticel_utana, d.ts AS uticel_utana_ts
        FROM c ASOF LEFT JOIN d ON c.MMSI = d.MMSI AND c.ts <= d.ts""").df()
    con.close()
    return elotte.merge(utana, on=["MMSI", "ts"], how="outer")


def napi_tabla(atk: pd.DataFrame, kapuk: dict) -> pd.DataFrame:
    """A kapuvonal.py --napi kimenete (ugyanazok az oszlopok es szabalyok)."""
    a = atk.copy()
    a["ora"] = pd.to_datetime(a["ts"]).dt.hour
    sorok = []
    for (nap, kn, cs), g in a.groupby(["nap", "kapu", "csoport"]):
        g2 = g[g["ora"] != kv.KIHAGYOTT_ORA]
        i0, i1 = kapuk[kn].iranyok
        sorok.append({"nap": nap, "kapu": kn, "csoport": cs,
                      "atkeles": len(g), "eszakra": int((g["irany"] == i0).sum()),
                      "delre": int((g["irany"] == i1).sum()),
                      "hajo": g["MMSI"].nunique(),
                      f"atkeles_{kv.KIHAGYOTT_ORA}_ora_nelkul": len(g2)})
    return pd.DataFrame(sorok)


# --- Egy nap ---------------------------------------------------------------

def pipeline_futtat(nap: str, args) -> dict:
    parancs = [sys.executable, str(SABLONOK / "pipeline.py"), nap,
               "--tarolo", str(args.tmp), "--dr-kihagy", "--torol-zip",
               "--naplo", str(args.pipeline_naplo), "--nincs-elotoltes"]
    if args.kozvetlen_zip:
        parancs.append("--kozvetlen-zip")
    print("  $ " + " ".join(parancs[1:]))
    t0 = time.perf_counter()
    r = subprocess.run(parancs)
    fal = time.perf_counter() - t0
    n = pd.read_csv(args.pipeline_naplo, dtype={"nap": str}) if args.pipeline_naplo.exists() else None
    sor = n[n["nap"] == nap].iloc[-1].to_dict() if n is not None and (n["nap"] == nap).any() else {}
    sor["_kilepes"] = r.returncode
    sor["_fal_mp"] = fal
    return sor


def utofeldolgozas(nap: str, pq: Path, args, kapuk_m, kapuk_d, foly_m, foly_d) -> dict:
    ki = {}
    # 1. fo valtozat: a ket monitorkapu (kapuvonal.py logikaja, valtozatlanul)
    atk_m, osszes = kv.feldolgoz_parquet(pq, foly_m, kapuk_m)
    # 2. Drogden: kulon hivas
    atk_d, _ = kv.feldolgoz_parquet(pq, foly_d, kapuk_d)
    # 3. duplikatum-valtozatok a monitorkapukon
    atk_ny, atk_s = valtozatok(pq, kapuk_m, foly_m)

    h = mg.napi_hajoadat(pq)
    for alk, atk in [("monitor", atk_m), ("monitor_drogden", atk_d),
                     ("monitor_nyers", atk_ny), ("monitor_sulyozatlan", atk_s)]:
        (HORMUZ / alk).mkdir(parents=True, exist_ok=True)
        mg.napi_frissites(nap, pq, atk, HORMUZ / alk, h=h)

    for fajl, atk in [("atkelesek.csv", atk_m), ("atkelesek_drogden.csv", atk_d),
                      ("atkelesek_nyers.csv", atk_ny), ("atkelesek_sulyozatlan.csv", atk_s)]:
        hozzafuz(HORMUZ / fajl, atk_formaz(atk, nap), nap)
    osszes_atk = pd.read_csv(HORMUZ / "atkelesek.csv", dtype={"nap": str})
    napi_tabla(osszes_atk, kapuk_m).to_csv(HORMUZ / "napi.csv", index=False, encoding="utf-8")

    # 5. uticel (minden valtozat atkeleseire; a kulcs MMSI + ts)
    egyutt = pd.concat([a for a in (atk_m, atk_d, atk_ny, atk_s) if not a.empty])
    egyutt = egyutt[egyutt["csoport"].isin(mg.CSOPORTOK)]
    u = uticelok(pq, egyutt)
    u.insert(0, "nap", nap)
    hozzafuz(HORMUZ / "uticel.csv", u, nap)

    # 6. szurt Parquet
    cel = szurt_ut(args.szurt, nap)
    cel.parent.mkdir(parents=True, exist_ok=True)
    tmp = cel.with_suffix(".parquet.tmp")
    f = Path(pq).as_posix()
    tip = ", ".join(f"'{t}'" for t in SZURT_TIPUSOK)
    con = duckdb.connect()
    con.execute(f"""COPY (SELECT * FROM read_parquet('{f}') WHERE "Ship type" IN ({tip}))
                    TO '{tmp.as_posix()}' (FORMAT parquet, COMPRESSION zstd)""")
    forras_n = con.execute(f"""SELECT count(*), sum(dup_db) FROM read_parquet('{f}')
                               WHERE "Ship type" IN ({tip})""").fetchone()
    cel_n = con.execute(f"SELECT count(*), sum(dup_db) FROM read_parquet('{tmp.as_posix()}')").fetchone()
    con.close()
    if tuple(forras_n) != tuple(cel_n):
        raise RuntimeError(f"szurt Parquet sorszam elter: {forras_n} != {cel_n}")
    tmp.replace(cel)

    tank = lambda a: int(((a["csoport"] == "Tanker")).sum()) if not a.empty else 0
    ki.update({
        "nyers_sor_kapuvonal": int(osszes),
        "atkeles_monitor": len(atk_m), "tanker_monitor": tank(atk_m),
        "atkeles_drogden": len(atk_d), "tanker_drogden": tank(atk_d),
        "atkeles_nyers": len(atk_ny), "atkeles_sulyozatlan": len(atk_s),
        "uticel_elotte_van": int(u["uticel"].notna().sum()), "uticel_atkeles": len(u),
        "szurt_sor": int(cel_n[0]), "szurt_mib": round(cel.stat().st_size / 1_048_576, 1),
    })
    print(f"  kapuk: monitor {len(atk_m)} atkeles ({ki['tanker_monitor']} tanker), "
          f"Drogden {len(atk_d)} ({ki['tanker_drogden']} tanker), nyers {len(atk_ny)}, "
          f"sulyozatlan {len(atk_s)}")
    print(f"  uticel az atkeles elott: {ki['uticel_elotte_van']}/{len(u)}")
    print(f"  szurt Parquet: {ki['szurt_sor']:,} sor, {ki['szurt_mib']} MiB -> {cel}")
    return ki


def szurt_ut(gyoker: Path, nap: str) -> Path:
    return gyoker / f"ev={nap[:4]}" / f"ho={nap[5:7]}" / f"aisdk-{nap}.parquet"


def egy_nap(nap: str, abl: str, args, kiserlet: int, kapuk_m, kapuk_d, foly_m, foly_d) -> dict:
    sor = {"nap": nap, "ablak": abl, "statusz": "hiba", "kiserlet": kiserlet, "hiba": "",
           "feldolgozva": datetime.now().isoformat(timespec="seconds")}
    t_nap = time.perf_counter()
    with LemezMero() as lm:
        p = pipeline_futtat(nap, args)
        sor.update({"zip_mib": p.get("zip_mib"), "zip_sor": p.get("zip_sor"),
                    "nyers_sor": p.get("nyers_sor"), "dedup_sor": p.get("dedup_sor"),
                    "parquet_mib": p.get("parquet_mib"), "letoltes_mp": p.get("letoltes_mp"),
                    "pipeline_mp": round(p["_fal_mp"], 1),
                    "pipeline_csucs_lemez_mib": p.get("csucs_lemez_mib")})
        pq = args.tmp / f"ev={nap[:4]}" / f"ho={nap[5:7]}" / f"aisdk-{nap}.parquet"
        pst = p.get("statusz")
        if pst != "validalt" or not pq.exists():
            sor["statusz"] = pst if pst in ("nincs_adat", "hiba") else "hiba"
            sor["hiba"] = str(p.get("hiba", "") or f"pipeline kilepes {p['_kilepes']}")[:300]
        else:
            # validalas meg egyszer, a kesz fajlbol (feladat 3.2)
            con = duckdb.connect()
            s, n = con.execute(f"SELECT sum(dup_db), count(*) FROM read_parquet('{pq.as_posix()}')").fetchone()
            con.close()
            if int(s) != int(p["zip_sor"]) or int(n) != int(p["dedup_sor"]):
                sor["statusz"] = "nem_validalt"
                sor["hiba"] = f"SUM(dup_db)={s} / ZIP-sor={p['zip_sor']}, count={n} / dedup={p['dedup_sor']}"
            else:
                sor["validalas"] = f"SUM(dup_db)={int(s)} = ZIP-sor"
                print(f"  validalas (visszaolvasva): SUM(dup_db) = {int(s):,} = ZIP-sorszam")
                t0 = time.perf_counter()
                try:
                    sor.update(utofeldolgozas(nap, pq, args, kapuk_m, kapuk_d, foly_m, foly_d))
                    sor["utofeldolgozas_mp"] = round(time.perf_counter() - t0, 1)
                    pq.unlink()
                    sor["statusz"] = "kesz"
                except Exception as e:  # technikai hiba: a teljes Parquet megmarad az ujraprobahoz
                    sor["hiba"] = f"utofeldolgozas: {type(e).__name__}: {e}"[:300]
                    print(f"  HIBA: {sor['hiba']}")
    sor["nap_mp"] = round(time.perf_counter() - t_nap, 1)
    sor["csucs_lemez_gb"] = round(lm.csucs_gb, 2)
    sor["szabad_gb_utana"] = round(szabad_gb(), 2)
    return sor


# --- Osszesito ---------------------------------------------------------------

def osszesito(minta: pd.DataFrame):
    a = allapot_olvas()
    m = minta.merge(a[["nap", "statusz"]], on="nap", how="left")
    m["statusz"] = m["statusz"].fillna("nincs_elkezdve")
    print("\nOsszesito ablakonkent:")
    for nev in ABLAKOK:
        g = m[m.ablak == nev]
        kesz = (g.statusz == "kesz").sum()
        print(f"  {nev}: {kesz}/{len(g)} kesz")
        for _, r in g[g.statusz != "kesz"].iterrows():
            print(f"      hianyzik: {r.nap} ({r.statusz})")
    if len(a):
        k = a[a.statusz == "kesz"]
        if len(k):
            print(f"  szurt Parquet osszesen: {k['szurt_mib'].sum():,.1f} MiB ({len(k)} nap)")
    return m


# --- Fovonal -----------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--minta", type=Path, default=MINTA)
    ap.add_argument("--napok", nargs="*", help="Csak ezek a napok (a mintabol)")
    ap.add_argument("--elso", type=int, help="Csak a minta elso N napja")
    ap.add_argument("--tmp", type=Path, default=TMP_TAROLO)
    ap.add_argument("--szurt", type=Path, default=SZURT_TAROLO)
    ap.add_argument("--pipeline-naplo", type=Path, default=PIPELINE_NAPLO)
    ap.add_argument("--min-szabad-gb", type=float, default=MIN_SZABAD_GB)
    ap.add_argument("--kozvetlen-zip", action="store_true",
                    help="pipeline.py --kozvetlen-zip: a CSV-t nem csomagolja ki (kisebb "
                         "atmeneti lemezcsucs; az eles napi futas is igy fut)")
    ap.add_argument("--osszesito", action="store_true", help="Csak az allapot kiirasa")
    args = ap.parse_args()

    minta = pd.read_csv(args.minta, dtype={"nap": str})
    if args.osszesito:
        osszesito(minta)
        return 0
    napok = minta
    if args.napok:
        napok = minta[minta.nap.isin(args.napok)]
    if args.elso:
        napok = napok.head(args.elso)

    kapuk = {k.nev: k for k in kv.betolt()}
    kapuk_m = {n: k for n, k in kapuk.items() if k.monitor}
    kapuk_d = {DROGDEN: kapuk[DROGDEN]}
    foly_m = {n: kv.folyoso(k) for n, k in kapuk_m.items()}
    foly_d = {n: kv.folyoso(k) for n, k in kapuk_d.items()}

    HORMUZ.mkdir(parents=True, exist_ok=True)
    allapot = allapot_olvas()
    print(f"Mintanapok: {len(napok)}; szabad hely: {szabad_gb():.2f} GB")
    leallt = False
    for i, r in enumerate(napok.itertuples()):
        a = allapot[allapot.nap == r.nap]
        elozo = a.iloc[-1].to_dict() if len(a) else {}
        if elozo.get("statusz") == "kesz":
            continue
        kiserlet = int(elozo.get("kiserlet", 0) or 0) + 1
        if kiserlet > MAX_KISERLET:
            print(f"\n{r.nap}: {MAX_KISERLET} sikertelen kiserlet utan kihagyva ({elozo.get('statusz')})")
            continue
        sz = szabad_gb()
        # a nap kozbeni csucs (letoltes + DuckDB-lapozas) is maradjon a hatar folott:
        # becsles = az utolso 5 kesz nap legnagyobb mert csucsa
        cs = (allapot[allapot.statusz == "kesz"]["csucs_lemez_gb"].tail(5).max()
              if "csucs_lemez_gb" in allapot and (allapot.statusz == "kesz").any() else 0.0)
        if sz - cs < args.min_szabad_gb:
            print(f"\nALLJ: szabad hely {sz:.2f} GB, varhato csucs {cs:.2f} GB -> "
                  f"a nap kozben {args.min_szabad_gb} GB ala esne ({r.nap} elott)")
            leallt = True
            break
        print(f"\n=== {r.nap} ({r.ablak}, {i + 1}/{len(napok)}, {kiserlet}. kiserlet) "
              f"szabad: {sz:.2f} GB ===")
        sor = egy_nap(r.nap, r.ablak, args, kiserlet, kapuk_m, kapuk_d, foly_m, foly_d)
        allapot_ir(sor)
        allapot = allapot_olvas()
        print(f"  -> {sor['statusz']}, {sor['nap_mp']} mp (letoltes {sor.get('letoltes_mp')} mp, "
              f"pipeline {sor.get('pipeline_mp')} mp, utofeldolgozas {sor.get('utofeldolgozas_mp')} mp), "
              f"csucs lemez {sor['csucs_lemez_gb']} GB, szabad utana {sor['szabad_gb_utana']} GB")
        if sor["szabad_gb_utana"] < args.min_szabad_gb:
            print(f"ALLJ: szabad hely {sor['szabad_gb_utana']} GB < {args.min_szabad_gb} GB")
            leallt = True
            break

    osszesito(minta)
    return 3 if leallt else 0


if __name__ == "__main__":
    sys.exit(main())
