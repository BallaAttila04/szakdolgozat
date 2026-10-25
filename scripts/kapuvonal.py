"""
Kapuvonal-metrika: hany hajo kel at tenylegesen a dan szorosokon.

Az eddigi forgalmi mutato (orankenti egyedi hajoszam a teljes teruleten) a
szabadidos hajozast merte, amelyre egy csatornalezarasnak nincs hatasa. Ez a
szkript azt szamolja, amit egy kereskedelmi utvonal-valtozas tenylegesen
erint: hany hajo haladt at a szoros keresztmetszeten, milyen iranyban, es
milyen tipusu.

Modszer:
  1. Kapuvonal: egy szakasz a szoroson keresztben, parttol partig (a ket
     vegpont szarazfoldon). A kapukat a scripts/kapuk.json adja meg (ld.
     ott); uj kapuhoz nem kell kodot modositani. Ket megadasi mod van:
     szelessegi kor (a ket eredeti kapu), vagy tetszoleges ket vegpont.
     A vonalak hosszat az adatbol ellenoriztuk: a savban levo osszes pozicio
     a vonalon belul esik (ld. naplo).
  2. H3-folyoso: a vonal menti 8-as felbontasu cellak es ket cellanyi
     kornyezetuk (kb. 2 km mindket oldalon). Csak az ide eso poziciokat
     vizsgaljuk - a H3 itt indexkent szerepel.
  3. Atkeles: egy hajo ket egymast koveto (folyosobeli) pozicioja a szakasz
     egyenesenek ket oldalan van, mindketto a szakasz hatarai kozott
     (a szakaszra eso meroleges vetuletuk a ket vegpont koze esik), es a
     ketto kozott legfeljebb MAX_RES_MP telt el. Az irany az oldalvaltasbol
     adodik: a kapu "iranyok" parjanak elso neve, ha a hajo az a->b iranyhoz
     kepest bal oldalra lep at, a masodik, ha jobbra. Szelessegi kornel ez
     pontosan a regi szabaly (eszak = kifele a Balti-tengerbol), ld. naplo,
     2026-10-12.

Kimenet:
  outputs/kapuvonal_atkelesek.csv  - atkelesenkent egy sor
  outputs/kapuvonal_napi.csv       - naponkent, kapunkent, tipusonkent

Bemenet lehet a napi ZIP, vagy a pipeline.py altal irt Parquet-tarolo napi
fajlja (a ketto ugyanazt az eredmenyt adja, ld. naplo, 2. fazis).

Hasznalat:
    python kapuvonal.py data/aisdk-2026-07-15.zip
    python kapuvonal.py data/aisdk-2026-07-15.zip --kapuk mas_kapuk.json --minden-kapu
    python kapuvonal.py data/aisdk-2026-07-*.zip data/aisdk-2026-09-05.zip
    python kapuvonal.py "outputs/tarolo/ev=2026/ho=07/*.parquet"
"""

import argparse
import csv
import glob
import json
import math
import sys
import zipfile
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path

import h3
import numpy as np
import pandas as pd

from utak import KIMENET, SABLONOK
from hajo_statisztika import csoport, tisztit

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except AttributeError:
    pass

# --- Parameterek ----------------------------------------------------------

# A kapuk konfiguracioja (nev, vegpontok, iranynevek, monitor, indoklas).
# A ket monitorozott kapu (Nagy-Balti-ov, Oresund) indoklasa is ott van.
KAPU_KONFIG = SABLONOK / "kapuk.json"

H3_FELBONTAS = 8          # ~0,74 km2/cella
FOLYOSO_K = 2             # a vonal menti cellak ket gyurunyi kornyezete

# Ket egymast koveto pozicio kozott legfeljebb ennyi ido telhet el. Hosszabb
# vetelkieses felett nem tudjuk, mi tortent kozben, ezert nem szamolunk
# atkelest. 10 perc: a lassu Class B hajok 3 perces adaskozenel bovebb.
MAX_RES_MP = 600

# Az elozetes bbox-szures felszelessege a vonalra merolegesen, szelessegi
# fokban (0,04 fok ~ 4,4 km). Szelesebb a H3-folyosonal (k=2 a 8-as
# felbontason legfeljebb ~2,5 km), igy csak gyorsit, a folyosobol nem szur ki
# semmit. Szelessegi kornel ez pontosan a regi lat +/- 0,04 sav.
SAV_FOK = 0.04

