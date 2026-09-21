# Szakdolgozat – nagy AIS-adathalmaz tárolása és feldolgozása

BSc szakdolgozat munkaanyaga (Budapesti Corvinus Egyetem,
gazdaságinformatika). A vizsgálat tárgya: hogyan lehet napi több gigabájtos
AIS hajóforgalmi adatot hatékonyan tárolni és lekérdezni.

A dolgozat **szövegét** ez a repó nem tartalmazza – itt a kód, a mérések és
a munkanapló van.

## Mappaszerkezet

```
data/                     nyers, letöltött AIS ZIP-ek (nincs verziózva, ~1 GB/nap)
scripts/                  minden futtatható szkript
  utak.py                 közös útvonalak – minden szkript ezt használja
  terkep_sablon.html      az interaktív térkép HTML-sablonja
  oldal_sablon.html       a publikus nyitólap sablonja (helyőrzőkkel)
  abrak_svg.py            beágyazott SVG-diagramok generálása
  teszt_terkep.mjs        a térkép JS-logikájának tesztje (node)
outputs/                  ábrák, táblázatok, köztes fájlok
  logs/                   futtatási naplók (nincs verziózva)
  tomorites_parquet/      származtatott Parquet fájlok (nincs verziózva)
docs/                     a GitHub Pages által kiszolgált oldal – GENERÁLT,
                          ne szerkeszd kézzel, az oldal_epit.py felülírja
szamok.md                 minden validált szám, forrással és dátummal
```

A szkriptek a saját helyükből számolják a projekt gyökerét, ezért **bármelyik
munkakönyvtárból futtathatók**, és mindig ugyanoda írnak.

## Adatforrás

Dán AIS-adat, napi bontású publikus ZIP fájlok:

```
http://aisdata.ais.dk/aisdk-YYYY-MM-DD.zip
```

HTTP, nem HTTPS – a szerver ezen a címen nem szolgáltat TLS-t. A korábban
használt `web.ais.dk` cím lejárt tanúsítványt ad, nem működik.

A vizsgált terület a dán szorosok: 54,5–56,5° É, 10,0–13,0° K.

## Feldolgozási lánc

```bash
# 1. Adatletöltés
python scripts/letoltes.py 2026-07-15 2026-07-16

# 2. Forgalmi kiértékelés (óránkénti hajószám, ábrával)
python scripts/forgalom_elemzes.py \
    --csucs    data/aisdk-2026-07-15.zip data/aisdk-2026-07-16.zip \
    --kontroll data/aisdk-2026-07-08.zip data/aisdk-2026-07-09.zip \
    --atlag    data/aisdk-2026-09-05.zip

# 3. Tárolási benchmark: CSV vs Parquet vs DuckDB
python scripts/tarolas_benchmark.py data/aisdk-2026-07-15.zip

# 4. Trajektória-tömörítés (dead reckoning) + tradeoff-ábra
python scripts/trajektoria_tomorites.py data/aisdk-2026-07-15.zip \
    --parquet-dir outputs/tomorites_parquet
python scripts/abra_tomorites.py

# 5. A tömörítés hatása az eredményre és a lekérdezési időre
python scripts/tomorites_hatas.py \
    --alap       outputs/tomorites_parquet/aisdk-2026-07-15_teljes.parquet \
    --tomoritett outputs/tomorites_parquet/aisdk-2026-07-15_dr50m.parquet

# 6. Interaktív térkép (pozíciók + hajóadatok + sablon -> egy HTML)
python scripts/terkep_adat.py outputs/tomorites_parquet/aisdk-2026-07-15_teljes.parquet
python scripts/hajo_adatok.py data/aisdk-2026-07-15.zip --csak-bbox
python scripts/terkep_epit.py

# 7. Úticél feloldása valódi kikötőkre UN/LOCODE-dal
python scripts/kikoto_feloldas.py data/aisdk-2026-07-15.zip --csak-bbox

# 8. Hajótípus- és tevékenység-statisztika (a nyitólap diagramjaihoz)
python scripts/hajo_statisztika.py data/aisdk-2026-07-15.zip

# 9. A publikus oldal összeállítása a docs/ mappába
python scripts/oldal_epit.py

# Segédeszköz: mennyi helyet foglalna egy hosszabb időszak?
# (HTTP HEAD-del méri a napi ZIP-méreteket, letöltés nélkül)
python scripts/meret_becsles.py 2026-07-01 2026-07-31
```

## Tesztek

