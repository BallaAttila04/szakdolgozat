"""
Hajotipus- es tevekenyseg-statisztika a napi AIS fajlbol.

Ket kerdesre valaszol:
  1. MILYEN hajok vannak a vizen (Ship type)
  2. MIT CSINALNAK ott (Navigational status), tipusonkent lebontva

Plusz orankenti volumen (uzenet + egyedi hajo), tipusonkent is - ebbol keszul
a weboldal forgalmi chartja.

FONTOS - ket kulonbozo mertekegyseg, es nem keverendok:
  - hajoszam: hany kulonbozo MMSI. Ez a valos "hany hajo".
  - uzenetszam: hany AIS sor. Ezt nehany folyamatosan sugarzo hajo (kompok)
    eluralja, ezert a tipusok megoszlasat ELTORZITJA. A weboldalon ezert a
    hajoszam a vezeto szam, az uzenetszam csak masodlagos.

A statikus mezok (Ship type) hajonkent tobbfele erteket is felvehetnek, mert
kezzel allitottak. Itt hajonkent a leggyakrabban jelentett erteket vesszuk,
es kulon szamoljuk, hany hajonal volt egyaltalan ellentmondas.

Hasznalat:
    python hajo_statisztika.py data/aisdk-2026-07-15.zip
    python hajo_statisztika.py <zip> --teljes-fajl --ki stat.json
"""

import argparse
import csv
import json
import sys
import zipfile
from collections import Counter, defaultdict
from pathlib import Path

import pandas as pd

from utak import KIMENET

# A Windows-konzol kodlapja nem birja a magyar ekezeteket sem mindig; a
# fajlkimenet utf-8, a konzolra csak a megjelenitest puhitjuk.
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except AttributeError:
    pass

LAT_MIN, LAT_MAX = 54.5, 56.5
LON_MIN, LON_MAX = 10.0, 13.0

CHUNK = 500_000

TS_OSZLOP = "# Timestamp"
COLS = {TS_OSZLOP, "MMSI", "Latitude", "Longitude",
        "Ship type", "Navigational status", "Type of mobile"}

# A Type of mobile nem hajotipus, hanem AIS-adotipus. Ezek NEM hajok, de
# benne vannak a napi fajlban es az egyedi MMSI-szamban: navigacios jelzok
# (AtoN = Aid to Navigation, pl. boja), parti bazisallomasok, mento-jeladok.
NEM_HAJO = {"AtoN", "Base Station", "Search and Rescue Transponder"}

# Ezeket "nincs adat"-kent kezeljuk
URES = {"", "UNKNOWN", "UNDEFINED", "NAN", "NONE", "N/A", "UNKNOWN VALUE",
        "NOT AVAILABLE", "RESERVED FOR FUTURE USE"}

# A nyers AIS hajotipusok osszevonasa hasznalati cel szerint. A terkepen
# ennyi szin fer el ugy, hogy meg megkulonboztethetok maradjanak - a
# finomabb bontas a tablazatban van meg.
#
# A sorrend szamit: az elso talalat nyer, ezert a specifikusabb minta
# elobb all. A kulcs a nyers ertek kisbetus valtozataban keresett reszlet.
CSOPORTOK = [
    ("Teherhajó",      ["cargo"]),
    ("Tanker",         ["tanker"]),
    ("Személyszállító", ["passenger"]),
    ("Halászhajó",     ["fishing"]),
    ("Kedvtelési",     ["pleasure", "sailing"]),
    ("Szolgálati",     ["tug", "pilot", "search and rescue", "law enforcement",
                        "port tender", "dredging", "military", "medical",
                        "anti-pollution", "towing", "spare", "wing in ground",
                        "high speed craft", "diving"]),
]
EGYEB = "Egyéb / ismeretlen"


def csoport(nyers: str) -> str:
    t = (nyers or "").strip().lower()
    if not t or t.upper() in URES:
        return EGYEB
    for nev, mintak in CSOPORTOK:
        for m in mintak:
            if m in t:
                return nev
    return EGYEB


def tisztit(v) -> str:
    s = str(v).strip() if v is not None else ""
    return "" if s.upper() in URES else s