CHUNK = 500_000
TS = "# Timestamp"
OSZLOPOK = {TS, "MMSI", "Latitude", "Longitude", "Ship type", "Draught"}

# A 2026-07-08-i 11. ora adathianyos (ld. szamok.md), ezert az
# osszehasonlitasokhoz ezt az orat minden naprol kihagyjuk.
KIHAGYOTT_ORA = 11


# --- Kapuk -----------------------------------------------------------------

@dataclass(frozen=True)
class Kapu:
    """Egy kapuvonal: az a -> b szakasz, (lat, lon) vegpontokkal."""
    nev: str
    a: tuple
    b: tuple
    iranyok: tuple = ("észak", "dél")   # (balra atlepes, jobbra atlepes)
    monitor: bool = False
    indoklas: str = ""
    kifele: str = ""                    # melyik iranynev jelenti: ki a Balti-tengerbol

    @property
    def szelessegi(self) -> bool:
        return self.a[0] == self.b[0] and self.a[1] < self.b[1]

    @property
    def ertek(self) -> tuple:
        """A KAPUK szotarbeli alak: szelessegi kornel (lat, lon0, lon1),
        kulonben (lat_a, lon_a, lat_b, lon_b)."""
        if self.szelessegi:
            return (self.a[0], self.a[1], self.b[1])
        return (*self.a, *self.b)

    @property
    def forditott(self) -> bool:
        """A szamitas mindig a kanonikus iranyu szakaszon fut (nyugati vegtol a
        keleti fele; azonos hosszusagnal delrol eszakra). Ha a konfigban a
        vegpontok forditva allnak, csak az iranynevek cserelodnek - igy a
        vonalon fekvo pont besorolasa (mindig a kanonikus bal oldal, pl.
        szelessegi kornel eszak) nem fugg a megadas sorrendjetol."""
        return (self.a[1], self.a[0]) > (self.b[1], self.b[0])

    @property
    def _vegek(self):
        return (self.b, self.a) if self.forditott else (self.a, self.b)

    def _sik(self):
        """Sikbeli kozelites: x = lon * cos(kozepso szelesseg), y = lat
        (a kapuk nehany tiz km hosszuak, a torzitas elhanyagolhato).
        Visszaad: (cos, dx, dy) - a kanonikus a -> b vektor."""
        a, b = self._vegek
        c = math.cos(math.radians((a[0] + b[0]) / 2))
        return c, (b[1] - a[1]) * c, b[0] - a[0]

    def bbox(self):
        """(lat_min, lat_max, lon_min, lon_max): a szakasz befoglalo teglalapja,
        a vonalra merolegesen SAV_FOK-kal kibovitve. Szelessegi kornel ez
        lat +/- SAV_FOK es lon0..lon1, azaz a regi szures."""
        c, dx, dy = self._sik()
        hossz = math.hypot(dx, dy)
        p_lat = SAV_FOK * abs(dx) / hossz
        p_lon = SAV_FOK * abs(dy) / hossz / c
        return (min(self.a[0], self.b[0]) - p_lat, max(self.a[0], self.b[0]) + p_lat,
                min(self.a[1], self.b[1]) - p_lon, max(self.a[1], self.b[1]) + p_lon)

    def oldal_es_bent(self, lat, lon):
        """Poziciokent: (1) a konfigbeli a -> b iranyhoz kepest bal oldalon
        van-e - a vonalra eso pont a kanonikus bal oldalhoz szamit (szelessegi
        kornel az eszakihoz, ahogy a regi kodban); (2) a szakasz hatarai kozott
        van-e (a vetulet parametere 0 es 1 koze esik)."""
        c, dx, dy = self._sik()
        a = self._vegek[0]
        px = (np.asarray(lon, dtype=float) - a[1]) * c
        py = np.asarray(lat, dtype=float) - a[0]
        bal = (dx * py - dy * px) >= 0
        t = (px * dx + py * dy) / (dx * dx + dy * dy)
        return (~bal if self.forditott else bal), (t >= 0) & (t <= 1)


