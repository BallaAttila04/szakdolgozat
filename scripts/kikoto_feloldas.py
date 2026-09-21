"""
Az AIS "Destination" mezo feloldasa valodi kikotokre UN/LOCODE alapjan.

Az AIS uticel mezoje szabad szoveg, amit a szemelyzet kezzel ir be. A
gyakorlatban keveredik benne a szabvanyos UN/LOCODE kod (SEGOT, DKCPH),
a sima kikotonev (SKAGEN) es a hasznalhatatlan szoveg (FOR ORDERS). Ez a
szkript megmeri, hogy ebbol tenylegesen mennyi oldhato fel kikotove.

A feloldas HAROM SZINTEN tortenik, es mindharom kulon van jelentve, hogy a
gyengebb (tobb tevedest megengedo) illesztes ne mosodjon ossze a biztossal:

  1. pontos   - a mezo pontosan egy ervenyes 5 karakteres UN/LOCODE
  2. nev      - a mezo egy tengeri kikoto neve, es a nev EGYERTELMU
                (ha tobb orszagban is van ilyen nevu kikoto, elvetjuk)
  3. prefix   - a mezo elso 5 karaktere ervenyes LOCODE (pl. "NLRTM PILOT")

A 3. szint a leggyengebb: veletlen egyezes is bekerulhet. Kulon szamoljuk.

Referenciaadat: UN/LOCODE, a datasets/un-locode GitHub-tukorbol (PDDL,
kozkincs). Az UNECE sajat letoltooldala automatizalt keresre 403-at ad,
ezert a tukrot hasznaljuk.

Hasznalat:
    python kikoto_feloldas.py data/aisdk-2026-07-15.zip
    python kikoto_feloldas.py <zip> --csak-bbox
    python kikoto_feloldas.py <zip> --locode data/unlocode.csv --ki out.csv
"""

import argparse
import csv
import re
import sys
import zipfile
from collections import Counter, defaultdict
from pathlib import Path

import pandas as pd
import requests

from utak import ADAT, KIMENET

# A tukor nyers CSV-je. Ellenorizve 2026-09-21: HTTP 200, 7 287 475 bajt,
# 116 213 helyseg, ebbol 17 596 tengeri kikoto.
LOCODE_URL = ("https://raw.githubusercontent.com/datasets/un-locode/"
              "main/data/code-list.csv")

# A Function oszlop 8 karakteres; az elso '1' = tengeri kikoto.
TENGERI_KIKOTO_JEL = "1"

# Dan szorosok - ugyanaz a bbox, mint a tobbi szkriptben
LAT_MIN, LAT_MAX = 54.5, 56.5
LON_MIN, LON_MAX = 10.0, 13.0

CHUNK = 500_000

# Ezeket "nincs uticel"-kent kezeljuk, nem feloldatlankent. Ugyanaz az elv,
# mint a hajo_adatok.py URES halmazaban, kiegeszitve az uticelre jellemzo
# ures ertekekkel.
URES = {"", "UNKNOWN", "UNDEFINED", "NAN", "NONE", "NA",
        "NIL", "NODEST", "NODESTINATION", "NONAME", "UNKNOW"}


def normalizal(s) -> str:
    """Csak betuk es szamok, nagybetusitve. 'SE-GOT ' -> 'SEGOT'"""
    return re.sub(r"[^A-Z0-9]", "", str(s).upper())


def koordinata(nyers: str):
    """'5743N 01158E' -> (57.716..., 11.966...). Ures/hibas eseten None."""
    m = re.fullmatch(r"(\d{2})(\d{2})([NS])\s+(\d{3})(\d{2})([EW])",
                     (nyers or "").strip())
    if not m:
        return None
    fok_l, perc_l, ns, fok_h, perc_h, ew = m.groups()
    lat = int(fok_l) + int(perc_l) / 60
    lon = int(fok_h) + int(perc_h) / 60
    return (-lat if ns == "S" else lat, -lon if ew == "W" else lon)


