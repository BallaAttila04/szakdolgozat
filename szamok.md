# Validált számok

A dokumentum csak ténylegesen lefuttatott szkriptek eredményeit
tartalmazza, forrásmegjelöléssel (szkript, paraméterek, dátum). A
megváltozott értékek nem kerülnek felülírásra: áthúzva maradnak, mellettük
az új érték és a változás indoklása.

## Forgalmi kiértékelés (dán szorosok, 54.5–56.5°N, 10.0–13.0°E)

Forrás: `forgalom_elemzes.py`, kimenet `forgalmi_osszefoglalo.csv`,
lefuttatva 2026-09-18.

| szám | jelentés | szkript | dátum |
|------|----------|---------|-------|
| 10 860 221 | napi üzenetszám a bounding boxban, 2026-07-15 | forgalom_elemzes.py | 2026-09-18 |
| 10 968 080 | napi üzenetszám a bounding boxban, 2026-07-16 | forgalom_elemzes.py | 2026-09-18 |
| 6 030 204 | napi üzenetszám a bounding boxban, 2026-09-05 (referencia) | forgalom_elemzes.py | 2026-09-18 |
| 2971 | csúcsórai (09:00) egyedi hajószám, 2026-07-15 | forgalom_elemzes.py | 2026-09-18 |
| 2943 | csúcsórai (09:00) egyedi hajószám, 2026-07-16 | forgalom_elemzes.py | 2026-09-18 |
| 1261 | csúcsórai (10:00) egyedi hajószám, 2026-09-05 (referencia) | forgalom_elemzes.py | 2026-09-18 |
| 2275.5 | átlagos órai egyedi hajószám, 2026-07-15 | forgalom_elemzes.py | 2026-09-18 |
| 2245.8 | átlagos órai egyedi hajószám, 2026-07-16 | forgalom_elemzes.py | 2026-09-18 |
| 1144.5 | átlagos órai egyedi hajószám, 2026-09-05 (referencia) | forgalom_elemzes.py | 2026-09-18 |
| ~~~2×~~ → **+20.2%** | 07-15/07-16 forgalomtöbblete | forgalom_elemzes.py + kézi számolás | ~~2026-09-18~~ → 2026-09-19 |

**A ~2× áthúzva — miért változott:** a ~2× a **szeptember 5-i**
referencianaphoz mérte a lezárási napokat, és ez a referencia két
szempontból is rossz volt: (1) más évszak, (2) **szombat**, miközben a
lezárási napok szerda és csütörtök. A 2026-09-19-én letöltött júliusi
kontrollnapokkal (07-08 szerda, 07-09 csütörtök, lezárás nélkül) a
különbség felbontható:

| összehasonlítás | arány | mit mér |
|---|---|---|
| lezárási napok / szeptemberi szombat | 1.962 (+96.2%) | a régi, félrevezető szám |
| júliusi kontroll / szeptemberi szombat | 1.632 (+63.2%) | évszak + hét napja |
| lezárási napok / júliusi kontroll | **1.202 (+20.2%)** | ennyi marad a lezárásra |

Párosított, azonos hét napján (a hibás 11. óra kihagyva minden napból):

| szám | jelentés | szkript | dátum |
|------|----------|---------|-------|
| 1.292 (+29.2%) | szerda: 07-15 / 07-08 arány | forgalom_elemzes.py | 2026-09-19 |
| 1.123 (+12.3%) | csütörtök: 07-16 / 07-09 arány | forgalom_elemzes.py | 2026-09-19 |
| 1.136 (+13.6%) | **zajszint**: két rendes kontrollnap aránya (07-09 / 07-08) | forgalom_elemzes.py | 2026-09-19 |
| 1741.1 | átlagos órai egyedi hajószám, 2026-07-08 (kontroll, 23 óra) | forgalom_elemzes.py | 2026-09-19 |
| 1978.8 | átlagos órai egyedi hajószám, 2026-07-09 (kontroll, 23 óra) | forgalom_elemzes.py | 2026-09-19 |

**Fontos — a hipotézis továbbra sem igazolt:** a csütörtöki +12.3% a
megfigyelt napi zajszint (+13.6%) **alatt** van, tehát nem
különböztethető meg a szokásos napi ingadozástól. A szerdai +29.2% a
zajszint fölött van, de ez 1 nap 1 nap ellen — szignifikanciát ebből
állítani nem lehet. Több kontrollnap kell (július összes szerdája és
csütörtöke a lezárással érintettek nélkül).

**Adathiány — 2026-07-08, 11. óra:** 134 168 üzenet és 1084 egyedi hajó
a szomszédos órák ~330–360 ezer / ~2020 értékei helyett. Ez vételi vagy
naplózási kiesés a forrásadatban, nem valódi forgalom. Mind az 5 nap
átvizsgálva, ez az egyetlen ilyen óra. A fenti arányok úgy készültek,
hogy a 11. óra **mindegyik napból ki van hagyva** (23 óra átlaga),
interpoláció nélkül.

## Adattárolás-benchmark (CSV vs Parquet vs DuckDB)

Forrás: `tarolas_benchmark.py`, kimenet `tarolas_benchmark.csv`,
lefuttatva 2026-09-18 a két valódi napi AIS fájlon
(`data/aisdk-2026-07-15.zip`, `data/aisdk-2026-07-16.zip`),
duckdb 1.5.5.

Méret:

| szám | jelentés | szkript | dátum |
|------|----------|---------|-------|
| 6248.0 MB | kicsomagolt CSV mérete, 2026-07-15 | tarolas_benchmark.py | 2026-09-18 |
| 6137.7 MB | kicsomagolt CSV mérete, 2026-07-16 | tarolas_benchmark.py | 2026-09-18 |
| 1061.2 MB | Parquet mérete, 2026-07-15 (a CSV ~17%-a) | tarolas_benchmark.py | 2026-09-18 |
| 1059.5 MB | Parquet mérete, 2026-07-16 (a CSV ~17%-a) | tarolas_benchmark.py | 2026-09-18 |
| 1537.3 MB | DuckDB natív tábla mérete, 2026-07-15 (a CSV ~25%-a) | tarolas_benchmark.py | 2026-09-18 |
| 1507.8 MB | DuckDB natív tábla mérete, 2026-07-16 (a CSV ~25%-a) | tarolas_benchmark.py | 2026-09-18 |