def kapu_szotarbol(k: dict) -> Kapu:
    if "szelesseg" in k:
        lo0, lo1 = k["hosszusag"]
        if not lo0 < lo1:
            raise ValueError(f"{k['nev']}: a hosszusag [nyugati, keleti] sorrendu legyen")
        a, b = (float(k["szelesseg"]), float(lo0)), (float(k["szelesseg"]), float(lo1))
    else:
        a, b = tuple(map(float, k["a"])), tuple(map(float, k["b"]))
    iranyok = tuple(k.get("iranyok", ("észak", "dél")))
    if len(iranyok) != 2 or a == b:
        raise ValueError(f"{k['nev']}: ket iranynev es ket kulonbozo vegpont kell")
    kifele = k.get("kifele", "")
    if kifele and kifele not in iranyok:
        raise ValueError(f"{k['nev']}: a kifele ({kifele}) nem az iranyok egyike")
    return Kapu(k["nev"], a, b, iranyok, bool(k.get("monitor", False)),
                k.get("indoklas", ""), kifele)


def betolt(ut=None) -> list:
    """A konfiguracios fajl kapui, a fajlbeli sorrendben."""
    ut = Path(ut or KAPU_KONFIG)
    adat = json.loads(ut.read_text(encoding="utf-8"))
    kapuk = [kapu_szotarbol(k) for k in adat["kapuk"]]
    nevek = [k.nev for k in kapuk]
    if len(set(nevek)) != len(nevek):
        raise ValueError(f"{ut}: ismetlodo kapunev")
    return kapuk


KAPU_LISTA = betolt()
KAPU_DEF = {k.nev: k for k in KAPU_LISTA}
# A monitor altal figyelt kapuk. A monitor.py (es mas importalok) ezt
# hasznaljak; nevek, sorrend es ertekek a korabbi, kodba irt szotarral
# azonosak: {"Nagy-Balti-öv": (55.40, 10.60, 11.35), "Øresund": (56.07, 12.40, 12.85)}.
KAPUK = {k.nev: k.ertek for k in KAPU_LISTA if k.monitor}


def kapu(nev, v=None) -> Kapu:
    """Kapu objektum a nevbol es/vagy a KAPUK-beli tuple-bol."""
    if isinstance(v, Kapu):
        return v
    if v is None or (nev in KAPU_DEF and KAPU_DEF[nev].ertek == tuple(v)):
        return KAPU_DEF[nev]
    if len(v) == 3:
        return Kapu(nev, (v[0], v[1]), (v[0], v[2]))
    return Kapu(nev, (v[0], v[1]), (v[2], v[3]), ("bal", "jobb"))


def folyoso(*v):
    """H3-folyoso: folyoso(lat, lon0, lon1), folyoso(lat_a, lon_a, lat_b, lon_b)
    vagy folyoso(Kapu)."""
    k = v[0] if len(v) == 1 else kapu("", v)
    va, vb = k._vegek
    a = h3.latlng_to_cell(*va, H3_FELBONTAS)
    b = h3.latlng_to_cell(*vb, H3_FELBONTAS)
    ut = h3.grid_path_cells(a, b)
    cellak = set()
    for c in ut:
        cellak.update(h3.grid_disk(c, FOLYOSO_K))
    return {h3.str_to_int(c) for c in cellak}


def atkelesek(df, k):
    """df: egy kapu folyosojaba eso poziciok (MMSI, ts, Latitude, Longitude).
    k: Kapu, vagy (visszafele kompatibilisen) egy szelesseg - ekkor a teljes
    szelessegi kor, eszak/del iranynevekkel."""
    if not isinstance(k, Kapu):
        k = Kapu("", (float(k), -180.0), (float(k), 180.0))
    df = df.sort_values(["MMSI", "ts"], kind="stable")
    m = df["MMSI"].to_numpy()
    t = df["ts"].to_numpy().astype("datetime64[s]").astype(np.int64)
    bal, bent = k.oldal_es_bent(df["Latitude"].to_numpy(), df["Longitude"].to_numpy())
    ugyanaz = m[1:] == m[:-1]
    dt = t[1:] - t[:-1]
    balra = ~bal[:-1] & bal[1:]
    jobbra = bal[:-1] & ~bal[1:]
    jo = ugyanaz & (dt <= MAX_RES_MP) & (balra | jobbra) & bent[:-1] & bent[1:]
    idx = np.flatnonzero(jo) + 1
    return pd.DataFrame({
        "MMSI": m[idx],
        "ts": df["ts"].to_numpy()[idx],
        "irany": np.where(balra[idx - 1], k.iranyok[0], k.iranyok[1]),
    })


def _kapuk(kapuk):
    """None -> a monitorozott kapuk; szotar (nev -> Kapu vagy tuple) -> Kapu-k."""
    kapuk = KAPUK if kapuk is None else kapuk
    return {n: kapu(n, v) for n, v in kapuk.items()}