```bash
node scripts/teszt_terkep.mjs     # a térkép színezés- és szűrőlogikája
```

A térkép JavaScriptjét DOM-csonkon futtatja, valódi böngésző nélkül. 22
állítást ellenőriz: a csoportszínezést, a jelmagyarázat felépítését, a
szűrést és a mód váltását.

## Megnyitható változat

A `docs/` mappát a GitHub Pages statikusan kiszolgálja, így az eredmények és az
interaktív térkép **telepítés és bejelentkezés nélkül**, egyetlen linkről
megnyithatók. Bekapcsolás: a repó **Settings → Pages**, *Source*: `Deploy from
a branch`, ág `main`, mappa `/docs`.

Helyi ellenőrzés közzététel előtt:

```bash
python -m http.server 8000 --directory docs   # majd http://localhost:8000
```

Minden szkript `--help`-pel dokumentálja a kapcsolóit.

## Főbb eredmények

A számok forrásostul a [`szamok.md`](szamok.md)-ben, a hozzájuk vezető úttal
és a zsákutcákkal együtt a [`naplo.md`](naplo.md)-ben vannak.

- **Tárolás:** a Parquet a kicsomagolt CSV ~17%-a, a natív DuckDB tábla ~25%.
  A lekérdezés 50–150× gyorsul. A konverzió egyetlen elemzési menet alatt
  megtérül.
- **Trajektória-tömörítés:** dead reckoninggal 50 méteres *garantált*
  hibakorlát mellett 6,4× kisebb fájl, az óránkénti hajószám mindössze
  0,42%-os (mindig alulszámoló) torzításával. A lekérdezés viszont csak
  ~2× gyorsul, nem 6,4× – a méret- és a sebességnyereség nem arányos.
- **Adatminőség:** a forrás sorainak **1,58%-a** használhatatlan pozíciójú
  (0,24% az AIS „pozíció nem elérhető" jelzőértéke `lat = 91,0` formában,
  1,34% érvényes tartományú, de földrajzilag képtelen pozíció).
- **Mi van a vízen:** a hajók **77,3%-a kedvtelési**, de az üzeneteknek csak
  27,9%-a jön tőlük; a teherhajók 5,7%-a adja az üzenetek 19,1%-át. Az
  üzenetszintű megoszlás tehát **nem** a hajómegoszlás.
- **Napszaki ingadozás:** az óránkénti összes hajószám 1,63-szeresére nő
  napközben, de ezt **majdnem teljesen a kedvtelési hajózás hajtja**
  (1248→2343, ×1,88), míg a teherhajóké gyakorlatilag lapos (115→141, ×1,23).
  Ez magyarázza a forgalmi hipotézisnél mért ±13,6%-os napi zajt.
- **AIS-osztály:** a hajók 81,9%-a Class B jeladó, ami **nem sugároz
  navigációs státuszt** – ezért a „mit csinál a hajó" kérdés csak a Class A
  flottára (17,3%, 715 hajó) válaszolható meg.
- **Úticél-feloldás (UN/LOCODE):** üzenetszinten a sorok **65,5%-ában** van
  érdemi úticél, hajószinten viszont a 4138 hajóból csak **15,4%** jelent
  ilyet, és mindössze **10,1%** oldható fel valódi kikötőre. Az AIS statikus
  mezőinek kitöltöttségét ezért hajószinten kell jelenteni, nem üzenetszinten.
  Rakományt az AIS nem közöl, és nyilvános forrásból sem párosítható.
- **Tárhely egy hónapra:** 2026 júliusának mind a 31 napja **22,2 GiB** nyers
  ZIP-ben (mérve, nem becsülve). Parquetté alakítva **nem kisebb**, hanem
  23,8–24,7 GiB — a Parquet a sebességet hozza, nem a helyet. A dán
  szorosokra szűrve, 6 oszloppal és dead reckoninggel viszont **0,31 GiB**,
  a nyers adat 1,4%-a: a nagyságrendi nyereség a szűrésből jön, nem a
  formátumból.
- **Forgalmi hipotézis:** a Kiel-csatorna lezárásának hatása **nem
  igazolt**. Az eredetileg mért ~2× különbség nagy része évszak- és
  hétvége-hatás volt; a kontrollnapokhoz képest +20,2% marad, ami részben
  a napi ingadozás (±13,6%) zajába esik.

## Függőségek

```
pandas  numpy  matplotlib  requests  duckdb  pyarrow
```

A teszt futtatásához `node` is kell (a térkép logikája JavaScript).