Lekérdezési idő (mind a négy lekérdezés együtt):

| szám | jelentés | szkript | dátum |
|------|----------|---------|-------|
| 151.4 mp | pandas, nyers CSV, 2026-07-15 | tarolas_benchmark.py | 2026-09-18 |
| 141.2 mp | pandas, nyers CSV, 2026-07-16 | tarolas_benchmark.py | 2026-09-18 |
| 56.2 mp | DuckDB nyers CSV-n, 2026-07-15 | tarolas_benchmark.py | 2026-09-18 |
| 60.9 mp | DuckDB nyers CSV-n, 2026-07-16 | tarolas_benchmark.py | 2026-09-18 |
| 3.10 mp | DuckDB + Parquet, 2026-07-15 | tarolas_benchmark.py | 2026-09-18 |
| 1.64 mp | DuckDB + Parquet, 2026-07-16 | tarolas_benchmark.py | 2026-09-18 |
| 0.99 mp | DuckDB natív tábla, 2026-07-15 | tarolas_benchmark.py | 2026-09-18 |
| 1.05 mp | DuckDB natív tábla, 2026-07-16 | tarolas_benchmark.py | 2026-09-18 |

Egyszeri konverziós költség:

| szám | jelentés | szkript | dátum |
|------|----------|---------|-------|
| 66.2 mp | CSV → Parquet konverzió, 2026-07-15 | tarolas_benchmark.py | 2026-09-18 |
| 54.4 mp | CSV → Parquet konverzió, 2026-07-16 | tarolas_benchmark.py | 2026-09-18 |
| 114.1 mp | CSV → DuckDB natív tábla, 2026-07-15 | tarolas_benchmark.py | 2026-09-18 |
| 124.2 mp | CSV → DuckDB natív tábla, 2026-07-16 | tarolas_benchmark.py | 2026-09-18 |

**Fontos – a mérés korlátai (a dolgozatban ki kell mondani):**
- **Egyetlen futás, ismétlés nélkül**, kontrollálatlan operációs
  rendszer fájl-cache-sel. Ez látszik az adatokon: azonos munkára
  3.10 mp (07-15) vs 1.64 mp (07-16) a Parquet-nél – közel 2× szórás.
  A nagyságrendi következtetést (Parquet/tábla >> CSV) ez nem érinti,
  de **publikálható számokhoz 3–5 ismételt mérés kell**, hideg/meleg
  cache külön jelölve. A fenti számok ezért **előzetesek**.
- A pandas-ág az összes oszlopot beolvassa, a Parquet/tábla motorok
  csak a lekérdezéshez kellőket – ez pont az oszlopos tárolás lényege,
  tehát jogos összehasonlítás, de explicit ki kell mondani.

**Keresztvalidáció:** a benchmark DuckDB-eredményei pontosan egyeznek a
`forgalom_elemzes.py` (pandas) fenti számaival – 10 860 221 és
10 968 080 bounding box-találat, csúcsóra 09:00-kor 2971 ill. 2943
egyedi hajóval. Két független kódút (pandas chunk vs SQL) azonos
eredménye, ez megerősíti a forgalmi kiértékelés számait.

## Trajektória-tömörítés (dead reckoning)

Forrás: `trajektoria_tomorites.py`, kimenet `trajektoria_tomorites.csv`,
lefuttatva 2026-09-19 a `data/aisdk-2026-07-15.zip` fájlon. Bounding box: 54.5–56.5°N, 10.0–13.0°E.
Oszlopok: MMSI, ts, Latitude, Longitude, SOG, COG. Kodek: zstd.

| szám | jelentés | szkript | dátum |
|------|----------|---------|-------|
| 10 860 221 | összes pozíció a bounding boxban, 2026-07-15 | trajektoria_tomorites.py | 2026-09-19 |
| 4 138 | egyedi hajó a bounding boxban, 2026-07-15 | trajektoria_tomorites.py | 2026-09-19 |
| 84.3 MB | tömörítetlen Parquet (zstd, 6 oszlop, bbox) | trajektoria_tomorites.py | 2026-09-19 |
| 20.8 MB / 4.05× | dead reckoning, 10 m küszöb (77.77% tömörítés) | trajektoria_tomorites.py | 2026-09-19 |
| 15.5 MB / 5.44× | dead reckoning, 25 m küszöb (80.57%) | trajektoria_tomorites.py | 2026-09-19 |
| **13.2 MB / 6.39×** | dead reckoning, **50 m küszöb** (82.02%) | trajektoria_tomorites.py | 2026-09-19 |
| 11.6 MB / 7.27× | dead reckoning, 100 m küszöb (82.99%) | trajektoria_tomorites.py | 2026-09-19 |
| 10.4 MB / 8.11× | dead reckoning, 250 m küszöb (83.58%) | trajektoria_tomorites.py | 2026-09-19 |
| 10.0 MB / 8.43× | dead reckoning, 500 m küszöb (83.78%) | trajektoria_tomorites.py | 2026-09-19 |
| ~16% | a megtartott pontok **padlója** (kötelező horgonyok: >600 mp időrés, érvénytelen SOG/COG, valódi manőverek) | trajektoria_tomorites.py | 2026-09-19 |

A küszöb **garantált felső korlát** a pozícióhibára, nem átlag: konstrukció
szerint minden eldobott pont visszaszámolási hibája a küszöb alatt marad.
Az átlagos hiba ennél jóval kisebb (50 m-es küszöbnél 13,6 m).

**Fontos – mivel NEM hasonlítható össze:** a 84.3 MB nem vethető össze a
tárolási benchmark 1061 MB-os értékével, mert az egész napra, ~26 oszlopra és
snappy kodekkel készült, míg ez bbox-szűrt, 6 oszlopos, zstd. A **6.39× tisztán
a trajektória-tömörítés hatása**, azonos oszlopkészleten és kodekkel mérve.