def feldolgoz(zip_ut, folyosok, kapuk=None):
    """Egy nap atkelesei a megadott kapukon (alapbol a monitorozottakon).

    A tipus-szavazas es a merules-median a hivasban szereplo OSSZES kapu
    folyosojanak pozicioin tortenik (igy volt eddig is), ezert ha a monitor
    kapuival azonos eredmeny kell, a tobbi kaput kulon hivasban kell szamolni.
    """
    kapuk = _kapuk(kapuk)
    if Path(zip_ut).suffix == ".parquet":
        return feldolgoz_parquet(zip_ut, folyosok, kapuk)
    gyujto = {k: [] for k in kapuk}
    tipus = defaultdict(Counter)
    merules = defaultdict(list)
    osszes = 0
    with zipfile.ZipFile(zip_ut) as zf:
        tag = [n for n in zf.namelist() if n.lower().endswith((".csv", ".txt"))][0]
        with zf.open(tag) as raw:
            for ch in pd.read_csv(raw, usecols=lambda c: c.strip() in OSZLOPOK,
                                  chunksize=CHUNK, low_memory=False,
                                  encoding="utf-8-sig"):
                ch.columns = [c.strip() for c in ch.columns]
                osszes += len(ch)
                for nev, k in kapuk.items():
                    la0, la1, lo0, lo1 = k.bbox()
                    sav = ch[ch["Latitude"].between(la0, la1)
                             & ch["Longitude"].between(lo0, lo1)]
                    if sav.empty:
                        continue
                    cella = np.fromiter(
                        (h3.str_to_int(h3.latlng_to_cell(a, b, H3_FELBONTAS))
                         for a, b in zip(sav["Latitude"], sav["Longitude"])),
                        dtype=np.int64, count=len(sav))
                    sav = sav[np.isin(cella, list(folyosok[nev]))]
                    if sav.empty:
                        continue
                    for mm, st, dr in zip(sav["MMSI"], sav["Ship type"], sav["Draught"]):
                        s = tisztit(st)
                        if s:
                            tipus[mm][s] += 1
                        if dr == dr and dr > 0:
                            merules[mm].append(float(dr))
                    gyujto[nev].append(sav[[TS, "MMSI", "Latitude", "Longitude"]])
                print(f"  {osszes:>12,} sor", end="\r")
    print(f"  {osszes:>12,} sor beolvasva")
    return osszesit(gyujto, tipus, merules, kapuk), osszes


def feldolgoz_parquet(pq_ut, folyosok, kapuk=None):
    """Ugyanaz, mint a feldolgoz(), a pipeline.py Parquet-tarolojabol.

    A tarolo deduplikalt: a bitre azonos sorokbol egy maradt, a `dup_db`
    oszlop mondja meg, hany volt belole. A tipus-szavazas es a merules-median
    a nyers sorokon tortent, ezert itt `dup_db`-vel sulyozunk; az atkeles-
    felismeres a deduplikalt pontokon fut (egy pont ismetlese nem atkeles).
    A H3-folyosot a tarolt `h3` oszlop adja, nem kell ujraszamolni.
    Az azonos masodpercu sorok forrasbeli sorrendjet a `sorrend` oszlop orzi;
    enelkul hamis oda-vissza atkelesek keletkeznek (ld. naplo, 2. fazis).
    """
    import duckdb
    kapuk = _kapuk(kapuk)
    gyujto = {k: [] for k in kapuk}
    tipus = defaultdict(Counter)
    merules = defaultdict(list)
    con = duckdb.connect()
    f = Path(pq_ut).as_posix()
    osszes = con.execute(f"SELECT sum(dup_db) FROM read_parquet('{f}')").fetchone()[0]
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
                tipus[mm][s] += int(db)
            if dr == dr and dr > 0:
                merules[mm].extend([float(dr)] * int(db))
        gyujto[nev].append(sav[["ts", "MMSI", "Latitude", "Longitude"]])
    con.close()
    print(f"  {osszes:>12,} nyers sor a Parquetben")
    return osszesit(gyujto, tipus, merules, kapuk, ts_kesz=True), osszes