def main():
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("zip_fajl")
    ap.add_argument("--teljes-fajl", action="store_true",
                    help="Ne szurjon bounding boxra (alapbol szur)")
    ap.add_argument("--ki", default=KIMENET / "hajo_statisztika.json")
    ap.add_argument("--csv", default=KIMENET / "hajo_statisztika.csv")
    args = ap.parse_args()

    path = Path(args.zip_fajl)
    if not path.exists():
        sys.exit(f"Nem letezik: {path}")

    # hajonkent: melyik tipust/statuszt hanyszor jelentette
    tipus_szavazat = defaultdict(Counter)
    statusz_szavazat = defaultdict(Counter)
    osztaly_szavazat = defaultdict(Counter)
    uzenet_hajonkent = Counter()

    # oranként
    ora_uzenet = Counter()                      # ora -> uzenet
    ora_hajok = defaultdict(set)                # ora -> {mmsi}
    ora_csoport_hajok = defaultdict(set)        # (ora, csoport) -> {mmsi}

    # a tipus a soron is rajta van, de a csoportositashoz a hajo vegleges
    # tipusa kell - ezert az oranként bontast ket menetben nem akarjuk;
    # ideiglenesen (ora, mmsi) parokat gyujtunk, a csoportot a vegen kotjuk hozza
    ora_mmsi_parok = set()

    osszes = 0
    bbox_sor = 0

    print(f"Beolvasas: {path.name}")
    with zipfile.ZipFile(path) as zf:
        tag = [n for n in zf.namelist() if n.lower().endswith((".csv", ".txt"))][0]
        with zf.open(tag) as raw:
            olvaso = pd.read_csv(raw, usecols=lambda c: c.strip() in COLS,
                                 chunksize=CHUNK, low_memory=False,
                                 encoding="utf-8-sig")
            for ch in olvaso:
                ch.columns = [c.strip() for c in ch.columns]
                osszes += len(ch)

                if not args.teljes_fajl:
                    ch = ch[ch["Latitude"].between(LAT_MIN, LAT_MAX)
                            & ch["Longitude"].between(LON_MIN, LON_MAX)]
                if ch.empty:
                    print(f"  {osszes:>12,} sor", end="\r")
                    continue
                bbox_sor += len(ch)

                ora = pd.to_datetime(ch[TS_OSZLOP], format="%d/%m/%Y %H:%M:%S",
                                     errors="coerce").dt.hour

                for mmsi, tip, stat, osz, o in zip(ch["MMSI"].to_numpy(),
                                                   ch["Ship type"].to_numpy(),
                                                   ch["Navigational status"].to_numpy(),
                                                   ch["Type of mobile"].to_numpy(),
                                                   ora.to_numpy()):
                    uzenet_hajonkent[mmsi] += 1
                    t = tisztit(tip)
                    if t:
                        tipus_szavazat[mmsi][t] += 1
                    s = tisztit(stat)
                    if s:
                        statusz_szavazat[mmsi][s] += 1
                    a = tisztit(osz)
                    if a:
                        osztaly_szavazat[mmsi][a] += 1
                    if o == o:                      # nem NaN
                        o = int(o)
                        ora_uzenet[o] += 1
                        ora_hajok[o].add(mmsi)
                        ora_mmsi_parok.add((o, mmsi))

                print(f"  {osszes:>12,} sor", end="\r")
    print()

    hajok = set(uzenet_hajonkent)
    print(f"  {osszes:,} sor beolvasva, {bbox_sor:,} maradt szures utan "
          f"({bbox_sor/max(osszes,1)*100:.1f}%), {len(hajok):,} egyedi hajo")

    # --- Hajonkenti vegleges tipus: a leggyakrabban jelentett ertek ---
    hajo_tipus, hajo_csoport = {}, {}
    ellentmondo = 0
    nincs_tipus = 0
    for m in hajok:
        sz = tipus_szavazat.get(m)
        if not sz:
            nincs_tipus += 1
            hajo_tipus[m] = ""
            hajo_csoport[m] = EGYEB
            continue
        if len(sz) > 1:
            ellentmondo += 1
        nyertes = sz.most_common(1)[0][0]
        hajo_tipus[m] = nyertes
        hajo_csoport[m] = csoport(nyertes)

    print(f"  {nincs_tipus:,} hajo ({nincs_tipus/max(len(hajok),1)*100:.1f}%) "
          f"nem jelentett hajotipust, {ellentmondo:,} tobbfelet")

    # --- Csoportonkenti osszesites ---
    cs_hajo = Counter(hajo_csoport.values())
    cs_uzenet = Counter()
    for m, db in uzenet_hajonkent.items():
        cs_uzenet[hajo_csoport[m]] += db

    # --- Reszletes tipusbontas (a tablazathoz) ---
    tip_hajo = Counter(t if t else "(nem jelentett)" for t in hajo_tipus.values())

    # --- Tevekenyseg: statusz hajonkent (a leggyakoribb) ---
    hajo_statusz = {}
    for m in hajok:
        sz = statusz_szavazat.get(m)
        hajo_statusz[m] = sz.most_common(1)[0][0] if sz else "(nem jelentett)"
    st_hajo = Counter(hajo_statusz.values())

    # --- AIS-osztaly (Type of mobile) ---
    # Ez magyarazza meg, miert hianyzik a statusz a hajok nagy reszenel: a
    # Class B jeladok pozicio-uzenete nem tartalmaz navigacios statuszmezot.
    hajo_osztaly = {}
    for m in hajok:
        sz = osztaly_szavazat.get(m)
        hajo_osztaly[m] = sz.most_common(1)[0][0] if sz else "(ismeretlen)"
    osztaly_db = Counter(hajo_osztaly.values())

    # Osztalyonkent: hany hajo jelentett egyaltalan ervenyes statuszt
    osztaly_statusz = {}
    for oszt in osztaly_db:
        tagok = [m for m in hajok if hajo_osztaly[m] == oszt]
        van = sum(1 for m in tagok if statusz_szavazat.get(m))
        osztaly_statusz[oszt] = {"hajo": len(tagok), "statusszal": van}

    nem_hajo_db = sum(d for o, d in osztaly_db.items() if o in NEM_HAJO)

    # Class A hajok statuszeloszlasa - csak nekik ertelmes
    class_a = [m for m in hajok if hajo_osztaly[m] == "Class A"]
    st_class_a = Counter(hajo_statusz[m] for m in class_a)

    # --- Kereszttabla: csoport x statusz (hajoszamban) ---
    kereszt = defaultdict(Counter)
    for m in hajok:
        kereszt[hajo_csoport[m]][hajo_statusz[m]] += 1

    # --- Oranként, csoportonkent ---
    for o, m in ora_mmsi_parok:
        ora_csoport_hajok[(o, hajo_csoport[m])].add(m)

    sorrend = [nev for nev, _ in CSOPORTOK] + [EGYEB]
    orank = []
    for o in range(24):
        sor = {"ora": o,
               "uzenet": ora_uzenet.get(o, 0),
               "hajo": len(ora_hajok.get(o, ()))}
        for cs in sorrend:
            sor[cs] = len(ora_csoport_hajok.get((o, cs), ()))
        orank.append(sor)

    # --- Kiiras ---
    print("\n  Hajotipus-csoportok (hajoszam szerint):")
    for cs in sorrend:
        h, u = cs_hajo.get(cs, 0), cs_uzenet.get(cs, 0)
        print(f"    {cs:<20} {h:>5} hajo ({h/max(len(hajok),1)*100:5.1f}%)   "
              f"{u:>10,} uzenet ({u/max(bbox_sor,1)*100:5.1f}%)")

    print("\n  AIS-osztaly (Type of mobile):")
    for oszt, db in osztaly_db.most_common():
        v = osztaly_statusz[oszt]
        jel = "  <- NEM hajo" if oszt in NEM_HAJO else ""
        print(f"    {oszt:<30} {db:>5} ({db/max(len(hajok),1)*100:5.1f}%)   "
              f"statuszt jelent: {v['statusszal']:>4}/{db:<5} "
              f"({v['statusszal']/max(db,1)*100:5.1f}%){jel}")
    print(f"    -> {nem_hajo_db} MMSI egyaltalan nem hajo "
          f"(boja, bazisallomas, mento-jeado)")

    print("\n  Navigacios statusz CSAK a Class A hajokon "
          f"({len(class_a):,} hajo), top 8:")
    for st, db in st_class_a.most_common(8):
        print(f"    {st[:38]:<38} {db:>5} ({db/max(len(class_a),1)*100:5.1f}%)")

    ki = {
        "nap": path.stem.replace("aisdk-", ""),
        "bbox": not args.teljes_fajl,
        "hajo_db": len(hajok),
        "uzenet_db": bbox_sor,
        "sor_osszes": osszes,
        "nincs_tipus": nincs_tipus,
        "ellentmondo_tipus": ellentmondo,
        "sorrend": sorrend,
        "csoportok": [{"nev": cs, "hajo": cs_hajo.get(cs, 0),
                       "uzenet": cs_uzenet.get(cs, 0)} for cs in sorrend],
        "tipusok": [{"nev": t, "hajo": d} for t, d in tip_hajo.most_common()],
        "statuszok": [{"nev": s, "hajo": d} for s, d in st_hajo.most_common()],
        "osztalyok": [{"nev": o, "hajo": d,
                       "statusszal": osztaly_statusz[o]["statusszal"],
                       "hajo_e": o not in NEM_HAJO}
                      for o, d in osztaly_db.most_common()],
        "nem_hajo_db": nem_hajo_db,
        "class_a_db": len(class_a),
        "class_a_statusz": [{"nev": s, "hajo": d}
                            for s, d in st_class_a.most_common()],
        "kereszt": {cs: dict(kereszt[cs].most_common()) for cs in sorrend},
        "orank": orank,
    }
    Path(args.ki).parent.mkdir(parents=True, exist_ok=True)
    Path(args.ki).write_text(json.dumps(ki, ensure_ascii=False,
                                        separators=(",", ":")), encoding="utf-8")

    with Path(args.csv).open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["csoport", "hajo_db", "hajo_szazalek",
                    "uzenet_db", "uzenet_szazalek"])
        for cs in sorrend:
            h, u = cs_hajo.get(cs, 0), cs_uzenet.get(cs, 0)
            w.writerow([cs, h, round(h/max(len(hajok),1)*100, 2),
                        u, round(u/max(bbox_sor,1)*100, 2)])

    print(f"\n-> {args.ki} kiirva")
    print(f"-> {args.csv} kiirva")


if __name__ == "__main__":
    main()