**Még nem mért, tehát nem állítható:** a tömörített adaton a lekérdezési idő,
és hogy a forgalmi kiértékelés ugyanazt az eredményt adja-e a tömörített
adaton. Csak egyetlen napon (07-15) futott.

### A tömörítés hatása az elemzésre és a lekérdezésre

Forrás: `tomorites_hatas.py`, kimenet `tomorites_hatas.csv`, lefuttatva
2026-09-19, 5 ismétlés / medián.
Lekérdezés: óránkénti egyedi hajószám – az a metrika, amire a forgalmi
kiértékelés épül.

| szám | jelentés | szkript | dátum |
|------|----------|---------|-------|
| 238.7 ms | lekérdezés a tömörítetlen Parqueten (84.3 MB), medián | tomorites_hatas.py | 2026-09-19 |
| 124.7 ms | lekérdezés a 50 m-es tömörítetten (13.2 MB), medián | tomorites_hatas.py | 2026-09-19 |
| **1.91×** | lekérdezési gyorsulás 50 m-nél (miközben a fájl 6.39× kisebb) | tomorites_hatas.py | 2026-09-19 |
| **0.42%** | max. relatív eltérés az óránkénti hajószámban, 50 m | tomorites_hatas.py | 2026-09-19 |
| 11 | max. abszolút eltérés (hajó/óra) a ~2600-ból, 50 m | tomorites_hatas.py | 2026-09-19 |
| 3.67 | átlagos abszolút eltérés (hajó/óra), 50 m | tomorites_hatas.py | 2026-09-19 |
| 4138 = 4138 | napi összes egyedi hajószám: tömörítetlen vs tömörített (**pontosan egyezik**) | tomorites_hatas.py | 2026-09-19 |

**Az eltérés iránya garantáltan egyirányú:** a tömörített adat kizárólag
**alulszámol**, soha nem felül (minden óránkénti eltérés ≥ 0). Oka: egy
órában rövid ideig jelen lévő, egyenesen haladó hajó elveszítheti az összes
pontját abban az órában, de új hajó nem keletkezhet. A **napi** hajószám
konstrukció szerint pontos, mert minden hajó első pontja mindig megmarad.

**Nagyságrendi viszonyítás:** a 0.42%-os torzítás a mért napi zajszint
(+13.6%) kb. harmincad része, a vizsgált lezárási hatásnak (+20.2%) az
ötvened része – az elemzési következtetéseket tehát nem befolyásolja.

**A tárhely- és a sebességnyereség NEM arányos:** 6.39× kisebb fájl mellett
csak 1.91× gyorsulás, mert a `COUNT(DISTINCT MMSI)` költségét a különböző
értékek száma (4138, minden változatban azonos) és a fix overhead hajtja, nem
a sorszám. A küszöb szigorítása a sebességet gyakorlatilag nem befolyásolja
(10 m: 121.5 ms vs 500 m: 119.5 ms – szóráson belül, nem monoton a mérettel).

**Még nem mért:** csak a 07-15-ös napon és csak erre az egy metrikára.
Útvonalhosszra, sebességeloszlásra vagy kapuvonal-átlépésre a torzítás más
lehet – azt külön kell mérni, nem szabad ebből általánosítani.

## Adatminőség a forrásfájlban (2026-07-15)

Forrás: közvetlen mérés a `data/aisdk-2026-07-15.zip` fájlon, 2026-09-19. A teljes napi fájlra
vonatkozik, nem csak a bounding boxra.

### Hibás pozíciók

| szám | jelentés | forrás | dátum |
|------|----------|--------|-------|
| 36 650 571 | a napi fájl összes sora | közvetlen mérés | 2026-09-19 |
| 87 126 (0.238%) | **jelzőérték** pozíció (lat ≥ 90 v. lon ≥ 180), tipikusan `91.0 / 0.0` | közvetlen mérés | 2026-09-19 |
| 3 223 (24%) | hajó, amely legalább egy jelzőértéket küldött (13 387-ből) | közvetlen mérés | 2026-09-19 |
| 492 650 (1.344%) | **érvényes tartományú, de földrajzilag képtelen** pozíció | közvetlen mérés | 2026-09-19 |
| 1 486 (11%) | hajó, amely legalább egy ilyet küldött (13 387-ből) | közvetlen mérés | 2026-09-19 |
| **1.58%** | a sorok összesen használhatatlan pozícióval | közvetlen mérés | 2026-09-19 |
| −85.801 – 81.304° | a fájl szélességi kiterjedése a jelzőértékek nélkül | közvetlen mérés | 2026-09-19 |
| −122.025 – 122.434° | a fájl hosszúsági kiterjedése a jelzőértékek nélkül | közvetlen mérés | 2026-09-19 |

A 91° az AIS szabvány (ITU-R M.1371) „pozíció nem elérhető" jelzőértéke, ami
a CSV-ben **valódi számként** jelenik meg, nem üres mezőként — előzetes
szűrés nélkül érvényes koordinátaként dolgozódna fel.

**Ezek a hibák az eddigi elemzést nem rontották el**, mert a bounding box
szűrés mindkét típust kizárja — de ez szerencse, nem tervezés.

### Statikus mezők ellentmondásai (bounding box, 4 138 hajó)

| szám | jelentés | szkript | dátum |
|------|----------|---------|-------|
| 256 (6.2%) | hajó ellentmondó `Type of mobile` értékkel — **gyanús**, az AIS-osztály nem változhat | hajo_adatok.py | 2026-09-19 |
| 128 (3.1%) | hajó ellentmondó `Destination` értékkel — **NEM hiba**, az úticél jogosan változik út közben | hajo_adatok.py | 2026-09-19 |
| 15 / 7 | hajó ellentmondó `Length` / `Width` értékkel — **valódi hiba**, a méret nem változik | hajo_adatok.py | 2026-09-19 |
| 5 / 3 / 1 | hajó ellentmondó `Name` / `Ship type` / `Callsign` értékkel | hajo_adatok.py | 2026-09-19 |
| 94 (2.3%) | hajó bejelentett név nélkül | hajo_adatok.py | 2026-09-19 |