def locode_betolt(utvonal: Path):
    """Letolti (ha kell) es beolvassa a LOCODE listat.

    Visszaad: (kodok, nevek) ahol
      kodok: 'SEGOT' -> {'nev','orszag','kikoto','lat','lon'}
      nevek: 'GOTEBORG' -> 'SEGOT'  (csak egyertelmu tengeri kikotonevek)
    """
    if not utvonal.exists():
        utvonal.parent.mkdir(parents=True, exist_ok=True)
        print(f"  UN/LOCODE letoltese: {LOCODE_URL}")
        v = requests.get(LOCODE_URL, timeout=120)
        v.raise_for_status()
        utvonal.write_bytes(v.content)
        print(f"  -> {utvonal} ({len(v.content)/1_048_576:.1f} MB)")
    else:
        print(f"  UN/LOCODE a gyorsitotarbol: {utvonal}")

    kodok = {}
    nevek = defaultdict(set)
    kikoto_db = 0

    with utvonal.open(encoding="utf-8", errors="replace") as f:
        for sor in csv.DictReader(f):
            hely = (sor.get("Location") or "").strip()
            orszag = (sor.get("Country") or "").strip()
            if not hely or not orszag:
                continue  # orszag-fejlec sor, nem helyseg

            kod = orszag + hely
            fn = sor.get("Function") or ""
            kikoto = fn.startswith(TENGERI_KIKOTO_JEL)
            nev = (sor.get("Name") or "").strip()
            nev_ekezet_nelkul = (sor.get("NameWoDiacritics") or nev).strip()
            koord = koordinata(sor.get("Coordinates"))

            kodok[kod] = {
                "nev": nev,
                # Ekezet nelkuli valtozat a konzolra: a Windows-konzol
                # cp1250 kodlapja nem tud kiirni pl. 'o'-perjelt (Kobenhavn).
                # A CSV-be a teljes nev megy, utf-8-ban.
                "nev_ascii": nev_ekezet_nelkul,
                "orszag": orszag,
                "kikoto": kikoto,
                "lat": koord[0] if koord else None,
                "lon": koord[1] if koord else None,
            }
            if kikoto:
                kikoto_db += 1
                # Nevegyezest csak tengeri kikotore engedunk
                nevek[normalizal(nev_ekezet_nelkul)].add(kod)

    # Csak az EGYERTELMU nevek hasznalhatok
    egyertelmu = {n: next(iter(k)) for n, k in nevek.items() if len(k) == 1}

    print(f"  {len(kodok):,} helyseg, ebbol {kikoto_db:,} tengeri kikoto, "
          f"{len(egyertelmu):,} egyertelmu kikotonev")
    return kodok, egyertelmu


def feloldas(nyers, kodok: dict, nevek: dict, csak_kikoto: bool = True):
    """Visszaad: (locode|None, szint) ahol szint: pontos|nev|prefix|nincs|ures

    csak_kikoto=True eseten csak tengeri kikotot fogadunk el. Ez nem
    kozmetikai szigoritas: a LOCODE-ter annyira suru, hogy szinte barmely
    5 betus szoveg talal valamit. Meresi pelda a 2026-07-15 napbol:

        "BALTIJSK"     -> BA+LTI -> Laktasi (Bosznia, szarazfoldi)
        "FREDERIKSHAVN"-> FR+EDE -> L'Ile-d'Elle (Franciaorszag, szarazfoldi)
        "BREMERHAVEN"  -> BR+EME -> Eneas Marques (Brazilia, szarazfoldi)
        "BREST"        -> BR+EST -> Estancia (Brazilia)  [Brest = FRBES]

    Mivel a hajo uticelje definicio szerint kikoto, a szarazfoldi talalat
    biztosan teves. A szures ezeket kiejti.
    """
    t = normalizal(nyers)
    if not t or t in URES:
        return None, "ures"

    def jo(kod):
        return kod in kodok and (not csak_kikoto or kodok[kod]["kikoto"])

    if len(t) == 5 and jo(t):
        return t, "pontos"

    kod = nevek.get(t)   # a nevtabla eleve csak tengeri kikotoket tartalmaz
    if kod:
        return kod, "nev"

    if len(t) > 5 and jo(t[:5]):
        return t[:5], "prefix"

    return None, "nincs"