def osszesit(gyujto, tipus, merules, kapuk=None, ts_kesz=False):
    kapuk = _kapuk(kapuk)
    ki = []
    for nev, darabok in gyujto.items():
        if not darabok:
            continue
        df = pd.concat(darabok, ignore_index=True)
        if not ts_kesz:
            df["ts"] = pd.to_datetime(df[TS], format="%d/%m/%Y %H:%M:%S", errors="coerce")
        df = df.dropna(subset=["ts"])
        a = atkelesek(df, kapuk[nev])
        a["kapu"] = nev
        a["folyoso_pozicio"] = len(df)
        ki.append(a)
    atk = pd.concat(ki, ignore_index=True) if ki else pd.DataFrame()
    atk["csoport"] = [csoport(tipus[m].most_common(1)[0][0]) if tipus[m] else "Egyéb / ismeretlen"
                      for m in atk["MMSI"]]
    atk["merules_m"] = [round(float(np.median(merules[m])), 1) if merules[m] else None
                        for m in atk["MMSI"]]
    return atk


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("zipek", nargs="+")
    ap.add_argument("--atkelesek", default=KIMENET / "kapuvonal_atkelesek.csv")
    ap.add_argument("--napi", default=KIMENET / "kapuvonal_napi.csv")
    ap.add_argument("--kapuk", type=Path, default=KAPU_KONFIG,
                    help="Kapu-konfiguracio (JSON, ld. scripts/kapuk.json)")
    ap.add_argument("--minden-kapu", action="store_true",
                    help="A konfiguracio minden kapuja, nem csak a monitor: true-k")
    args = ap.parse_args()

    kapuk = {k.nev: k for k in betolt(args.kapuk) if k.monitor or args.minden_kapu}
    if not kapuk:
        sys.exit(f"Nincs kapu: {args.kapuk}")
    folyosok = {n: folyoso(k) for n, k in kapuk.items()}
    for n, c in folyosok.items():
        k = kapuk[n]
        print(f"Kapu: {n:<14} {k.a} -> {k.b}, H3-folyoso: {len(c)} cella")

    # a PowerShell nem bontja ki a *-ot, ezert itt tesszuk meg
    bemenetek = []
    for z in args.zipek:
        bemenetek += sorted(glob.glob(z)) if any(c in z for c in "*?[") else [z]

    minden = []
    for z in bemenetek:
        p = Path(z)
        if not p.exists():
            sys.exit(f"Nem letezik: {p}")
        nap = p.stem.replace("aisdk-", "")
        print(f"\n{nap}:")
        atk, _ = feldolgoz(p, folyosok, kapuk)
        atk["nap"] = nap
        minden.append(atk)
        for nev, kp in kapuk.items():
            k = atk[atk["kapu"] == nev] if not atk.empty else atk
            if k.empty:
                print(f"  {nev:<14} 0 atkeles")
                continue
            ker = k[k["csoport"].isin(["Teherhajó", "Tanker"])]
            i0, i1 = kp.iranyok
            print(f"  {nev:<14} {len(k):>5} atkeles, {k['MMSI'].nunique():>4} hajo | "
                  f"tanker {int((k['csoport']=='Tanker').sum()):>3}, "
                  f"teherhajo {int((k['csoport']=='Teherhajó').sum()):>3}, "
                  f"kereskedelmi {i0}/{i1} {int((ker['irany']==i0).sum())}/"
                  f"{int((ker['irany']==i1).sum())}")

    osszes = pd.concat(minden, ignore_index=True)
    osszes = osszes[["nap", "kapu", "ts", "MMSI", "irany", "csoport", "merules_m"]]
    osszes.to_csv(args.atkelesek, index=False, encoding="utf-8")

    osszes["ora"] = pd.to_datetime(osszes["ts"]).dt.hour
    sorok = []
    for (nap, kn, cs), g in osszes.groupby(["nap", "kapu", "csoport"]):
        g2 = g[g["ora"] != KIHAGYOTT_ORA]
        # eszakra/delre: a kapu ket iranya (szelessegi kornel eszak/del;
        # altalanos szakasznal a konfig "iranyok" parja, ugyanebben a sorrendben)
        i0, i1 = kapuk[kn].iranyok
        sorok.append({"nap": nap, "kapu": kn, "csoport": cs,
                      "atkeles": len(g), "eszakra": int((g["irany"] == i0).sum()),
                      "delre": int((g["irany"] == i1).sum()),
                      "hajo": g["MMSI"].nunique(),
                      f"atkeles_{KIHAGYOTT_ORA}_ora_nelkul": len(g2)})
    with Path(args.napi).open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(sorok[0].keys()))
        w.writeheader()
        w.writerows(sorok)
    print(f"\n-> {args.atkelesek} ({len(osszes):,} atkeles)")
    print(f"-> {args.napi}")


if __name__ == "__main__":
    main()