**Figyelem:** a `hajo_adatok.py` jelenleg minden eltérést „ellentmondásként"
számol, beleértve a jogos változásokat is (`Destination`). A dolgozatban ezt
szét kell választani, különben felfújt adatminőségi szám jön ki.

## Úticél-feloldás UN/LOCODE-dal (2026-07-15, bounding box)

Forrás: `kikoto_feloldas.py data/aisdk-2026-07-15.zip --csak-bbox`, kimenet
`outputs/uticel_feloldas.csv` és `outputs/uticel_feloldatlan.csv`,
lefuttatva 2026-09-21.
Referenciaadat: UN/LOCODE, `datasets/un-locode` GitHub-tükör (PDDL, közkincs).

| szám | jelentés | szkript | dátum |
|------|----------|---------|-------|
| 116 067 | UN/LOCODE helység összesen | kikoto_feloldas.py | 2026-09-21 |
| 17 596 | ebből tengeri kikötő (`Function` első karaktere `1`) | kikoto_feloldas.py | 2026-09-21 |
| 16 723 | egyértelmű (egy országhoz köthető) tengeri kikötőnév | kikoto_feloldas.py | 2026-09-21 |
| 24 021 314 (65.5%) | üzenet érdemi úticéllel, teljes napi fájl | kikoto_feloldas.py | 2026-09-21 |
| 4 869 | különböző (hajó, úticél) bejelentés a bounding boxban | kikoto_feloldas.py | 2026-09-21 |
| 781 | ebből érdemi (nem `Unknown` / üres) | kikoto_feloldas.py | 2026-09-21 |
| 306 (39.2%) | feloldva **pontos** 5 karakteres LOCODE-ként | kikoto_feloldas.py | 2026-09-21 |
| 158 (20.2%) | feloldva **egyértelmű kikötőnévként** | kikoto_feloldas.py | 2026-09-21 |
| 55 (7.0%) | feloldva **LOCODE-prefixként** (leggyengébb szint) | kikoto_feloldas.py | 2026-09-21 |
| **519 (66.5%)** | összesen feloldva a 781 érdemi bejelentésből | kikoto_feloldas.py | 2026-09-21 |
| 262 (33.5%) | nem oldható fel | kikoto_feloldas.py | 2026-09-21 |
| 184 | különböző célkikötő | kikoto_feloldas.py | 2026-09-21 |
| 83 (45%) | ebből koordináta nélküli az UN/LOCODE-ban (térképre nem rakható) | kikoto_feloldas.py | 2026-09-21 |

Hajószintű lefedettség — **ez a lényeges szám** egy honnan-hová elemzéshez:

| szám | jelentés | szkript | dátum |
|------|----------|---------|-------|
| 4 138 | hajó a bounding boxban | kikoto_feloldas.py | 2026-09-21 |
| 636 (**15.4%**) | hajó, amely egyáltalán jelentett érdemi úticélt | kikoto_feloldas.py | 2026-09-21 |
| 419 (**10.1%**) | hajó, amelynek az úticélja valódi kikötőre feloldható | kikoto_feloldas.py | 2026-09-21 |

**A legfontosabb megállapítás — az üzenetszintű kitöltöttség félrevezető:**
üzenetszinten a sorok **65,5%-ában** van érdemi úticél, hajószinten viszont
csak a hajók **15,4%-a** jelent ilyet. A különbség oka, hogy az üzenetszámot
néhány folyamatosan sugárzó, rögzített útvonalú hajó (kompok) uralja. Az AIS
statikus mezőinek kitöltöttségét ezért **hajószinten kell jelenteni**,
üzenetszinten nem — ez általánosítható a `Ship type`, `Destination`,
`Draught` mezőkre is.

**Módszertani döntés – csak tengeri kikötő fogadható el.** Kikötőszűrés
nélkül a 195 célpontból **12 szárazföldi** helység volt, rendszeres hibából:

| hibás találat | valójában | mechanizmus |
|---|---|---|
| `BALTI` → Laktasi (BA) | Baltijsk | a `BALTIJSK` első 5 karaktere: BA+LTI |
| `FREDE` → L'Ile-d'Elle (FR) | Frederikshavn | FR+EDE |
| `BREME` → Eneas Marques (BR) | Bremerhaven | BR+EME |
| `BREST` → Estancia (BR) | Brest (= FRBES) | BR+EST |
| `COPENHAGEN` → USKOG (US) | København (DKCPH) | névegyezés egy New York állami faluval |

116 067 helység mellett a kódtér olyan sűrű, hogy szinte bármely 5 betűs
szöveg talál valamit, ha az első két karaktere érvényes országkód. A szűkítés
után **0 nem-kikötő** maradt a 184 célpontból.

**A szűkítés ára:** a `GILLELEJE` (DKGLE) valódi dán halászkikötő, de az
UN/LOCODE `--3-----` (közúti terminál) kóddal tartja nyilván, ezért kiesik.
A szigorítás tehát néhány valódi kisebb kikötőt is elveszít.

**Rakomány – amit NEM lehet:** az AIS nem sugároz rakománymegnevezést, és
nyilvános forrásból sem párosítható ehhez az adathoz. Az egyetlen nyilvános
rakjegy-adatbázis az amerikai vámhatóságé (19 CFR 103.31(d)), ami csak az
USA-ba tartó tengeri importot fedi — a dán szorosok Balti-tenger ↔ Északi-
tenger forgalmával gyakorlatilag nulla átfedésben. Az EU-ban nincs nyilvános
manifeszt. A `Cargo type` oszlop **nem rakomány**, hanem IMO szerinti
szennyezési veszélykategória (X/Y/Z/OS), és csak töredékesen kitöltött.

## Hajótípus és tevékenység (2026-07-15, bounding box)

Forrás: `hajo_statisztika.py data/aisdk-2026-07-15.zip`, kimenet
`outputs/hajo_statisztika.json` és `.csv`, lefuttatva 2026-09-21. A hajónkénti típus és státusz a
hajó által **legtöbbször jelentett** érték (a statikus mezőket kézzel
állítják, ezért egy hajó többfélét is jelenthet: 2 hajó tett így).