def main():
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("zip_fajl")
    ap.add_argument("--csak-bbox", action="store_true",
                    help="Csak a bounding boxban megjelent hajok uticeljai")
    ap.add_argument("--locode", default=ADAT / "unlocode_code-list.csv",
                    help="A LOCODE CSV helye (letolti, ha nincs meg)")
    ap.add_argument("--ki", default=KIMENET / "uticel_feloldas.csv")
    ap.add_argument("--feloldatlan", default=KIMENET / "uticel_feloldatlan.csv",
                    help="A fel nem oldott uticelek gyakorisaggal")
    ap.add_argument("--barmely-locode", action="store_true",
                    help="Szarazfoldi LOCODE-ot is elfogad (alapbol csak "
                         "tengeri kikotot - ld. a feloldas() dokumentaciojat)")
    args = ap.parse_args()

    path = Path(args.zip_fajl)
    if not path.exists():
        sys.exit(f"Nem letezik: {path}")

    print("UN/LOCODE referenciaadat:")
    kodok, nevek = locode_betolt(Path(args.locode))

    # --- AIS beolvasas ---
    # A mertekado egyseg a (MMSI, uticel) par, nem az uzenetszam: a statikus
    # mezo minden sorra ra van masolva, igy az uzenetszam a hajo aktivitasat
    # merne, nem az uticelek eloszlasat.
    parok = set()
    bbox_hajok = set()
    uzenet_ervenyes_uticellel = 0
    osszes = 0

    print(f"\nAIS beolvasas: {path.name}")
    with zipfile.ZipFile(path) as zf:
        tag = [n for n in zf.namelist() if n.lower().endswith((".csv", ".txt"))][0]
        with zf.open(tag) as raw:
            olvaso = pd.read_csv(
                raw,
                usecols=lambda c: c.strip() in
                {"MMSI", "Destination", "Latitude", "Longitude"},
                chunksize=CHUNK, low_memory=False, encoding="utf-8-sig")
            for ch in olvaso:
                ch.columns = [c.strip() for c in ch.columns]
                osszes += len(ch)

                benne = (ch["Latitude"].between(LAT_MIN, LAT_MAX)
                         & ch["Longitude"].between(LON_MIN, LON_MAX))
                bbox_hajok.update(ch.loc[benne, "MMSI"].unique().tolist())

                # FONTOS: a notna() nem eleg. A DMA CSV-ben a hianyzo uticel
                # nem ures cella, hanem a literal "Unknown" szoveg - azt a
                # notna() kitoltottnek latna, es 100%-ot jelentene.
                van = ch["Destination"].notna()
                uzenet_ervenyes_uticellel += int(
                    (~ch["Destination"].astype("string")
                       .str.replace(r"[^A-Za-z0-9]", "", regex=True)
                       .str.upper()
                       .fillna("")
                       .isin(URES)).sum())
                parok.update(
                    map(tuple,
                        ch.loc[van, ["MMSI", "Destination"]]
                          .drop_duplicates().to_numpy()))

                print(f"  {osszes:>12,} sor", end="\r")
    print()

    if args.csak_bbox:
        parok = {(m, d) for m, d in parok if m in bbox_hajok}

    print(f"  {osszes:,} sor, ebbol {uzenet_ervenyes_uticellel:,} uzenetben van "
          f"erdemi uticel ({uzenet_ervenyes_uticellel/max(osszes,1)*100:.1f}%) "
          f"- a teljes fajlra, a bbox-szurestol fuggetlenul")
    print(f"  {len(bbox_hajok):,} hajo a bounding boxban, "
          f"{len(parok):,} kulonbozo hajo-uticel bejelentes feldolgozasra")

    # --- Feloldas ---
    szintek = Counter()
    talalat = Counter()          # locode -> hany hajo jelentette
    feloldatlan = Counter()
    hajo_feloldva = set()        # hajo, aminek van feloldhato uticelja
    hajo_ertekelheto = set()     # hajo, aki egyaltalan jelentett erdemi uticelt

    for mmsi, nyers in parok:
        kod, szint = feloldas(nyers, kodok, nevek,
                              csak_kikoto=not args.barmely_locode)
        szintek[szint] += 1
        if szint != "ures":
            hajo_ertekelheto.add(mmsi)
        if kod:
            talalat[kod] += 1
            hajo_feloldva.add(mmsi)
        elif szint == "nincs":
            feloldatlan[str(nyers).strip().upper()] += 1

    ertekelheto = len(parok) - szintek["ures"]
    feloldva = szintek["pontos"] + szintek["nev"] + szintek["prefix"]

    print(f"\n  Feloldas ({ertekelheto:,} ertekelheto bejelentesbol, "
          f"{szintek['ures']:,} ures ertek kihagyva):")
    for szint, cimke in [("pontos", "1. pontos LOCODE"),
                         ("nev", "2. egyertelmu kikotonev"),
                         ("prefix", "3. LOCODE prefix (gyenge)"),
                         ("nincs", "   nem oldhato fel")]:
        db = szintek[szint]
        print(f"    {cimke:<28} {db:>7,}  ({db/max(ertekelheto,1)*100:5.1f}%)")
    print(f"    {'OSSZESEN feloldva':<28} {feloldva:>7,}  "
          f"({feloldva/max(ertekelheto,1)*100:5.1f}%)")

    # Hajoszintu lefedettseg - ez a lenyeges szam egy honnan-hova elemzeshez
    hajo_db = len(bbox_hajok) if args.csak_bbox else len({m for m, _ in parok})
    print(f"\n  Hajoszintu lefedettseg ({hajo_db:,} hajobol):")
    print(f"    erdemi uticelt jelentett      {len(hajo_ertekelheto):>7,}  "
          f"({len(hajo_ertekelheto)/max(hajo_db,1)*100:5.1f}%)")
    print(f"    ebbol kikotore feloldhato     {len(hajo_feloldva):>7,}  "
          f"({len(hajo_feloldva)/max(hajo_db,1)*100:5.1f}%)")

    # --- Kimenet: kikotonkenti osszesites ---
    Path(args.ki).parent.mkdir(parents=True, exist_ok=True)
    with Path(args.ki).open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["locode", "kikoto", "orszag", "lat", "lon",
                    "tengeri_kikoto", "hajo_db"])
        for kod, db in talalat.most_common():
            m = kodok[kod]
            w.writerow([kod, m["nev"], m["orszag"], m["lat"], m["lon"],
                        int(m["kikoto"]), db])

    with Path(args.feloldatlan).open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["uticel_szoveg", "hajo_db"])
        for szoveg, db in feloldatlan.most_common():
            w.writerow([szoveg, db])

    print("\n  Top 10 celkikoto (hajo-bejelentes szerint):")
    for kod, db in talalat.most_common(10):
        m = kodok[kod]
        print(f"    {kod}  {m['nev_ascii'][:28]:<28} {db:>5}")

    print("\n  Top 10 fel nem oldott uticel-szoveg:")
    for szoveg, db in feloldatlan.most_common(10):
        # A nyers uticel-szoveg barmit tartalmazhat; a konzolt nem bizhatjuk ra
        biztos = szoveg[:34].encode("ascii", "replace").decode("ascii")
        print(f"    {biztos:<34} {db:>5}")

    koord_nelkul = sum(1 for k in talalat if kodok[k]["lat"] is None)
    print(f"\n  {len(talalat):,} kulonbozo celkikoto, ebbol {koord_nelkul:,} "
          f"koordinata nelkul (terkepre nem rakhato)")
    print(f"-> {args.ki} kiirva")
    print(f"-> {args.feloldatlan} kiirva")


if __name__ == "__main__":
    main()