| szám | jelentés | szkript | dátum |
|------|----------|---------|-------|
| 4 138 | egyedi MMSI a bounding boxban | hajo_statisztika.py | 2026-09-21 |
| ~~10 860 221~~ → **4 759 634** | üzenet a bounding boxban (~~29,6%~~ → 13,0% a napi fájlból) — a régi szám 56% duplikátumot tartalmazott | hajo_statisztika.py | ~~2026-09-21~~ → 2026-09-21 (javítva) |
| 141 (3,4%) | hajó, amely nem jelentett hajótípust | hajo_statisztika.py | 2026-09-21 |

Típusmegoszlás — **a két mértékegység szándékosan egymás mellett**:

| csoport | hajó | hajó % | ~~üzenet (nyers)~~ → **üzenet (dedup.)** | ~~üzenet %~~ → **%** |
|---|---|---|---|---|
| Kedvtelési (vitorlás + sport) | 3 200 | **77,3%** | ~~3 026 786~~ → **1 788 679** | ~~27,9%~~ → **37,6%** |
| Egyéb / ismeretlen | 278 | 6,7% | ~~1 489 125~~ → **566 479** | ~~13,7%~~ → **11,9%** |
| Teherhajó | 237 | **5,7%** | ~~2 076 260~~ → **648 421** | ~~19,1%~~ → **13,6%** |
| Szolgálati (vontató, révkalauz, mentő…) | 158 | 3,8% | ~~1 434 159~~ → **672 383** | ~~13,2%~~ → **14,1%** |
| Személyszállító | 133 | 3,2% | ~~1 503 005~~ → **600 626** | ~~13,8%~~ → **12,6%** |
| Tanker | 67 | 1,6% | ~~675 232~~ → **199 095** | ~~6,2%~~ → **4,2%** |
| Halászhajó | 65 | 1,6% | ~~655 654~~ → **283 951** | ~~6,0%~~ → **6,0%** |

**Az üzenetoszlop áthúzva — miért változott:** kiderült, hogy a forrásadat
sorainak **56,0%-a bitre azonos duplikátum** (ld. lentebb, „Duplikált sorok").
A duplikálás aránya **típusonként erősen eltér** (tanker 70,5%, kedvtelési
40,9%), ezért a nyers sorszámból számolt megoszlás torz volt: felülbecsülte a
kereskedelmi hajók üzenetrészesedését. A `hajo_statisztika.py` 2026-09-21 óta
alapból deduplikál; a nyers érték a `--nyers-sorok` kapcsolóval kérhető vissza.
**A hajószámok változatlanok** — azokat a duplikáció nem érinti, és a rájuk
épülő megállapítások is állnak.

**Az üzenetszintű megoszlás NEM a hajómegoszlás.** A kedvtelési hajók a hajók
77,3%-át adják, de az üzenetek 27,9%-át; a teherhajóknál fordított az arány
(5,7% vs 19,1%). Oka: a Class A jeladók másodperces nagyságrendben sugároznak,
a Class B-k jóval ritkábban. Ugyanez a csapda jött elő az úticél-feloldásnál
(65,5% üzenetszinten vs 15,4% hajószinten) — **tehát rendszerszintű
tulajdonság, nem egyedi eset.** A dolgozatban minden megoszlási arányt
hajószinten kell jelenteni, és ki kell mondani, melyiket használjuk.

### AIS-osztály (`Type of mobile`)

| szám | jelentés | szkript | dátum |
|------|----------|---------|-------|
| 3 389 (81,9%) | **Class B** jeladó (kisebb és szabadidős hajók) | hajo_statisztika.py | 2026-09-21 |
| 715 (17,3%) | **Class A** jeladó (kereskedelmi hajók kötelező jeladója) | hajo_statisztika.py | 2026-09-21 |
| 693 / 715 (96,9%) | Class A hajó, amely jelentett navigációs státuszt | hajo_statisztika.py | 2026-09-21 |
| 1 / 3 389 (0,0%) | Class B hajó, amely jelentett navigációs státuszt | hajo_statisztika.py | 2026-09-21 |
| **33** | MMSI, amely **egyáltalán nem hajó**: 24 navigációs jelző (AtoN, bója), 8 parti bázisállomás, 1 mentő-jeladó | hajo_statisztika.py | 2026-09-21 |

**A hiányzó státusz nem adathiba.** A Class B jeladók pozícióüzenete az
AIS-szabvány szerint nem tartalmaz navigációs státuszmezőt — a 0,0% éppen ezt
erősíti meg. Következmény: a „mit csinál a hajó" kérdés **csak a Class A
flottára (17,3%) válaszolható meg** — ami viszont éppen a kereskedelmi
forgalom, tehát az érdemi rész.

**A 4 138 kb. 0,8%-kal felülszámolja a valódi hajókat**, mert 33 azonosító nem
hajó. A korábbi számokat ez nem érvényteleníti (nagyságrendileg nem számít),
de a dolgozatban ki kell mondani, hogy az „egyedi MMSI" és a „hajó" nem
ugyanaz.

### Class A navigációs státusz (715 hajó)

| státusz | magyarul | hajó | arány |
|---|---|---|---|
| Under way using engine | Géppel úton | 499 | 69,8% |
| Moored | Kikötve | 95 | 13,3% |
| Engaged in fishing | Halászik | 28 | 3,9% |
| Under way sailing | Vitorlával úton | 23 | 3,2% |
| (nem jelentett) | – | 22 | 3,1% |
| At anchor | Horgonyon | 18 | 2,5% |
| Restricted maneuverability | Korlátozott manőverképesség | 16 | 2,2% |
| Constrained by her draught | Merülése korlátozza | 8 | 1,1% |

### Napszaki ingadozás — és ami ebből a Kiel-hipotézisre következik

| szám | jelentés | szkript | dátum |
|------|----------|---------|-------|
| 1 824 → 2 971 (**×1,63**) | óránkénti **összes** egyedi hajószám min→max | hajo_statisztika.py | 2026-09-21 |
| 1 248 → 2 343 (**×1,88**) | óránkénti **kedvtelési** hajószám min→max | hajo_statisztika.py | 2026-09-21 |
| 115 → 141 (**×1,23**) | óránkénti **teherhajó**-szám min→max | hajo_statisztika.py | 2026-09-21 |
| 99 → 115 (×1,16) | óránkénti személyszállító-szám min→max | hajo_statisztika.py | 2026-09-21 |
| 304 | teher + tanker hajó összesen a 4 138-ból (**7,3%**) | hajo_statisztika.py | 2026-09-21 |

**A napi forgalmi görbét majdnem teljesen a szabadidős hajózás hajtja.** A
kereskedelmi hajók száma a nap 24 órájában gyakorlatilag állandó.

**Ez a forgalmi hipotézis mérőszámát érinti.** A Kiel-lezárás hatását
óránkénti **összes** egyedi hajószámon mértük (ld. fentebb, „Forgalmi
kiértékelés"). Ezt a mérőszámot viszont a kedvtelési hajózás uralja, ami
időjárás- és napszakfüggő, a csatornalezárásra pedig érzéketlen. A lezárás a
kereskedelmi átmenő forgalmat terelné el — ami itt 304 hajó, a flotta 7,3%-a.
**Valószínű magyarázat arra, miért volt ±13,6% a napi zaj, és miért nem
emelkedik ki belőle a +20,2%-os hatás.**

A fenti Kiel-számokat **ez nem érvényteleníti és nem írja felül** — azok
pontosan azt mérik, amit mérnek. A helyes folytatás egy **kereskedelmi
hajókra szűrt kapuvonal-metrika**, ami eddig is nyitott tétel volt; most
konkrét indoklást kapott.

**Korlát:** egyetlen nap (2026-07-15, július közepe). A napszaki mintázat
erőssége csaknem biztosan évszakfüggő — egy téli napon a kedvtelési hajózás
töredéke várható. Ezt **nem mértük**, tehát nem is állítjuk.

### Színpaletta-validálás (módszertani melléklet)

A térkép típusszíneit nem szemre választottuk. A színeket egy színlátás-zavart szimuláló ellenőrző szkripttel
vizsgáltuk a térkép tényleges felületszíneire futtatva,
**minden színpárra** (a térkép szórásdiagram jellegű, bármely két pont
szomszédos lehet):

| színek száma | világos (#e6ecf0) | sötét (#0b131b) |
|---|---|---|
| 7 | bukás (CVD ΔE 3,2; normál látás ΔE 12,9) | bukás (CVD ΔE 1,6; normál ΔE 9,8) |
| 5 (6 kombináció) | mind bukás | mind bukás |
| 4 (5 kombináció) | mind bukás | mind bukás |
| **3** (kék+narancs+aqua) | **átmegy** | **átmegy** |

Ezért a térképen **három kategória kap saját színt** (ezek fedik a hajók
88%-át), a többi semleges szürkét, és a jelmagyarázat kattintható szűrő, hogy
minden típus külön is megnézhető legyen. A weboldal vonaldiagramjai
**szomszédos** párokon validálnak (ott a sorozatok nem keverednek térben), ott
6 szín is átmegy mindkét témában.

## Egy teljes hónap tárhelyigénye (2026. július)

Forrás: `meret_becsles.py 2026-07-01 2026-07-31`, lefuttatva 2026-09-21.

**A letöltendő méret MÉRT, nem becsült:** a napi ZIP-ek `Content-Length`
értéke HTTP HEAD kéréssel, letöltés nélkül. A módszer keresztvalidálva az
öt már letöltött napon — mind az ötnél **bájtra egyezik** a szerver által
jelentett méret a lemezen lévő fájllal.

| szám | jelentés | szkript | dátum |
|------|----------|---------|-------|
| 31 | elérhető nap 2026 júliusában (hiánytalan) | meret_becsles.py | 2026-09-21 |
| 23 860 254 786 bájt (**22,2 GiB**) | a teljes hónap nyers ZIP-ben | meret_becsles.py | 2026-09-21 |
| 734 MiB | átlagos napi ZIP-méret | meret_becsles.py | 2026-09-21 |
| 583 – 988 MiB | a napi méret szórása (**±35%**) | meret_becsles.py | 2026-09-21 |

A napi méret ±35%-os szórása miatt **egyetlen napból extrapolálni félrevezető
lett volna** — ezért mértük mind a 31 napot.

Tárolt méret formánként (a benchmark ZIP-hez viszonyított arányaiból, alsó–felső
sáv a két mért napból):

| tárolási forma | teljes hónap | napi |
|---|---|---|
| Nyers ZIP (ahogy letöltjük) | **22,2 GiB** | 734 MiB |
| Kicsomagolt CSV | 138,0 – 145,3 GiB | 4 559 – 4 799 MiB |
| **Parquet (snappy, minden oszlop)** | **23,8 – 24,7 GiB** | 787 – 815 MiB |
| DuckDB natív tábla | 33,9 – 35,7 GiB | 1 120 – 1 181 MiB |

**A Parquet NEM kisebb a ZIP-nél** — 22,2 GiB helyett 23,8–24,7 GiB. Ez
megerősíti a tárolási benchmark korábbi megfigyelését: a Parquet nyeresége a
**lekérdezési sebesség**, nem a hely. A ZIP már tömörített; a Parquet azért
nagyobb, mert oszloponként külön tömörít és row-group statisztikákat is tárol —
cserébe viszont egy oszlop kiolvasható belőle a fájl kitömörítése nélkül.
Ezt a dolgozatban ki kell mondani, különben azt sugallná, hogy a Parquet
helytakarékos is.

Csak a vizsgált területre szűrve (bounding box + 6 oszlop + zstd):

| tárolási forma | teljes hónap | napi | a nyers %-a |
|---|---|---|---|
| Parquet, tömörítés nélkül | 1,96 GiB | 65 MiB | 8,8% |
| **+ dead reckoning (50 m)** | **0,31 GiB** | **10 MiB** | **1,4%** |

**A nagyságrendi nyereség nem a formátumból jön, hanem a szűrésből.** A
22,2 GiB → 0,31 GiB útból a formátum és a dead reckoning együtt kb. hatszoros,
a maradékot az adja, hogy nem tároljuk azt, ami nem kell (a sorok ~70%-a a
bounding boxon kívül esik, és ~26 oszlopból 6 kell).

**Ez a két sor NEM ugyanazt tárolja, mint a fenti táblázat.** Bounding
boxra szűrt és 6 oszlopos — teljes lefedettséghez vagy a többi oszlophoz nem
elég. Egy táblázatba keverve azt a hamis látszatot keltené, hogy ugyanabból a
tartalomból lett 70-szer kisebb.

| szám | jelentés | szkript | dátum |
|------|----------|---------|-------|
| 46,9 GiB | **átmeneti** helyigény a konverzió alatt (ZIP + Parquet egyszerre) | meret_becsles.py | 2026-09-21 |
| ~35 perc | becsült CPU-idő a hónap Parquetté alakítására (31 × 66 mp) | benchmark alapján | 2026-09-21 |

**Korlátok:**
- A tárolt méretek **két napon** (07-15, 07-16) mért arányokból jönnek.
- A dead reckoning aránya **egyetlen napon** (07-15) mért, ráadásul az egyik
  legforgalmasabb napon — ha a bounding boxba eső sorok aránya napról napra
  változik, ez a sor tér el a legjobban.
- A **zstd vs snappy** különbség a teljes fájlra **továbbra sincs lemérve**;
  a Parquet-sor snappy-vel készült. Zstd-vel várhatóan kisebb, de nem mértük.

## Duplikált sorok a forrásadatban (2026-07-15)

Forrás: közvetlen mérés a `data/aisdk-2026-07-15.zip` nyers CSV-jén és a
származtatott Parqueten, 2026-09-21.

**A forrásfájl sorainak több mint fele bitre azonos ismétlés.** Ugyanazt az
AIS-adást több parti vevőállomás is veszi, és a napi fájl mindegyik vételt
külön sorként tartalmazza — megkülönböztető mező nélkül.

| szám | jelentés | forrás | dátum |
|------|----------|--------|-------|
| 55,9% | a nyers CSV sorai közül **mind a 26 oszlopban** azonos (első 400 000 sor) | közvetlen mérés | 2026-09-21 |
| 56,2% | ismétlődő (MMSI, időbélyeg) pár a bounding boxban | közvetlen mérés | 2026-09-21 |
| 56,0% | ebből **teljesen azonos** sor (pozíció, sebesség, irány is) | közvetlen mérés | 2026-09-21 |
| 0,1% | azonos időbélyeg, de eltérő pozíció/sebesség (13 499 sor) | közvetlen mérés | 2026-09-21 |
| 10 860 221 → **4 759 634** | sor a bounding boxban dedup. előtt/után | hajo_statisztika.py | 2026-09-21 |

**Ez a forrásban van, nem a feldolgozásunkban.** Ellenőrizve a nyers CSV-n,
mindenféle saját szűrés előtt.

A duplikálás aránya **típusonként erősen eltér** — ezért torzítja a
megoszlásokat:

| csoport | duplikátum-arány |
|---|---|
| Tanker | 70,5% |
| Teherhajó | 68,8% |
| Személyszállító | 60,0% |
| Halászhajó | 56,7% |
| Szolgálati | 53,1% |
| **Kedvtelési** | **40,9%** |

Valószínű magyarázat (nem mértük, ezért nem állítjuk biztosra): a Class A
jeladók nagyobb teljesítménnyel és magasabb antennáról sugároznak, így több
parti állomás veszi őket, mint a kis Class B készülékeket.

**Mit érint és mit nem:**
- **Érinti** minden üzenetszám-alapú arányt (ld. a fenti áthúzott táblázatot).
- **Nem érinti** az egyedi hajószámokat, az óránkénti hajószámokat, a
  napszaki ingadozást, az AIS-osztály megoszlását, sem a Kiel-hipotézis
  eredményeit — azok mind egyedi MMSI-t számolnak.

**Módszertani eltérés:** a `hajo_statisztika.py` a nyers CSV-n deduplikál
(bounding box-szűrés **előtt**), egy független ellenőrző mérés a már
szűrt Parqueten. A kettő 30 sorban tér el (4 759 634 vs 4 759 664, 0,0006%):
azok a sorok, amelyeknek azonos az (MMSI, idő) párja, de az egyik pozíciója a
boxon belül, a másiké kívül esik. Nagyságrendileg jelentéktelen.

### A tömörítési arány felbontása (2026-07-15, bbox, 6 oszlop, zstd)

A korábbi 6,39×-es szám olyan adaton mértük, ami 56% duplikátumot
tartalmazott. Lebontva:

| lépés | méret | arány az eredetihez |
|---|---|---|
| eredeti | 84,3 MiB | 1,00× |
| csak deduplikálva (**veszteségmentes**) | 56,1 MiB | 1,50× |
| eredeti + dead reckoning 50 m (a korábbi szám) | 13,2 MiB | 6,37× |
| **deduplikálva + dead reckoning 50 m** | **10,8 MiB** | **7,79×** |

| szám | jelentés | dátum |
|------|----------|-------|
| 1,50× | a **deduplikáció** önmagában (veszteségmentes) | 2026-09-21 |
| **5,19×** | a **dead reckoning** önmagában, már deduplikált adaton | 2026-09-21 |
| 7,79× | a kettő együtt (1,50 × 5,19 = 7,79) | 2026-09-21 |

**A korábbi 6,39× nem volt „felfújva" annyira, mint a sorszámok sugallnák.**
A zstd a bitre azonos sorokat eleve jól tömöríti, ezért a dedup bájtban csak
1,50×-et hoz, nem 2,27×-et (ami a sorszámból jönne). A dead reckoning tiszta
adaton **5,19×** — ez a módszer valódi hozzájárulása.

**Gyakorlati következmény:** érdemes **előbb deduplikálni, aztán** dead
reckoninget futtatni: 7,79× vs 6,37×, és a dedup veszteségmentes. A
tömörítési lánc sorrendje tehát nem mindegy.

**Még nem mért:** hogy a napi fájl egészére (nem csak a bounding boxra)
ugyanennyi-e a duplikátum-arány; a mérés a teljes nyers CSV első 400 000
sorára és a bbox-szűrt teljes napra készült.

## Külső referenciaadat: IMF PortWatch chokepoint-forgalom

Forrás: `portwatch_letoltes.py` (mind a 28 chokepoint), kimenet
`data/portwatch_chokepoints.csv`, lefuttatva 2026-09-22.
Eredeti forrás: IMF PortWatch, `Daily_Chokepoints_Data` FeatureService.

| szám | jelentés | szkript | dátum |
|------|----------|---------|-------|
| 78 764 | sor összesen (28 chokepoint × napok) | portwatch_letoltes.py | 2026-09-22 |
| 28 | chokepoint (tengeri szoros/csatorna) a teljes adathalmazban | portwatch_letoltes.py | 2026-09-22 |
| 2019-01-01 – 2026-09-13 | lefedett időtartomány | portwatch_letoltes.py | 2026-09-22 |
| 7 673 KB | a teljes CSV mérete | portwatch_letoltes.py | 2026-09-22 |

**Módszertani korlát:** a PortWatch a dán vizeken csak az **Oresund**-ot
(`chokepoint10`) követi, a Nagy-Balti-övet és a Kis-Balti-övet nem. A saját
bounding boxunk (54,5–56,5°É, 10,0–13,0°K) mindhárom átjárót lefedi, ezért a
saját számolt tanker-forgalmunk strukturálisan nagyobb kell legyen, mint a
PortWatch Oresund-értéke — ez nem hiba, hanem eltérő területi lehatárolás.

**Nem ellenőrzött, csak feltételezés:** a legutóbbi kb. 2–3 hét (2026-09-22-i
állapot szerint) feltűnően alacsony értékeket mutat a korábbi hónapokhoz
képest — valószínűleg feldolgozási késés a PortWatch oldalán, nem valódi
forgalomesés. Független forrásból nem ellenőrizve.

## H3 térbeli index hatása a tárolásra és a lekérdezésre (2026-07-15)

Forrás: `h3_tarolas.py`, kimenet `outputs/h3_tarolas.csv`, lefuttatva
2026-09-24, két független futás. Bemenet: a vizsgált terület 10 860 221
pozíciója (6 oszlop). Minden változat azonos adatot, zstd kódeket és
100 000 soros sorcsoportot használ; csak a sorrend és a `h3` oszlop tér el.
H3-felbontás: 8 (~0,74 km²/cella), a nap során 32 214 különböző cella.

Vizsgálati lekérdezések:
- térbeli: a Nagy-Balti-híd környéke (É 55,28–55,40, K 10,85–11,15) –
  189 egyedi hajó, 350 049 sor;
- időbeli: 09:00–10:00 – 574 394 sor;
- óránkénti egyedi hajószám (a forgalmi kiértékelés mutatója).

Mind a négy változat mindhárom lekérdezésre **azonos eredményt** adott.

Determinisztikus mérőszámok (a két futásban bájtra azonosak):

| változat | méret | sorcsoport | térbeli lekérdezésnél átugorható | időbelinél átugorható |
|---|---|---|---|---|
| alap (hajó, idő sorrend) | 68,7 MiB | 109 | 1 | 0 |
| alap + `h3` oszlop | 70,0 MiB (+1,9%) | 109 | 1 | 0 |
| **H3 szerint rendezve** | 76,7 MiB (+11,6%) | 109 | **94** | 0 |
| **idő szerint rendezve** | 83,9 MiB (+22,1%) | 109 | 0 | **102** |

Lekérdezési idők, medián ms (5 ismétlés, meleg gyorsítótár; két futás
értékei):

| változat | térbeli | térbeli `h3` cellalistával | időbeli | óránkénti |
|---|---|---|---|---|
| alap | 115 / 117 | – | 63 / 65 | 170 / 171 |
| alap + `h3` | 112 / 125 | 135 / 161 | 65 / 67 | 174 / 229 |
| H3 szerint rendezve | **21 / 25** | 22 / 23 | 68 / 80 | 178 / 175 |
| idő szerint rendezve | 184 / 189 | – | **8 / 7** | 163 / 163 |

**Megállapítások:**
- **A H3 szerinti rendezés a térbeli lekérdezést kb. 5×-ösére gyorsítja**
  (115 → 21–25 ms), mert a 109 sorcsoportból 94-et a min/max statisztika
  alapján be sem kell olvasni.
- **Az idő szerinti rendezés az időbeli lekérdezést kb. 8×-osára gyorsítja**
  (63 → 7–8 ms), 102 sorcsoport átugrásával – a térbelit viszont lassítja.
- **Nincs mindkettőre optimális sorrend:** a tárolási sorrend eldönti, melyik
  lekérdezéstípus lesz gyors. A választás a várható munkaterheléstől függ.
- **A nyereség a rendezésből jön, nem magából a `h3` oszlopból.** Rendezett
  adaton a cellalistás szűrés nem gyorsabb a sima szélesség–hosszúság
  szűrésnél (22–23 vs. 21–25 ms), rendezetlenen pedig lassabb. A H3 szerepe
  az, hogy jó **rendezési kulcs**: a térben közeli pontokat egy sorcsoportba
  gyűjti.
- **Ára a méret:** az eredeti (hajó, idő) sorrend tömörít a legjobban, mert
  egy hajó egymást követő pozíciói alig térnek el. A H3-rendezés +11,6%-kal,
  az időrendezés +22,1%-kal nagyobb fájlt ad. Maga a `h3` oszlop +1,9%.
- Az óránkénti mutató (teljes beolvasás) a sorrendtől gyakorlatilag
  független.

**Korlátok:** egyetlen nap, egyetlen vizsgálati terület, meleg gyorsítótár.
Az időmérések futásonként akár ~30%-ot is szórnak (pl. az `alap + h3`
óránkénti értéke: 174 vs. 229 ms), ezért csak a többszörös különbségek
értelmezhetők; a méret és az átugorható sorcsoportok száma determinisztikus.
A H3-cellák kiszámítása 20–23 mp a 10,86 millió pontra (egyszeri költség).
