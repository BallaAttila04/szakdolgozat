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

### A H3-rendezés haszna a lekérdezett terület méretének függvényében

Forrás: `h3_teruletmeret.py`, kimenet `outputs/h3_teruletmeret.csv` és
`outputs/h3_teruletmeret.png`, lefuttatva 2026-09-24, két futás. Ugyanaz a
lekérdezés egyre nagyobb, azonos középpontú (É 55,34 / K 11,00) területen, a
`h3_tarolas.py` változatain. Minden változat minden területre azonos
eredményt adott.

A beolvasandó sorcsoportok száma (109-ből) determinisztikus, a két futásban
azonos:

| terület | a napi sorok aránya | eredeti sorrend | H3 szerint | idő szerint | H3-gyorsulás (2. futás) |
|---|---|---|---|---|---|
| 5 km² | 0,07% | 107 | **11** | 109 | 5,6× / 5,5× |
| 31 km² | 0,86% | 108 | 13 | 109 | 4,2× / 4,9× |
| 124 km² | 1,43% | 108 | 14 | 109 | 5,9× / 5,0× |
| 496 km² | 3,99% | 108 | 16 | 109 | 6,7× / 4,1× |
| 1 983 km² | 8,24% | 108 | 19 | 109 | 3,8× / 3,4× |
| 7 931 km² | 19,07% | 109 | 44 | 109 | 2,3× / 2,0× |
| 27 138 km² | 62,98% | 109 | **87** | 109 | 1,2× / 1,1× |

**Megállapítás:** a H3-rendezés haszna a terület növelésével csökken. Amíg a
lekérdezett terület a napi adat néhány százalékát tartalmazza, a sorcsoportok
80–90%-át át lehet ugrani, és a lekérdezés 4–6× gyorsabb. A napi adat ötödénél
nagyobb területen a nyereség 2× alá esik, kétharmadnál gyakorlatilag eltűnik.
Az eredeti és az idő szerinti sorrendnél területmérettől függetlenül szinte
minden sorcsoportot be kell olvasni.

**Korlát:** az egyes időmérések nem monotonok (pl. 4,2× → 5,9× → 6,7×), ez
mérési szórás; a sorcsoportszám monoton. Egyetlen középpont, egyetlen nap.

## Kapuvonal-metrika: kereskedelmi átkelések a dán szorosokon

Forrás: `kapuvonal.py` az 5 letöltött napra, kimenet
`outputs/kapuvonal_atkelesek.csv` (1 258 átkelés) és
`outputs/kapuvonal_napi.csv`, lefuttatva 2026-09-24.

Módszer: két kapuvonal szélességi körként a szorosokon keresztben
(Nagy-Balti-öv: É 55,40, K 10,60–11,35; Øresund: É 56,07, K 12,40–12,85 – a
Helsingør–Helsingborg komp útvonala alatt). A vonalak partról partra érnek,
ezt az adatból ellenőriztük. H3-folyosó (8-as felbontás, a vonal menti cellák
két gyűrűnyi környezete: 314, ill. 194 cella) szűri a vizsgált pozíciókat.
Átkelés: egy hajó két egymást követő pozíciója a vonal két oldalán van,
legfeljebb 10 perc különbséggel. Az átkelésfelismerés hét szintetikus
esetre (átkelés, vételkiesés, visszafordulás, oda-vissza, duplikátum, pontosan
a vonalra érkezés) helyes eredményt adott. A Kis-Balti-öv a vizsgált területen
kívül esik.

### Összevetés az IMF PortWatch Oresund-számával

| nap | saját: tanker | saját: teher | saját: össz. | PortWatch: tanker | PortWatch: össz. | arány |
|---|---|---|---|---|---|---|
| 2026-07-08 | 11 | 34 | 45 | 8 | 31 | 1,45 |
| 2026-07-09 | 14 | 48 | 62 | 9 | 41 | 1,51 |
| 2026-07-15 | 17 | 47 | 64 | 10 | 45 | 1,42 |
| 2026-07-16 | 12 | 41 | 53 | 8 | 45 | 1,18 |
| 2026-09-05 | 10 | 25 | 35 | 7 | 32 | 1,09 |

| szám | jelentés |
|---|---|
| **r = 0,82** | napi korreláció, összes kereskedelmi (5 nap) |
| **r = 0,98** | napi korreláció, csak tanker (5 nap) |
| 1,33 (1,09–1,51) | a saját szám átlagosan ennyiszerese a PortWatch-énak |

**Értelmezés:** a két mérés erősen együtt mozog, a saját szám szisztematikusan
magasabb. Egy közel állandó szorzó módszertani eltérésre utal, nem véletlen
hibára. Lehetséges okok (nem ellenőrizve): eltérő kapuhelyzet és -szélesség, a
PortWatch hajólajstromból veszi a típust, a saját mérés az AIS által bejelentett
`Ship type`-ot használja, és a PortWatch kiszűrheti a kisebb hajókat.
**Korlát:** 5 nap, a korreláció ekkora mintán bizonytalan.

### A Kiel-hipotézis újravizsgálata a helyes mérőszámmal

Kereskedelmi (teherhajó + tanker) átkelések, a két kapu együtt, a hibás
2026-07-08-i 11. órát minden napból kihagyva:

| nap | Nagy-Balti-öv | Øresund | összesen |
|---|---|---|---|
| 07-08 (szerda, kontroll) | 47 | 44 | 91 |
| 07-09 (csütörtök, kontroll) | 45 | 62 | 107 |
| **07-15 (szerda, lezárás)** | 51 | 61 | **112** |
| **07-16 (csütörtök, lezárás)** | 43 | 51 | **94** |
| 09-05 (szombat) | 51 | 32 | 83 |

| összehasonlítás | arány |
|---|---|
| szerda: 07-15 / 07-08 | 1,231 (+23,1%) |
| csütörtök: 07-16 / 07-09 | 0,879 (−12,1%) |
| zajszint: 07-09 / 07-08 | 1,176 (17,6%) |
| **lezárási napok / kontrollnapok** | **1,040 (+4,0%)** |

(Teljes napra, a 11. órával: +27,2% / −8,4% / 16,3% zaj / +8,0%.)

**Megállapítás:** a helyes, kereskedelmi átkelésekre szűrt mérőszámmal sem
mutatható ki a lezárás hatása: a két nap együtt +4%, a csütörtök pedig
**kevesebb** a kontrollnál. A korábbi negatív eredmény tehát nem a rossz
mérőszám terméke. Napi kb. 100 kereskedelmi átkelés és kb. 15–18%-os napi
ingadozás mellett egy-egy nap összevetésével csak nagy (kb. 30% feletti) hatás
lenne kimutatható.

**Mellékeredmény:** a szeptemberi szombaton a Nagy-Balti-övön ugyanannyi
kereskedelmi hajó kelt át (51), mint a júliusi hétköznapokon (43–51), miközben
az óránkénti összes hajószám ott fele akkora volt. A korábbi „~2×-es
különbség" tehát valóban a szabadidős hajózásból adódott.

A kereskedelmi hajók közül 481 egyszer, 10 kétszer kelt át ugyanazon a napon
ugyanazon a kapun (visszaút).

### Tanker-merülés kapunként

Forrás: `outputs/kapuvonal_atkelesek.csv` (`merules_m` = a hajó bejelentett
`Draught` értékeinek mediánja), 5 nap, kiértékelve 2026-09-24.

| kapu | tanker-átkelés merüléssel | medián | 90. percentilis | max. | 10 m feletti |
|---|---|---|---|---|---|
| Nagy-Balti-öv | 83 | 9,5 m | 14,7 m | **15,0 m** | **37** |
| Øresund | 64 | 6,0 m | 7,0 m | **8,0 m** | **0** |

**Megállapítás:** az Øresundon egyetlen 8 m-nél mélyebb merülésű tanker sem
kelt át, a Nagy-Balti-övön a tanker-átkelések 45%-a 10 m fölötti merüléssel
történt. A mérés összhangban van azzal, hogy a nagy, rakott tankerek számára a
dán szorosok közül csak a Nagy-Balti-öv elég mély.
**Korlát:** a `Draught` kézzel beállított mező, és a hajó rakott/üres
állapotát nem feltétlenül frissítik.

## Feldolgozó lánc: `pipeline.py` (Parquet-tároló)

Forrás: `pipeline.py --zipbol`, kimenet `outputs/pipeline_napok.csv`, lefuttatva
2026-10-05 az 5 letöltött napon. Tároló: 16 oszlop (amit bármely szkript olvas),
mind a 26 oszlopban bitre azonos sorok összevonva (`dup_db` = példányszám),
H3 (8) oszlop, (h3, ts) rendezés, zstd, 100 000 soros sorcsoport.

| szám | jelentés | szkript | dátum |
|------|----------|---------|-------|
| 140 430 880 | nyers sor az 5 napon (= a ZIP-ek sorszáma, mind validálva) | pipeline.py | 2026-10-05 |
| 70 926 117 | sor a deduplikált tárolóban (5 nap) | pipeline.py | 2026-10-05 |
| 49,5% | bitre azonos duplikátum, 5 nap, teljes fájl | pipeline.py | 2026-10-05 |
| **54,6%** | bitre azonos duplikátum, 2026-07-15, **teljes napi fájl** (eddig nem mért) | pipeline.py | 2026-10-05 |
| 56,03% | ugyanez a bounding boxban (10 860 221 → 4 775 542) – egyezik a korábbi 56,0%-kal | pipeline.py | 2026-10-05 |
| 37,7% – 54,6% | a teljes fájlra vonatkozó duplikátum-arány napi szórása (09-05 – 07-15) | pipeline.py | 2026-10-05 |
| 3 990 MiB → ~~941 MiB~~ → 941,7 MiB | ZIP → Parquet-tároló, 5 nap (**23,6%**); 2. séma: +0,7 MiB a `sorrend` oszlop miatt | pipeline.py | ~~2026-10-05~~ → 2026-10-06 |
| 226,7 MiB | 2026-07-15 a tárolóban (vö. 1 061 MiB: snappy, 26 oszlop, dedup. nélkül) | pipeline.py | 2026-10-05 |
| 126 MiB | DR 50 m-es réteg, 5 nap, teljes terület, 6 oszlop | pipeline.py | 2026-10-05 |
| ~~131 – 348 mp~~ → **196 – 385 mp** | futási idő/nap, meglévő ZIP-ből (~~medián 183 mp~~ → medián 264 mp); a változás oka a `sorrend` oszlop (2. séma), ld. lent | pipeline.py | ~~2026-10-05~~ → 2026-10-06 |
| ~6,0 GiB | csúcsmemória/nap (a beállított 6 GB-os DuckDB-korlát) | pipeline.py | 2026-10-05 |
| ~~6,2 – 14,0 GB~~ → **7,7 – 16,5 GB** | csúcs lemezhasználat/nap (kicsomagolt CSV + DuckDB-lapozás), 2. séma | pipeline.py | ~~2026-10-05~~ → 2026-10-06 |

**Keresztellenőrzés:** a 07-15-i 36 650 571 sor, a 10 860 221 bbox-sor és a
13 387 egyedi MMSI pontosan egyezik a korábbi független mérésekkel; a
tárolóból a korábbi módon képzett bbox/6 oszlop/DR 50 m adat bájtra a régi
56,1 → 10,8 MiB-ot (7,79×, DR önmagában 5,19×) adja.

**Fontos:** a 23,6% NEM vethető össze a „Parquet NEM kisebb a ZIP-nél” korábbi
megállapítással (az snappy, 26 oszlop, duplikátumokkal). A különbség forrása a
deduplikálás, a zstd és az elhagyott 10 oszlop együtt; ezek hatását külön nem
bontottuk fel.

**Módosítás 2026-10-06 – a tároló 2. sémája (`sorrend` oszlop):** a 2. fázis
ellenőrzése kimutatta, hogy az 1. sémából elveszett az azonos (MMSI, ts) párú,
de eltérő pozíciójú sorok forrásbeli sorrendje, ami 8 hamis kapuvonal-átkelést
okozott (1 266 vs. 1 258). A javított séma ezt egy kis egész oszlopban őrzi.
Hatása: Parquet-méret +0,1–0,2 MiB/nap; a DR-réteg pontszáma a 07-15-i napon
3 537 278 → 3 536 660 (a DR az azonos másodpercű pontok sorrendjére érzékeny).
A Parquet-lépés ideje nőtt (a sorszámozáshoz a DuckDB-nek meg kell őriznie a
beolvasási sorrendet), és a csúcs lemezhasználat is (a legnagyobb napon
16,5 GB).

## Kapuvonal-metrika a Parquet-tárolóból (2. fázis ellenőrzése)

Forrás: `kapuvonal.py` a tároló 5 napi Parquet-fájlján, kimenet
`outputs/kapuvonal_napi_parquet.csv`, `outputs/kapuvonal_atkelesek_parquet.csv`,
lefuttatva 2026-10-06.

| szám | jelentés | szkript | dátum |
|------|----------|---------|-------|
| 1 258 = 1 258 | átkelés: ZIP-ből vs. Parquet-tárolóból (2. séma) – **bájtra azonos CSV** | kapuvonal.py | 2026-10-06 |
| ~~1 266~~ | ugyanez az 1. sémájú tárolóból – hibás, a `sorrend` oszlop hiánya miatt | kapuvonal.py | 2026-10-05 |

## Három hónap a Parquet-tárolóban (2026. június–augusztus)

Forrás: `pipeline.py 2026-06-01 2026-08-31 --torol-zip ...`, kimenet
`outputs/pipeline_napok.csv`, lefuttatva 2026-10-06 – 2026-10-09.

| szám | jelentés | szkript | dátum |
|------|----------|---------|-------|
| 92 / 92 | validált nap (a szerveren mind elérhető, hiba 0) | pipeline.py | 2026-10-09 |
| 2 085 308 912 | nyers AIS-sor, 3 hónap | pipeline.py | 2026-10-09 |
| 1 182 974 452 | sor a deduplikált tárolóban | pipeline.py | 2026-10-09 |
| 43,3% | bitre azonos duplikátum, 3 hónap, teljes fájl (napi 35,0–58,8%, medián 39,1%) | pipeline.py | 2026-10-09 |
| 63,9 GiB (65 390 MiB) | nyers ZIP, 3 hónap | pipeline.py | 2026-10-09 |
| **15,1 GiB (15 422 MiB)** | Parquet-tároló, 3 hónap (**23,6%** a ZIP-hez; havonta 23,3–23,9%) | pipeline.py | 2026-10-09 |
| 1,9 GiB (1 940 MiB) | DR 50 m-es réteg, 3 hónap | pipeline.py | 2026-10-09 |
| 4,7 – 5,3 GiB | Parquet-tároló havonta | pipeline.py | 2026-10-09 |

**Futási idő – NEM jellemző szám:** a 3. fázis napi ideje (medián 560 mp,
max. 1 160 mp) egy azóta javított hibát tartalmaz (a hosszan futó folyamat
lassult, ld. naplo 2026-10-09). Friss folyamatban ugyanaz a nap 8,2×
gyorsabb volt (08-28: 638,5 → 78,3 mp Parquet-lépés).

## A napi monitor erőforrásigénye (6a)

Forrás: `szerver_napok.py` (2026-10-05) és `pipeline.py 2026-07-15` négy
beállítással (2026-10-09, `outputs/logs/lemezmeres_0715.log`), friss folyamatban.

| szám | jelentés | szkript | dátum |
|------|----------|---------|-------|
| 48,3 óra (48,3–48,7) | a napi fájl megjelenése a nap vége (UTC) után, 14 + 92 nap HEAD | szerver_napok.py | 2026-10-05 |
| 174 mp / 6,0 GiB / 8,7 GiB | a legnagyobb nap (07-15): idő / csúcsmemória / munkakönyvtár-csúcs, kicsomagolással, 6 GB-os korláttal | pipeline.py | 2026-10-09 |
| 204 mp / 10,6 GiB / 2,5 GiB | ugyanez közvetlen ZIP-olvasással (`--kozvetlen-zip`) – a GitHub-futtató beállítása | pipeline.py | 2026-10-09 |
| ≈ 4,6 GiB | becsült lemezigény a futtatón (lapozás + ZIP + előtöltött ZIP + Parquet) | számolt | 2026-10-09 |
| 16 GB RAM / 14 GB SSD / 6 óra | a nyilvános repó standard Linux runnere (GitHub-dokumentáció) | – | 2026-10-05 |

## Motorok és skálázás a Parquet-tárolón (4. fázis)

Forrás: `skalazas.py` (→ `tarolas_benchmark.py --tarolo-meres`), kimenet
`outputs/skalazas.csv`, `outputs/skalazas.png`, lefuttatva 2026-10-09.
A négy lekérdezés: sorszám, egyedi hajó, bbox-szűrés, óránkénti bbox-bontás;
3 ismétlés mediánja, a négy együtt; minden motor minden méreten azonos
eredményt adott. duckdb 1.5.5, polars 1.44.2 (streaming), pyspark 4.2.0 helyi
mód (JDK 21, 8 GB driver), egy 8 szálas, 16 GB-os laptopon.

| adat | nyers sor | Parquet | DuckDB | Polars | Spark (+ indulás) | DuckDB-CSV | pandas-CSV |
|---|---|---|---|---|---|---|---|
| 1 nap (07-15) | 36,7 M | 227 MiB | 0,51 mp | 0,38 mp | 8,5 mp (+23,5) | 51,3 mp | 113,6 mp |
| 7 nap | 190,0 M | 1,3 GiB | 3,8 mp | 2,9 mp | 22,1 mp (+13,2) | – | – |
| 1 hónap (július) | 739,2 M | 5,3 GiB | 15,0 mp | 12,4 mp | 87,2 mp (+12,2) | – | – |
| 3 hónap (jún–aug) | 2 085,3 M | 15,1 GiB | 42,0 mp | 33,4 mp | 233,4 mp (+16,1) | – | – |

| szám | jelentés | szkript | dátum |
|------|----------|---------|-------|
| 140 / 197 / 377 / 619 MiB | DuckDB csúcsmemória (1 nap … 3 hónap) | skalazas.py | 2026-10-09 |
| 564 / 1 848 / 3 030 / 3 728 MiB | Polars csúcsmemória | skalazas.py | 2026-10-09 |
| 1 603 / 2 502 / 2 882 / 3 589 MiB | Spark csúcsmemória (Python + JVM) | skalazas.py | 2026-10-09 |
| 17× → 5,6× | a Spark lassúsága a DuckDB-hez (1 nap → 3 hónap), session-indulás nélkül | skalazas.py | 2026-10-09 |
| 94,4 mp vs 3,1 mp | `count(DISTINCT MMSI)` 3 hónapon: Spark vs DuckDB | skalazas.py | 2026-10-09 |
| 101× / 225× | a DuckDB-CSV / pandas-CSV lassúsága a DuckDB-Parquethez, 1 nap | skalazas.py | 2026-10-09 |

**Az 1 napos tárolós DuckDB-szám (0,51 mp) nem vethető össze a régi
benchmark 3,10 / 1,64 mp-ével:** az a nyers (26 oszlopos, duplikátumos,
snappy) Parquet volt, egyetlen futás.

**Spark-telepítés:** pip (polars + pyspark + geopandas együtt) 228 mp; hordozható
Temurin JDK 21, 205 MB, 26 mp; winutils az olvasáshoz nem kellett; első
kísérletre működött. Session-indulás 12–39 mp.

### GeoParquet vs. lat/lon Parquet (2026-07-15, 16 638 836 sor)

Forrás: `geoparquet_proba.py`, kimenet `outputs/geoparquet_proba.csv`, 2026-10-09, 5 ismétlés.

| szám | jelentés | szkript | dátum |
|------|----------|---------|-------|
| 274,0 vs 560,6 MiB (**2,05×**) | lat/lon Parquet vs GeoParquet 1.1 (WKB + bbox-oszlop) | geoparquet_proba.py | 2026-10-09 |
| 10,2 vs 39,8 mp | írás (a GeoParquetnél a GeoDataFrame-építéssel) | geoparquet_proba.py | 2026-10-09 |
| 30,7 vs 39,1 ms | térbeli lekérdezés DuckDB-vel: lat/lon vs GeoParquet bbox-oszlop | geoparquet_proba.py | 2026-10-09 |
| 245,5 ms | ugyanez GeoPandasszal (`read_parquet(bbox=...)`) | geoparquet_proba.py | 2026-10-09 |
| 1,57 vs 16,1 mp | teljes beolvasás: pandas vs GeoPandas | geoparquet_proba.py | 2026-10-09 |

## Napi forgalmi monitor (6b–6c)

Forrás: `monitor.py` (`outputs/monitor/`), lefuttatva 2026-10-09. Sorozat: a
kereskedelmi (teher + tanker) kapuvonal-átkelések naponta; alapszint: az előző
4 hét azonos napjának mediánja; küszöb: 2 × 1,4826 × MAD az idősor relatív
eltéréseiből.

| szám | jelentés | szkript | dátum |
|------|----------|---------|-------|
| 93 nap (06-01 – 09-05), 72 alapszinttel | a visszamenőleges futás idősora | monitor.py | 2026-10-09 |
| **11,8%** | a két kapu együttes napi kereskedelmi átkelésének robusztus szórása (a korábbi egypáros 17,6% helyett; medián abszolút eltérés 7,8%, p90 22,0%) | monitor.py | 2026-10-09 |
| 17,8% / 12,8% | ugyanez a Nagy-Balti-övön / az Øresundon | monitor.py | 2026-10-09 |
| ±23,5% / ±35,7% / ±25,7% | jelzési küszöb (Mindkét kapu / Nagy-Balti-öv / Øresund), 93 napos idősor | monitor.py | 2026-10-09 |
| 8,3% / 5,6% / 12,5% | a jelzett napok aránya (ugyanebben a sorrendben) | monitor.py | 2026-10-09 |
| +33,0% (117 vs 88,0) – szokatlanul magas | 2026-07-15, mindkét kapu; a 72 napból a 2. legnagyobb eltérés | monitor.py | 2026-10-09 |
| −7,1% (98 vs 105,5) – normál | 2026-07-16, mindkét kapu | monitor.py | 2026-10-09 |
| 124 nap, 2 882 sor | a monitortábla a helyi napi futás után (06-01 – 10-06) | napi_futas.py | 2026-10-09 |
| 96 – 141 mp, ~~8,6 – 10,1 GiB~~ → **8,4 – 9,9 GiB** | napi idő és csúcsmemória a napi futásban (`--kozvetlen-zip`); a régi érték MiB-ból GiB-ra váltásnál hibás volt (8 626–10 128 MiB ÷ 1024) | napi_futas.py | 2026-10-09 |

A küszöbök az idősor bővülésével változnak (117 napon: ±22,7% / ±35,3% /
±24,9%; 124 napon az oldal szerint ±23,5% / ±35,6% / ±25,4%).

## Mérés a GitHub-futtatón (6a ellenőrzése)

Forrás: GitHub Actions, `napi_monitor.yml` mérési mód (`meresi_nap=2026-07-15`),
futás <https://github.com/BallaAttila04/szakdolgozat/actions/runs/37910491337>,
2026-10-09, `ubuntu-24.04`; `pipeline.py --felulir --kozvetlen-zip --dr-kihagy`.

| szám | jelentés | szkript | dátum |
|------|----------|---------|-------|
| 4 CPU, 15 989 MiB RAM | a futtató (nproc, free -m) | napi_monitor.yml | 2026-10-09 |
| 87 777 MB | szabad lemez a mérés indulásakor (df) – a dokumentált 14 GB-nál jóval több | napi_monitor.yml | 2026-10-09 |
| 49 mp | a 955,7 MB-os napi ZIP letöltése | pipeline.py | 2026-10-09 |
| **130,2 mp** | a legnagyobb nap feldolgozása (sorszámlálás 17,0 + Parquet 111,5 mp) | pipeline.py | 2026-10-09 |
| **12 539 MiB** | csúcsmemória (helyben ugyanez 10 871 MiB) – a tartalék ~3,4 GiB | pipeline.py | 2026-10-09 |
| 2 761 MiB | csúcs lemezhasználat a letöltött ZIP-en felül | pipeline.py | 2026-10-09 |
| 54,6% / 16 638 836 / 227,0 MiB | duplikátum-arány / dedup. sor / Parquet – egyezik a helyi futással | pipeline.py | 2026-10-09 |
| 87,2 mp | ugyanez, 2. futás (<https://github.com/BallaAttila04/szakdolgozat/actions/runs/37914275224>, a javított kóddal, zöld): letöltés 50,9, sorszámlálás 11,4, Parquet 74,6 mp – a két futás közti eltérés a futtatógépek szórása | pipeline.py | 2026-10-09 |
| 12 565 MiB / 2 699 MiB | 2. futás: csúcsmemória / munkakönyvtár-csúcs (szabad lemez a végén 86 580 MB) | pipeline.py | 2026-10-09 |

## Megrakottsági mutató (7. fázis)

Forrás: `megrakottsag.py` (`--lefedettseg`, `--szamol`, `--teszt`) és a
`monitor.py` napi frissítése, kimenet `outputs/monitor/megrakottsag_napi.csv`,
`outputs/megrakottsag_*.csv`, `outputs/megrakottsag_hisztogram.png`, lefuttatva
2026-10-09, a 2026-06-01 – 2026-10-06 folytonos, 128 napos idősoron.

| szám | jelentés | szkript | dátum |
|------|----------|---------|-------|
| 1,0 ≤ d < 25,5 m | hihető merülés (az 1 m alatti sáv: tanker 1 343 sor a 208,7 M-ból; 25,5 = telített érték) | megrakottsag.py | 2026-10-09 |
| 96,5% / 97,3% | hihető és változó merülésű átkelés, tanker / teher, mindkét kapu – **K3 TELJESÜL** (≥ 80%) | megrakottsag.py | 2026-10-09 |
| 3 737 / 9 232 | tanker- / teher-átkelés (mindkét kapu) | megrakottsag.py | 2026-10-09 |
| 89,2% / 92,0% | a kapun átkelő hajók közül változó merülésű, tanker (1 045 / 1 172) / teher (2 471 / 2 685) | megrakottsag.py | 2026-10-09 |
| 3,3 m / 2,4 m | a merülés terjedelmének mediánja hajónként, tanker / teher | megrakottsag.py | 2026-10-09 |
| **0,815 / 0,787** | megrakott-küszöb (Otsu) a relatív merülésre, tanker / teher | megrakottsag.py | 2026-10-09 |
| 57,9% / 71,0% | megrakott átkelés aránya, tanker / teher (értékelhető átkelésekből) | megrakottsag.py | 2026-10-09 |
| 68,8% / 43,0% | megrakott tanker-arány: Nagy-Balti-öv / Øresund | megrakottsag.py | 2026-10-09 |
| 10 / 10 | szúrópróba: relatív merülés a nyers tárolóból függetlenül visszaszámolva | ellenőrző szkript | 2026-10-09 |
| ±13,1% / ±20,1% / ±20,5% | jelzési küszöb (7 napos gördülő): megrakott tanker / teher / tanker-volumen | monitor.py | 2026-10-09 |
| 7 / 101 nap | téves riasztás, megrakott tanker (júl. 2, aug. 2, szept. 3); teher 0, volumen 1 | megrakottsag.py | 2026-10-09 |
| 13/13, 13/13, 12/13 | mesterséges 40 / 30 / 20%-os csökkenés észlelése 14 napon belül | megrakottsag.py | 2026-10-09 |
| 2 / 3 / 4 nap | ugyanez, a jelzés napjának mediánja (0 = a hét első napja) | megrakottsag.py | 2026-10-09 |

**Korábbi szám pontosítva (nem áthúzva, mert érvényes marad):** „Øresund: 0 db
8 m-nél mélyebb tanker” (2026-09-24, 5 nap). A 128 napon az Øresund-kapun 55
tanker-átkelés mélyebb 8 m-nél (max. 11,7 m); közülük csak 4 ment le a Drogden
alá (É 55,55°, legmélyebb 8,8 m), a többi a koppenhágai kikötőknél megállt.
Az *átmenő* forgalomra a korábbi állítás igaz; a kapu a kikötőbe tartó
forgalmat is számolja.

**Monitor-küszöbök a folytonos idősoron:** a 09-01 – 09-04 napok hiányoztak
(ld. napló); pótlás után (128 nap) a kapuvonal-jelzés küszöbe ~~±23,5%~~ →
**±23,0%** (mindkét kapu), ~~±35,6%~~ → ±34,4% (Nagy-Balti-öv), ~~±25,4%~~ →
±25,8% (Øresund).

## A dolgozat számai a fagyasztott állapotban (2026-10-22, `f8603b3`)

Forrás: a `szamok-ujraszamolasa` ellenőrzési lánc (kereső → független adatellenőrzés → szövegellenőrzés), 2026-10-25/26. A fagyasztás leírása: `dolgozat/munka/fagyasztas.md`; a dolgozatba beírt 250 csere: `dolgozat/munka/valtozasok.json`. Ha egy szám megváltozott, a korábbi érték a „korábban:” után szerepel (a 2026-10-12-i, 131 napos állapot vagy a régi PortWatch-fájl). A teljességi kritika és a szamok.md-összevetés ügynöke a munkamenet-limit miatt nem futott le; a meglévő, felülírt sorok áthúzása ezért még hátravan.

### Backtest

| szám | jelentés | szkript / forrás | dátum |
|------|----------|------------------|-------|
| 92,0% | Kiel-méretű (2 nap, ±30%) szintetikus esemény észlelési aránya a „Mindkét kapu” sorozaton, k = 2, saját ablak (173/188), 95% CI 88,3–95,7% (korábban: ~~90,7%~~) | outputs/backtest/bootstrap.csv (Mindkét kapu, 'eszleles, Kiel-eset (2 nap, ±30%)'); injektalas.csv R1 param 2.0, ablak sajat, m 0.3, L 2: 89/94 + 84/94; fagyasztott állapot 2026-10-22, futtatva 2026-10-25 | 2026-10-25 |
| 432 + 414 jelzés-sor, 0 eltérés | a backtest reprodukciója a fagyasztott monitorállapoton (korábban: ~~393 + 375 (a 131 napos állapoton, 4.2 [672]; ez nem a 2.1 része)~~) | outputs/backtest/reprodukcio.csv | 2026-10-25 |
| 432 + 414 sor, 0 eltérés | a backtest-motor a fagyasztott monitor jelzés-tábláit eltérés nélkül reprodukálja (korábban: ~~393 + 375 (a 4.2 K7-cellájában, nem a 2.1-ben)~~) | outputs/backtest/reprodukcio.csv | 2026-10-25 |
| ≥ 90% | a backtest munkapont-kritériuma (a [350] marad) | outputs/logs/backtest_fagyasztas_2026-10-22.log 185. sor; outputs/backtest/munkapont.csv | 2026-10-25 |
| 92,0% (173/188) [88,3; 95,7] | Kiel-méretű (2 nap, ±30%) esemény észlelése, Mindkét kapu, R0 walk-forward k = 2, saját ablak (korábban: ~~90,7% (147/162, 125f554)~~) | outputs/backtest/injektalas.csv (−1: 89/94, +1: 84/94); szabalyok.csv 0,9202; bootstrap.csv CI 0,883–0,9574 | 2026-10-25 |
| 92,0% | Kiel-méretű esemény észlelése, Mindkét kapu, bővülő walk-forward (173/188) (korábban: ~~90,7%~~) | outputs/backtest/bootstrap.csv; injektalas.csv | 2026-10-25 |
| 15 naptári hét (n = 102 nap) | Walk-forward téves riasztási értékelés heti blokkjai (korábban: ~~13 (n = 89)~~) | outputs/backtest/bootstrap.csv blokkok | 2026-10-25 |
| 2,06 / 3,24 / 2,94 | Téves riasztás / 30 nap a három kapusorozaton (a [860] '2–4' tartományán belül) (korábban: ~~2,36 / 3,71 / 3,37~~) | outputs/backtest/bootstrap.csv | 2026-10-25 |
| 2,06 / 3,24 / 2,94 | Téves riasztás / 30 nap a három kapusorozaton (a [860] „2–4” tartományán belül) (korábban: ~~2,36 / 3,71 / 3,37~~) | outputs/backtest/bootstrap.csv | 2026-10-25 |
| 432 + 414; 1 151; 264 915; 281 799 | reprodukció: jelzéssorok; megrakottsági napi tábla; nulla-injektálás; előretekintés-teszt (mind 0 eltérés) (korábban: ~~393 + 375; 1 047; 230 517; 229 824~~) | outputs/backtest/reprodukcio.csv | 2026-10-25 |
| 102 / 96 nap | walk-forward értékelt napok, kapu- / megrakottsági sorozatok (korábban: ~~89 / 83~~) | outputs/backtest/walkforward.csv napok (bovulo, min. 21 nap) | 2026-10-25 |
| 2,06 / 3,24 / 2,94; 4,06 / 0,94 / 0,94 | téves riasztás / 30 nap, R0, bővülő walk-forward (korábban: ~~2,36 / 3,71 / 3,37; 2,89 / 0,72 / 1,08~~) | outputs/backtest/walkforward.csv fa30_wf; bootstrap.csv | 2026-10-25 |
| 68,6% / 86,7% / 92,0% / 65,3% / 47,2% / 39,8% | Kiel-méretű esemény észlelése sorozatonként (korábban: ~~69,1% / 86,4% / 90,7% / 56,0% / 47,3% / 42,7%~~) | outputs/backtest/injektalas.csv L=2, m=0,3, R0 sajat (n = 188 / 176) | 2026-10-25 |
| 17 400 / 504 900 | injektált esemény / szabálykimenet (korábban: ~~15 060 / 431 190~~) | outputs/logs/backtest_fagyasztas_2026-10-22.log (újrafuttatás log 83. sora) | 2026-10-25 |
| R4 48,7% vs. R0 50,0%; 0,3 vs. 2,7 | CUSUM és R0 a tartós, gyenge eseményen és téves riasztásban (Mindkét kapu, közös ablak); a „legalább olyan jól” már nem igaz (korábban: ~~56,5% vs. 53,2%; 0,4 vs. 3,2~~) | outputs/backtest/szabalyok.csv kozos (teljes pontosság: 0,486667 / 0,500000; 0,340909 / 2,727273) | 2026-10-25 |
| 88 nap | a szabályváltozatok közös értékelési ablaka (július 27-től) (korábban: ~~75 nap~~) | outputs/backtest/szabalyok.csv ablak=kozos | 2026-10-25 |
| k = 2,25: 91,0%, 2,06; k = 2: 92,0%, 2,94; Øresund k = 1,5: 6,47; Nagy-Balti-öv legjobb 89,4% | munkapont (korábban: ~~90,1%, 2,36; 90,7%, 3,37; 6,40; 88,8%~~) | outputs/backtest/munkapont.csv; roc.csv; injektalas.csv | 2026-10-25 |

### Egyéb

| szám | jelentés | szkript / forrás | dátum |
|------|----------|------------------|-------|
| 0,736 | napi Pearson-r: a monitor Øresund-kapuja (kereskedelmi) és a PortWatch, 128 napon (nem a 2.1-ben szerepel, hanem a 4.5-ben és az 1.1.5-ben) (korábban: ~~0,720 (105 nap, r = 0,7204)~~) | ugyanaz a saját számítás, Øresund oszlop: r = 0,7363 | 2026-10-25 |
| 4 CPU, 16 GB, 14 GB SSD; 6 óra/feladat; díjmentes | a GitHub standard Linux-futtató korlátai ([327], K10), változatlan | WebFetch 2026-10-25: docs.github.com/en/actions/reference/runners/github-hosted-runners („4”, „16 GB”, „14 GB”, „free and unlimited on public repositories”); docs.github.com/en/actions/reference/limits („up to 6 hours of execution time”) | 2026-10-25 |
| 4,55% | normális eloszlásnál a \|z\| > 2 napok várt aránya (korábban: ~~5% (kerekítve)~~) | 2 · (1 − scipy.stats.norm.cdf(2)) = 0,045500 | 2026-10-25 |
| 92,0% (173/188) | Kiel-méretű (2 nap, ±30%) esemény észlelése, Mindkét kapu, R0 walk-forward k = 2, saját ablak (korábban: ~~90,7% (147/162, 125f554)~~) | injektalas.csv (R0 (k=2), m 0.3, L 2, sajat: 89/94 + 84/94); log: 0.920 [0.883; 0.957] | 2026-10-25 |
| 1,29 (0,98–1,66) | saját/PortWatch napi arány átlaga (min–max), Øresund kereskedelmi (korábban: ~~1,29 (0,98–1,65) (105 nap); 1,33 (5 nap)~~) | újraszámolás: 1.2922, 0.98, 1.6552 | 2026-10-25 |
| 127 / 128 nap | napok, amelyeken az arány ≥ 1 (a „szisztematikusan” alátámasztása) | saját újraszámolás: (arany<1).sum()=1 | 2026-10-25 |
| heti r 0,971 (19 hét) – nem használható; 0,755 (18 teljes hét) | heti r, Øresund kereskedelmi; a 19. hét (10-05 – 10-06) csak 2 napos, ez torzít (korábban: ~~0,760 (15 hét)~~) | saját: resample('W-SUN').sum(); size()==7 szűréssel 0.7548; utolsó hét 2 nap | 2026-10-25 |
| 0,720 / 1,286 a 105 napon az új fájllal | az új PortWatch-fájl a régi ablakon a régi értékeket adja, tehát a változás oka a 23 új nap | saját: index<=2026-09-13 → r 0.72036, arány 1.28595 (a régi 125f554-es fájllal egyezik) | 2026-10-25 |
| 0,737 km²; 122; 12; hatszög max/min 1,99; ötszöggel 2,39 | H3 res-8 átlagos terület, alapcellák, ötszögek, területarány | h3 4.5.0: average_hexagon_area(8)=0.73733; get_res0_cells 122; get_pentagons(8) 12, 0.37205 km²; mintavételes hatszög min 0.4465, max 0.8896 | 2026-10-25 |
| 127 / 128 nap | napok, amelyeken az Øresund/PortWatch arány ≥ 1 | (arany<1).sum()=1 | 2026-10-25 |
| r = 0,892; arány 1,17 | Drogden alatti kapu kereskedelmi vs. PortWatch n_total, 128 nap (korábban: ~~0,905; 1,15 (105 nap)~~) | újraszámolás: r 0.8916, arány 1.1661 (0.975–1.4667) | 2026-10-25 |
| heti r = 0,755 (18 teljes hét); fájlban 0,971 (19 hét) | heti r Øresund; a 19. hét csak két nap (10-05 – 10-06; AIS 108, PW 87), ezért a fájlbeli érték nem használható (korábban: ~~0,760 (15 hét)~~) | resample('W-SUN').sum(), szűrés size()==7 | 2026-10-25 |
| heti r = 0,827 (18 teljes hét); fájlban 0,979 | heti r, Drogden-kapu | ugyanaz a számítás a 'Øresund – Drogden' oszlopra | 2026-10-25 |
| 0,720 / 1,286 a régi 105 napon | ellenőrzés: az új PortWatch-fájl a régi ablakon a régi értékeket adja, a változást az új napok okozzák | index<=2026-09-13: r 0.7204, arány 1.2860 (0.98–1.6452); Drogden r 0.9048, arány 1.1511 | 2026-10-25 |
| 0,4465 / 0,8896 km²; 1,992×; ötszög 0,372 km²; 2,39× | H3 res-8 hatszög min/max területe és aránya; az ötszög területe; max hatszög/ötszög | h3 4.5.0; h3geo.org restable res 8: 0.446526174 / 0.889635157 / 1.992347 / 0.372048038 | 2026-10-25 |
| 0,737 km²; 122; 12 | H3 res-8 átlagos hatszögterület; res-0 cellák száma; ötszögek | h3 4.5.0: average_hexagon_area(8)=0.73733; len(get_res0_cells())=122; len(get_pentagons(8))=12 | 2026-10-25 |
| 28 | a PortWatch chokepoint-fájlban szereplő szorosok száma | portname.nunique() a régi és az új fájlban is 28 | 2026-10-25 |
| 00:18–00:44 UTC (00:17:52 – 00:43:54), D+3 | a napi fájl megjelenési ideje (Last-Modified), 104 elérhető nap (korábban: ~~00:18–00:42~~) | outputs/szerver_keses.csv (12 elérhető a 14-ből) + outputs/szerver_napok_jun_aug.csv (92), last_modified_utc | 2026-10-25 |
| 48,30 – 48,73 óra (medián 48,34) | a fájl késése a nap végéhez képest | ugyanaz, keses_ora | 2026-10-25 |
| 4,55% | a téves jelzések aránya normális eloszlásnál ±2 szórásos küszöbbel (korábban: ~~mintegy 5%~~) | scipy.stats.norm: 2*norm.sf(2) = 0,0455003 | 2026-10-25 |
| 0,7373 km² | átlagos H3-cellaterület 8-as felbontáson | h3.average_hexagon_area(8, 'km^2') | 2026-10-25 |
| 203,6 mp / 10 871 MiB / 2 596 MiB; 8 909 MiB kicsomagolással | 07-15, helyben: idő / csúcsmemória / munkakönyvtár-csúcs közvetlen ZIP-olvasással; a különbség 6,17 GiB | outputs/logs/lemezmeres_0715.log zip_6GB és kicsomag_6GB sor | 2026-10-25 |
| 127 / 128 nap | napok, amelyeken az Øresund/PortWatch arány legalább 1 | (arany<1).sum()=1 | 2026-10-25 |
| heti r = 0,755 (18 teljes hét); fájlban 0,971 (19 hét) | heti r, Øresund; a 19. hét csak két nap (10-05 – 10-06), ezért a fájlbeli érték nem használható (korábban: ~~0,760 (15 hét)~~) | resample('W-SUN').sum(), szűrés size()==7 | 2026-10-25 |
| 92–143 mp; 07:59–11:14 UTC | a 16 ütemezett futás ideje és indulási sávja (a 3. fejezetben nem szerepel; a 4.6-hoz) (korábban: ~~105–143 mp; 10:04–11:14 (3 futás)~~) | futasok.csv futasido_mp min 92, max 143; inditas_utc 07:59 (10-17) – 11:14 (10-12) | 2026-10-25 |
| 48,30–48,73 óra (medián 48,34) | a fájl késése a nap végéhez képest | ugyanaz, keses_ora | 2026-10-25 |
| 4,55% | téves jelzések aránya normális eloszlásnál, ±2 szórásos küszöbbel (korábban: ~~mintegy 5%~~) | scipy.stats.norm: 2*norm.sf(2) = 0,0455003 | 2026-10-25 |
| 203,6 mp / 10 871 MiB / 2 596 MiB; kicsomagolással 8 909 MiB | 07-15, helyi gépen: idő / csúcsmemória / munkakönyvtár-csúcs közvetlen ZIP-olvasással; a különbség 6,17 GiB | outputs/logs/lemezmeres_0715.log, zip_6GB és kicsomag_6GB sor | 2026-10-25 |
| 68,6–92,0% | Kiel-méretű esemény észlelése a három kapusorozaton (korábban: ~~69,1–90,7%~~) | bootstrap.csv Kiel-eset sorai | 2026-10-25 |
| 2,94 / 30 nap | téves riasztás, Mindkét kapu, bővülő walk-forward (102 nap) (korábban: ~~3,37 / 30 nap~~) | walkforward.csv fa30_wf | 2026-10-25 |
| 1,25–4,71 / 30 nap | a téves riasztás 95%-os bootstrap-intervalluma, Mindkét kapu (korábban: ~~1,65–5,27 / 30 nap~~) | bootstrap.csv ci_also / ci_felso | 2026-10-25 |
| 15 hét | a backtest által lefedett naptári hetek (07-13 – 10-22) (korábban: ~~13 hét~~) | bootstrap.csv blokkok 15, n 102 | 2026-10-25 |
| 1–2 / 1–7 nap 102-ből | bővülő / rögzített walk-forward eltérő napjai a kapusorozatokon (korábban: ~~1–2 / 1–7 nap 89-ből~~) | walkforward.csv elter_nap | 2026-10-25 |
| 2–3 / 4–19 nap 96-ból | bővülő / rögzített walk-forward eltérő napjai a megrakottsági sorozatokon (korábban: ~~2–4 / 12–17 nap 83-ból~~) | walkforward.csv elter_nap | 2026-10-25 |
| 5,5 → 1,0 / 30 nap; 95,6% → 66,9% | k = 1,5 … 3: téves riasztás és Kiel-eset észlelése, Mindkét kapu, közös ablak (88 nap) (korábban: ~~6,4 → 1,2 / 30 nap; 94,8% → 68,7%~~) | szabalyok.csv kozos, R1 k=1.5 és k=3 | 2026-10-25 |
| 2,7 / 91,9% / 50,0% | napi szabály (R0): téves riasztás / Kiel-eset / gyenge, tartós esemény, közös ablak (korábban: ~~3,2 / 90,3% / 53,2%~~) | szabalyok.csv kozos R0 (k=2) | 2026-10-25 |
| 0,3 / 79,4% / 48,7% | CUSUM h = 4: téves riasztás / Kiel-eset / gyenge, tartós esemény, közös ablak (korábban: ~~0,4 / 79,9% / 56,5%~~) | szabalyok.csv kozos R4 CUSUM h=4 | 2026-10-25 |
| 89,4% | a Nagy-Balti-öv legjobb Kiel-eset észlelése a k = 1–4 rácson (90% alatt) | roc.csv Nagy-Balti-öv R1 eszl_kiel max | 2026-10-25 |
| 1 perc 32 mp – 2 perc 23 mp | éles futásidő, 16 ütemezett futás (átlag 116,6 mp) (korábban: ~~1 perc 45 mp – 2 perc 23 mp~~) | futasok.csv futasido_mp 92–143 | 2026-10-25 |
| 4,5–7,7 óra | az ütemezett indulás késése a 03:30-as (UTC) cronhoz képest (korábban: ~~6,5–7,7 óra~~) | futasok.csv inditas_utc 07:59–11:14 | 2026-10-25 |
| 16 / 16 | ütemezett éles futások 2026-10-10 – 10-25, mind sikeres (korábban: ~~3 / 3~~) | futasok.csv event = schedule | 2026-10-25 |
| 3 534 | a dashboard által 0 eltéréssel reprodukált jelzéssorok (432 + 414 + 2 688) (korábban: ~~3 456~~) | node scripts/teszt_dashboard.mjs B) rész | 2026-10-25 |
| 2,15× | mért / normális eloszlásból várt téves riasztás (2,94 / 1,365) | walkforward.csv; 2·(1−Φ(2))·30 | 2026-10-25 |
| 1–2 / 1–7 nap 102-ből | a bővülő / rögzített walk-forward eltérő napjai a kapusorozatokon (korábban: ~~1–2 / 1–7 nap 89-ből~~) | walkforward.csv elter_nap | 2026-10-25 |
| 2–3 / 4–19 nap 96-ból | a bővülő / rögzített walk-forward eltérő napjai a megrakottsági sorozatokon (korábban: ~~2–4 / 12–17 nap 83-ból~~) | walkforward.csv elter_nap | 2026-10-25 |
| 16 / 16 | ütemezett éles futások 2026. október 10. – 25., mind sikeres (korábban: ~~3 / 3~~) | futasok.csv event = schedule | 2026-10-25 |
| 88,5% (5 248 / 5 930) | Átmenő kereskedelmi Drogden-átkelések (változatlan) | saját újraszámolás az atkelesek.csv-ből (±12 óra, azonos MMSI + irány) | 2026-10-25 |
| 92–143 s | Ütemezett futás teljes ideje (korábban: ~~105–143 s~~) | futasok.csv futasido_mp | 2026-10-25 |
| #2: nyitva 10-11, lezárva 10-13, 2 megjegyzés | Az éles üzem egyetlen jelzés-issue-ja | gh issue view 2 --comments; gh issue list --state all; issuek.csv | 2026-10-25 |
| #2: 2 megjegyzés, lezárva 2026-10-13; új issue nem nyílt | az éles issue-k története 10-25-ig (korábban: ~~1 megjegyzés~~) | issuek.csv; gh issue view 2 --json comments; gh issue list --state all | 2026-10-25 |
| 55/56 | dashboard-tesztállítás a fagyasztott backtest mellett, a dashboard újraépítése előtt (korábban: ~~56/56~~) | node scripts/teszt_dashboard.mjs (2026-10-25) | 2026-10-25 |
| 88 nap | a szabályváltozatok közös értékelési ablaka (07-27-től) (korábban: ~~75 nap~~) | szabalyok.csv ablak=kozos | 2026-10-25 |
| k = 2,25: 91,0%, 2,06; k = 2: 92,0%, 2,94; Øresund k = 1,5: 6,47; NBÖ legjobb 89,4% | munkapont (korábban: ~~90,1%, 2,36; 90,7%, 3,37; 6,40; 88,8%~~) | munkapont.csv; roc.csv; injektalas.csv | 2026-10-25 |

### Hivatkozások (DOI)

| szám | jelentés | szkript / forrás | dátum |
|------|----------|------------------|-------|
| https://doi.org/10.2307/25148625 | Hevner, March, Park & Ram (2004) DOI-ja (MIS Quarterly 28(1)); Crossref-oldaltartomány 75-106, a szövegben a megszokott 75–105 maradt | curl -s https://api.crossref.org/works/10.2307/25148625 (lekérve 2026-10-25) | 2026-10-25 |
| https://doi.org/10.2753/MIS0742-1222240302 | Peffers, Tuunanen, Rothenberger & Chatterjee (2007) DOI-ja (JMIS 24(3), 45–77) | curl -s https://api.crossref.org/works/10.2753/MIS0742-1222240302 (lekérve 2026-10-25) | 2026-10-25 |
| https://doi.org/10.25300/MISQ/2013/37.2.01 | Gregor & Hevner (2013) DOI-ja (MIS Quarterly 37(2), 337–355) | curl -s https://api.crossref.org/works/10.25300/MISQ/2013/37.2.01 (lekérve 2026-10-25) | 2026-10-25 |
| 10.2307/25148625 | Hevner et al. (2004) DOI-ja; a cím, a szerzők, az év és a folyóirat (MIS Quarterly 28(1)) a Crossref szerint egyezik. Az oldaltartomány a Crossrefben 75–106, a tételben 75–105 [NEM ELLENŐRIZVE]. | curl -s https://api.crossref.org/works/10.2307/25148625 (2026-10-25) | 2026-10-25 |
| 10.2753/MIS0742-1222240302 | Peffers et al. (2007) DOI-ja; JMIS 24(3), 45–77, a Crossref szerint egyezik | curl -s https://api.crossref.org/works/10.2753/MIS0742-1222240302 (2026-10-25) | 2026-10-25 |
| 10.25300/MISQ/2013/37.2.01 | Gregor & Hevner (2013) DOI-ja; MIS Quarterly 37(2), 337–355, a Crossref szerint egyezik | curl -s https://api.crossref.org/works/10.25300/MISQ/2013/37.2.01 (2026-10-25) | 2026-10-25 |
| 19 | a Hivatkozások szakaszban ([1170]–[1231]) már szereplő DOI-k száma; mind a 19-re HTTP 200 a válasz a Crossref API-tól | python -X utf8: re.findall(r'https://doi.org/\S+') a bekezdesek.txt [1169]–[1231] soraira -> 19 (újrafuttatva 2026-10-25); Crossref HTTP-kódok: az adatellenőrző futása (2026-10-25), 19× 200 | 2026-10-25 |

### Kísérleti kapuk (128 nap)

| szám | jelentés | szkript / forrás | dátum |
|------|----------|------------------|-------|
| 0,58 | Kis-Balti-öv hétvége/hétköznap arány (a többi új kapu 1,03–1,14) | outputs/kapuk_kiterjesztes/napi_statisztika.csv hetvege_per_hetkoznap 0,577 | 2026-10-25 |

### Monitor: zajszint, küszöb, napok

| szám | jelentés | szkript / forrás | dátum |
|------|----------|------------------|-------|
| 144 nap; kuszob_szorzo 2,0 | a fagyasztott monitorállapot (2026-06-01 – 10-22) még a teljes idősoros küszöbbel fut, a bővülő ablakot nem vezették be | outputs/fagyasztas_2026-10-22/monitor/allapot.json | 2026-10-25 |
| 5 | új kísérleti kapu a konfigurációs fájlban (Øresund – Drogden, Fehmarn-öv, Kadet-rende, Kis-Balti-öv, Skagen) | scripts/kapuk.json, 'kapuk' kulcs, monitor=False bejegyzések száma | 2026-10-25 |
| 97,2% / 97,6% | hihető és változó merülésű átkelések aránya, tanker / teher, mindkét kapu, 144 napon (4 195 / 10 434 átkelés) (korábban: ~~96,5% / 97,3% (dae2366, 128 nap, 3 737 / 9 232 átkelés; pontosan reprodukálva, a [262] történeti sora ezt rögzíti, változatlan)~~) | $TEMP/ell21/lef.py: megrakottsag.lefedettseg(outputs/fagyasztas_2026-10-22/monitor) | 2026-10-25 |
| 144 | a monitor fagyasztott állapotának napjai (2026-06-01 – 2026-10-22) (korábban: ~~72 (3.5; 06-01 – 09-05 idősor)~~) | outputs/fagyasztas_2026-10-22/monitor/allapot.json napok_szama; jelzesek.csv Mindkét kapu 144 sor | 2026-10-25 |
| 123 | alapszintes napok sorozatonként a 144 napos állapotban (korábban: ~~72~~) | allapot.json zajszint[*].napok; jelzesek.csv, alapszint notna | 2026-10-25 |
| 10,6% (0,105726) | Mindkét kapu: a relatív eltérés robusztus szórása (1,4826·MAD) (korábban: ~~11,8%~~) | jelzesek.csv, Mindkét kapu, alapszint notna, e = ertek/alapszint − 1; allapot.json 0.1057 | 2026-10-25 |
| 7,1% (0,071429) | Mindkét kapu: medián abszolút eltérés (korábban: ~~7,8%~~) | jelzesek.csv median\|e\|; allapot.json 0,0714 | 2026-10-25 |
| 20,7% (0,206731) | Mindkét kapu: az abszolút eltérés 90. percentilise (korábban: ~~22,0%~~) | np.quantile(\|e\|, 0.9); allapot.json 0,2067 | 2026-10-25 |
| 17,0% (0,169719) | Nagy-Balti-öv robusztus szórás (korábban: ~~17,8%~~) | jelzesek.csv; allapot.json 0,1697 | 2026-10-25 |
| 12,9% (0,128922) | Øresund robusztus szórás (korábban: ~~12,8%~~) | jelzesek.csv; allapot.json 0,1289 | 2026-10-25 |
| ±21,1% (0,211452) | Mindkét kapu jelzési küszöbe (2 × 1,4826 × MAD), 144 napos állapot (korábban: ~~±23,5% (72 nap); ±20,93% (131 nap)~~) | jelzesek.csv-ből számolva; allapot.json kuszob 0,2115 | 2026-10-25 |
| 12/123 (9,8%) | Mindkét kapu jelzett napjai (9 magas, 3 alacsony) (korábban: ~~8,3% (≈ 6/72); 12/110 = 10,9% (131 nap)~~) | jelzesek.csv, Mindkét kapu, alapszint notna, jelzes ≠ normál | 2026-10-25 |
| 5/123 (4,1%) | Nagy-Balti-öv jelzett napjai (korábban: ~~5,6% (72 nap); 5/110 = 4,5% (131 nap)~~) | jelzesek.csv, Nagy-Balti-öv | 2026-10-25 |
| 13/123 (10,6%) | Øresund jelzett napjai (korábban: ~~12,5% (72 nap); 13/110 = 11,8% (131 nap)~~) | jelzesek.csv, Øresund | 2026-10-25 |
| 2. (a 123-ból) | a július 15-i +33,0% rangja az abszolút eltérések között (1. augusztus 18., +39,8%) (korábban: ~~2. a 72-ből~~) | jelzesek.csv, Mindkét kapu, \|elteres\| szerint rendezve | 2026-10-25 |
| 83,7% | a 17,6% percentilis-helye a 123 abszolút eltérés között, a „felső rész, nem kiugró” minősítés alapja | jelzesek.csv, mean(\|e\| < 0,176) = 0.8374 | 2026-10-25 |
| 101,6 (medián 101,5; 77–129) | Mindkét kapu napi kereskedelmi átkelése a 144 napon, a „napi mintegy száz” alapja | jelzesek.csv, Mindkét kapu, ertek describe() | 2026-10-25 |
| 5 | új kísérleti kapu a konfigurációs fájlban | scripts/kapuk.json: 7 kapu, ebből 5-nél "monitor": false | 2026-10-25 |
| 144 nap (2026. június 1. – október 22.) | a monitor fagyasztott idősorának hossza (korábban: ~~131 nap (2026. június 1. – október 9.)~~) | outputs/fagyasztas_2026-10-22/monitor/allapot.json napok_szama = 144; jelzesek.csv datum.nunique() = 144 | 2026-10-25 |
| 144 nap (2026-06-01 – 2026-10-22) | a monitor fagyasztott állapota, hézag nélkül (korábban: ~~124 nap (2026-06-01 – 10-06)~~) | outputs/fagyasztas_2026-10-22/monitor/allapot.json napok_szama; kapuvonal_napi.csv datum: 144 egyedi nap = naptári tartomány | 2026-10-25 |
| 2 óra 46 perc | a 03:30-as ütemezés tartaléka a legkésőbbi mért megjelenéshez (00:43:54) képest (korábban: ~~legalább 3 óra~~) | 03:30 − 00:43:54; napi_monitor.yml cron "30 3 * * *" | 2026-10-25 |
| 8 fájl, 4 256 119 bájt (4,06 MiB) | a napi futás által a repóba visszaírt monitortáblák a fagyasztott commitban | git ls-tree -r -l f8603b3 outputs/monitor | 2026-10-25 |
| 314 / 194 cella | H3-folyosó: Nagy-Balti-öv / Øresund | python (scripts/): kapuvonal.folyoso(k) a két monitorkapura; MAX_RES_MP = 600 | 2026-10-25 |
| ±33,9% / ±25,8% | Nagy-Balti-öv / Øresund jelzési küszöb, 144 napos állapot (a 3.5 szövegében nem szerepel) | jelzesek.csv-ből 0,339437, 0,257843; allapot.json 0,3394, 0,2578 | 2026-10-25 |
| 2. (a 123-ból) | a július 15-i +33,0% rangja az abszolút eltérések között (Mindkét kapu); az 1. augusztus 18. (+39,8%) (korábban: ~~2. a 72-ből~~) | jelzesek.csv, \|elteres\| szerint rendezve | 2026-10-25 |
| 83,7% | az egy napból számolt 17,6% percentilis-helye a 123 abszolút eltérés között (Mindkét kapu); a „felső rész, nem kiugró” minősítés alapja | jelzesek.csv, mean(\|e\| < 0,176) = 0,83740 | 2026-10-25 |
| 101,6 (medián 101,5; 77–129) | Mindkét kapu napi kereskedelmi átkelése, 144 nap; a „napi mintegy száz” alapja | jelzesek.csv, Mindkét kapu, ertek | 2026-10-25 |
| 144 nap (2026. június 1. – október 22.) | a monitor fagyasztott állapota, hézag nélkül (korábban: ~~124 nap (2026. június 1. – október 6.)~~) | outputs/fagyasztas_2026-10-22/monitor/allapot.json napok_szama; kapuvonal_napi.csv datum: 144 egyedi nap = naptári tartomány | 2026-10-25 |
| 144 | a monitor fagyasztott állapotának napjai (2026. június 1. – október 22.) (korábban: ~~72 (3.5; június 1. – szeptember 5. idősor)~~) | outputs/fagyasztas_2026-10-22/monitor/allapot.json napok_szama; jelzesek.csv Mindkét kapu 144 sor | 2026-10-25 |
| 10,6% (0,105726) | Mindkét kapu: a relatív eltérés robusztus szórása (1,4826 · MAD) (korábban: ~~11,8%~~) | jelzesek.csv, Mindkét kapu, alapszint notna, e = ertek/alapszint − 1; allapot.json 0,1057 | 2026-10-25 |
| 144 nap | a monitor fagyasztott állapotának hossza (2026-06-01 – 10-22), hiány nélkül (korábban: ~~131 nap~~) | outputs/fagyasztas_2026-10-22/monitor/allapot.json napok_szama; jelzesek.csv 144 különböző dátum | 2026-10-25 |
| 10,6% | „Mindkét kapu” robusztus szórása (123 alapszintes nap) (korábban: ~~10,5%~~) | allapot.json zajszint.Mindkét kapu.robusztus_szoras 0,1057 | 2026-10-25 |
| 144 nap | a monitor fagyasztott állapotának hossza (2026. június 1. – október 22.), hiány nélkül (korábban: ~~131 nap~~) | outputs/fagyasztas_2026-10-22/monitor/allapot.json napok_szama; jelzesek.csv 144 különböző dátum | 2026-10-25 |
| 10,6% | a „Mindkét kapu” robusztus szórása (123 alapszintes nap) (korábban: ~~10,5%~~) | allapot.json zajszint.Mindkét kapu.robusztus_szoras 0,1057 | 2026-10-25 |
| ±33,9% / ±25,8% | Nagy-Balti-öv / Øresund küszöb a 144 napos állapotban (a 128 napos kapuablakon ±34,4% / ±25,8%) | outputs/fagyasztas_2026-10-22/monitor/allapot.json kuszob 0,3394 / 0,2578; kiel_ablak.csv 0,3437 / 0,2578 | 2026-10-25 |
| 2 978; 0 eltérés | A kapukód napi aggregátuma vs. a fagyasztott monitortábla (≤ 10-06) | saját merge: kapuvonal_napi.csv (kapuk) vs. fagyasztas_2026-10-22/monitor/kapuvonal_napi.csv, datum ≤ 2026-10-06: 2 978 both, 0 eltérés | 2026-10-25 |
| 144 nap | A monitor idősora a fagyasztott állapotban (korábban: ~~131 nap~~) | f8603b3 allapot.json napok_szama | 2026-10-25 |
| 133; 110,0; +20,9%; ±12,0% | Megrakott tanker 2026-10-08 a fagyasztott állapotban (korábban: ~~112,5; +17,3%~~) | fagyasztott jelzesek_megrakottsag.csv | 2026-10-25 |
| ±13,05% → ±11,97% (közben ±11,86–14,90%) | Megrakott tanker küszöbe az éles üzemben (korábban: ~~±13,05% → ±14,85%~~) | allapot.json kuszob_megrakottsag, 17 commit | 2026-10-25 |
| 0,8148; 0,7871 → 0,7911 | Otsu megrakott-küszöb: tanker változatlan, teherhajó a 10-21-i futástól (korábban: ~~0,8148 / 0,7871 változatlan~~) | allapot.json megrakott_kuszob_relativ_merules, 17 commit | 2026-10-25 |
| 444 215 bájt; 9 fájl, 0,57 MB | Dashboard és adat-feed a fagyasztott állapotból (korábban: ~~429 421 bájt; 0,54 MB~~) | python scripts/dashboard_epit.py --monitor outputs/fagyasztas_2026-10-22/monitor --oldal <scratch>/oldal2; wc -c; du -cb = 596 897 | 2026-10-25 |
| 432 / 414 / 2 688; 56/56 | A dashboard JS újraszámolása (0 eltérés) és a tesztállítások (korábban: ~~393 / 375 / 2 688; 56/56~~) | node <scratch>/td.mjs (teszt_dashboard.mjs másolata a scratch-dashboardra és a fagyasztott monitorra) | 2026-10-25 |
| 2 978; 0 eltérés | A kapukód napi aggregátuma vs. a fagyasztott monitortábla (≤ október 6.) | saját merge: kapuvonal_napi.csv (kapuk) vs. fagyasztas_2026-10-22/monitor/kapuvonal_napi.csv, datum ≤ 2026-10-06: 2 978 közös, 0 eltérés | 2026-10-25 |
| 133; 110,0; +20,9%; ±12,0% | Megrakott tanker 2026. október 8. a fagyasztott állapotban (korábban: ~~112,5; +17,3%~~) | outputs/fagyasztas_2026-10-22/monitor/jelzesek_megrakottsag.csv | 2026-10-25 |
| 0,8148; 0,7871 → 0,7911 | Otsu megrakott-küszöb: a tankeré változatlan, a teherhajóé az október 21-i futástól változott (korábban: ~~0,8148 / 0,7871 változatlan~~) | allapot.json megrakott_kuszob_relativ_merules, 17 commit | 2026-10-25 |
| 432 / 414 / 2 688; 56 / 56 | A dashboard JS újraszámolása (0 eltérés) és a tesztállítások (korábban: ~~393 / 375 / 2 688; 56 / 56~~) | node <scratch>/td.mjs (teszt_dashboard.mjs másolata a scratch-dashboardra és a fagyasztott monitorra) | 2026-10-25 |
| 97,2% / 97,6% (4 195 / 10 434 átkelés) | K3: hihető és változó merülésű átkelés, tanker / teherhajó, mindkét kapu, 144 nap (korábban: ~~96,5% / 97,3% (3 737 / 9 232)~~) | megrakottsag.lefedettseg(Path('outputs/fagyasztas_2026-10-22/monitor')), írás nélkül | 2026-10-25 |

### Placebo-teszt (Kiel-ablak)

| szám | jelentés | szkript / forrás | dátum |
|------|----------|------------------|-------|
| p = 0,017 | Øresund placebo-teszt: a Kiel-ablak rangja 2/119 kétnapos ablak között (egyoldali p); PortWatch Øresund p = 0,033; a többi AIS-sorozat p ≥ 0,117; Bonferroni-küszöb 0,05/7 ≈ 0,0071 (korábban: ~~0,019 (2/107)~~) | outputs/backtest/placebo.csv minden_2napos_p_felso | 2026-10-25 |
| p = 0,017 | Øresund placebo-teszt, Kiel-ablak rangja 2/119 kétnapos ablak között (egyoldali empirikus p); PortWatch Øresund p = 0,033; a többi AIS-sorozat p ≥ 0,117; Bonferroni 0,05/7 ≈ 0,0071 alatt nincs sorozat (korábban: ~~0,019 (2/106)~~) | outputs/backtest/placebo.csv minden_2napos_p_felso; régi: git show 125f554:outputs/backtest/placebo.csv → Øresund 0,0187 (2/106), PortWatch 0,0333 | 2026-10-25 |
| p = 0,017 / 0,242 / 0,117 | Kiel-ablak placebo p-értéke: Øresund / Nagy-Balti-öv / Mindkét kapu (119 kétnapos ablak) (korábban: ~~0,019 / 0,243 / 0,131~~) | placebo.csv minden_2napos_p_felso | 2026-10-25 |
| p = 0,017 / 0,242 / 0,117 | a Kiel-ablak placebo p-értéke: Øresund / Nagy-Balti-öv / Mindkét kapu (119 kétnapos ablak) (korábban: ~~0,019 / 0,243 / 0,131~~) | placebo.csv minden_2napos_p_felso | 2026-10-25 |
| 2 / 120; 0,017; 1 / 18; 0,056 | Placebo, Øresund (rang/ablakszám, p; szerda–csütörtök rang/párszám, p) (korábban: ~~2 / 107; 0,019; 1 / 16; 0,0625~~) | outputs/backtest/placebo.csv; saját újraszámolás a fagyasztott jelzesek.csv-ből; backtest.py --ki <scratch>/bt -> placebo.csv bájtra azonos | 2026-10-25 |
| +11,1%; 14 / 120; 0,117; 3 / 18; 0,167 | Placebo, Mindkét kapu (korábban: ~~14 / 107; 0,131; 3 / 16; 0,188~~) | outputs/backtest/placebo.csv; saját újraszámolás | 2026-10-25 |
| +6,5%; 29 / 120; 0,242; 7 / 18; 0,389 | Placebo, Nagy-Balti-öv (korábban: ~~26 / 107; 0,243; 6 / 16; 0,375~~) | outputs/backtest/placebo.csv; saját újraszámolás | 2026-10-25 |
| +4,2%; 30 / 114; 0,263; 5 / 17; 0,294 | Placebo, Megrakott tanker (7 nap) (korábban: ~~+5,3%; 27 / 101; 0,267; 4 / 15; 0,267~~) | outputs/backtest/placebo.csv; saját újraszámolás a fagyasztott jelzesek_megrakottsag.csv-ből | 2026-10-25 |
| +5,7%; 37 / 114; 0,325; 6 / 17; 0,353 | Placebo, Megrakott teherhajó (7 nap) (korábban: ~~+4,9%; 34 / 101; 0,337; 5 / 15; 0,333~~) | outputs/backtest/placebo.csv; saját újraszámolás | 2026-10-25 |
| −0,2%; 54 / 114; 0,474; 9 / 17; 0,529 | Placebo, Tanker-volumen (7 nap) (korábban: ~~−0,2%; 49 / 101; 0,485; 8 / 15; 0,533~~) | outputs/backtest/placebo.csv; saját újraszámolás | 2026-10-25 |
| +27,7%; 94 / 2 824; 0,033; 16 / 404; 0,040 | Placebo, PortWatch Øresund 2019-01-01 – 2026-10-18 (2 848 nap) (korábban: ~~93 / 2 789; 15 / 399; 0,038~~) | placebo.csv; saját újraszámolás data/portwatch_chokepoints_2026-10-25.csv n_total-ból | 2026-10-25 |
| 2 / 120; 0,017; 1 / 18; 0,056 | Placebo, Øresund (rang/ablakszám, p; szerda–csütörtök rang/párszám, p); Kiel-ablak eltérése +18,2% változatlan (korábban: ~~2 / 107; 0,019; 1 / 16; 0,0625~~) | outputs/backtest/placebo.csv; saját újraszámolás a fagyasztott jelzesek.csv-ből; backtest.py --ki <scratch>/bt -> placebo.csv bájtra azonos | 2026-10-25 |
| +27,7%; 94 / 2 824; 0,033; 16 / 404; 0,040 | Placebo, PortWatch Øresund 2019. január 1. – 2026. október 18. (2 848 nap) (korábban: ~~93 / 2 789; 0,033; 15 / 399; 0,038~~) | outputs/backtest/placebo.csv; saját újraszámolás data/portwatch_chokepoints_2026-10-25.csv n_total-ból | 2026-10-25 |

### PortWatch-összevetés

| szám | jelentés | szkript / forrás | dátum |
|------|----------|------------------|-------|
| 0,892 | az Øresund – Drogden kapu kereskedelmi átkelései és a PortWatch Oresund n_total napi Pearson-r-je, 128 közös napon (2026-06-01 – 10-06); Spearman 0,886 (korábban: ~~0,905~~) | kereskedelmi_napi.csv × portwatch_chokepoints_2026-10-25.csv saját merge + corr; outputs/kapuk_kiterjesztes/portwatch_osszevetes.csv r_napi | 2026-10-25 |
| 28 / 1 | PortWatch chokepointok száma; ebből egyetlen dán szoros szerepel, az Oresund Strait | data/portwatch_chokepoints_2026-10-25.csv: portname.nunique() = 28; a 'resund'/'Belt'/'Dan' mintára csak az 'Oresund Strait' illeszkedik | 2026-10-25 |
| 0,892 | napi Pearson-r: a Drogden alatti kapu kereskedelmi átkelései és a PortWatch n_total, 128 közös napon (2026. június 1. – október 6.) (korábban: ~~0,905 (105 nap, régi PortWatch-fájl, r = 0,9048)~~) | saját pandas-számítás: outputs/kapuk_kiterjesztes/kereskedelmi_napi.csv × data/portwatch_chokepoints_2026-10-25.csv (Oresund), r = 0,8916; egyezik a portwatch_osszevetes.csv r_napi értékével (0.89155) | 2026-10-25 |
| 0,736 | Øresund-kapu kereskedelmi vs. PortWatch n_total, Pearson r, 128 nap (06-01 – 10-06) (korábban: ~~0,82 (5 nap); 0,720 (105 nap)~~) | kereskedelmi_napi.csv ⋈ portwatch_chokepoints_2026-10-25.csv saját számítás: 0.73626 | 2026-10-25 |
| 0,666 | ugyanez tankerre (n_tanker), 128 nap (korábban: ~~0,98 (5 nap); 0,678 (105 nap)~~) | monitor kapuvonal_napi.csv (Øresund, Tanker) vs. n_tanker, ≤ 10-06: 0,66564; portwatch_osszevetes.csv 0,665639 | 2026-10-25 |
| 1,29 (0,98–1,66) | saját / PortWatch napi arány átlaga (min–max), Øresund kereskedelmi, 128 nap (korábban: ~~1,33 (5 nap); 1,29 (0,98–1,65; 105 nap)~~) | újraszámolva 1,29220, 0,98, 1,65517; portwatch_osszevetes.csv | 2026-10-25 |
| 0,892; 1,17 | Drogden alatti kapu vs. PortWatch: r és arány, 128 nap (korábban: ~~0,905; 1,15 (105 nap)~~) | újraszámolva 0,89155, 1,16608; portwatch_osszevetes.csv 'Øresund – Drogden: kereskedelmi' | 2026-10-25 |
| 1,03 | Drogden-kapu, csak átmenő átkelések / PortWatch arány, 128 nap (korábban: ~~1,02 (105 nap, 4.5)~~) | portwatch_osszevetes.csv 'Øresund – Drogden + Øresund (atmeno): kereskedelmi' arany_atlag 1.0314 | 2026-10-25 |
| 128 nap (2026-06-01 – 2026-10-06) | a kapu-PortWatch-összevetés közös napjai az új PortWatch-fájllal (korábban: ~~105 nap (2026-06-01 – 2026-09-13); 5 nap~~) | kereskedelmi_napi.csv × data/portwatch_chokepoints_2026-10-25.csv (Oresund Strait), inner join; portwatch_osszevetes.csv napok/elso/utolso | 2026-10-25 |
| r = 0,736 | napi Pearson-r, Øresund-kapu kereskedelmi átkelései vs PortWatch n_total (korábban: ~~0,720 (105 nap); 0,82 (5 nap)~~) | portwatch_osszevetes.csv r_napi=0.73626; saját újraszámolás 0.73626 | 2026-10-25 |
| r = 0,892; arány 1,17 | Drogden alatti kapu kereskedelmi vs PortWatch n_total (korábban: ~~0,905; 1,15 (105 nap)~~) | portwatch_osszevetes.csv 'Øresund – Drogden: kereskedelmi' r_napi=0.89155, arany_atlag=1.16608; saját újraszámolás egyezik | 2026-10-25 |
| 0,892 | Øresund – Drogden kapu kereskedelmi átkelései és a PortWatch Oresund n_total napi Pearson-r-je, 128 közös nap (2026-06-01 – 10-06) (korábban: ~~0,905~~) | outputs/kapuk_kiterjesztes/portwatch_osszevetes.csv r_napi 0.89155 | 2026-10-25 |
| 28 / 1 | PortWatch chokepointok száma, ebből egyetlen dán szoros (Oresund Strait); Nagy-Balti-öv nincs | data/portwatch_chokepoints_2026-10-25.csv: portname nunique = 28; Oresund/Belt/Kattegat/Skag szűrés → ['Oresund Strait'] | 2026-10-25 |
| r = 0,736 | napi Pearson-r, régi Øresund-kapu kereskedelmi átkelései vs. PortWatch n_total (korábban: ~~0,720 (105 nap); 0,82 (5 nap)~~) | újraszámolás: 0.7363; portwatch_osszevetes.csv r_napi=0.73626 | 2026-10-25 |
| 128 nap (2026. június 1. – október 6.) | a kapu-PortWatch-összevetés közös napjai az új PortWatch-fájllal (korábban: ~~105 nap (2026. június 1. – szeptember 13.); 5 nap~~) | kereskedelmi_napi.csv × data/portwatch_chokepoints_2026-10-25.csv (Oresund Strait), inner join; portwatch_osszevetes.csv napok/elso/utolso | 2026-10-25 |
| 0,736 | Øresund-kapu kereskedelmi napi átkelése vs. PortWatch n_total, Pearson r, 128 nap (június 1. – október 6.) (korábban: ~~0,82 (5 nap); 0,720 (105 nap)~~) | kereskedelmi_napi.csv ⋈ data/portwatch_chokepoints_2026-10-25.csv (Oresund Strait): 0,73626; portwatch_osszevetes.csv r_napi 0,736261 | 2026-10-25 |
| 11,7% | az Øresund saját / PortWatch napi arányának relatív szórása, 128 nap (a „közel állandó” jelző elhagyásának indoka) | std/mean = 0,11659; portwatch_osszevetes.csv arany_rel_szoras | 2026-10-25 |
| 0,731 / 0,651 / 1,29 | kontroll: a monitor 144 napos Øresund-sorozata vs. új PortWatch, 140 közös nap (június 1. – október 18.); a szövegben nem szerepel | monitor kapuvonal_napi.csv (Øresund, Teherhajó+Tanker / Tanker) ⋈ új PortWatch: r 0,73098, tanker-r 0,65105, arány 1,29127 | 2026-10-25 |
| r = 0,736 | Øresund kereskedelmi átkelés és a PortWatch n_total napi korrelációja, 128 közös nap (korábban: ~~0,720 (105 nap)~~) | outputs/kapuk_kiterjesztes/portwatch_osszevetes.csv r_napi | 2026-10-25 |
| r = 0,892 | Drogden-kapu és a PortWatch napi korrelációja, 128 közös nap (korábban: ~~0,905~~) | portwatch_osszevetes.csv r_napi | 2026-10-25 |
| 1,17 | Drogden / PortWatch átlagos arány (128 nap); az Øresund-arány 1,29 marad (1,2922) (korábban: ~~1,15~~) | portwatch_osszevetes.csv arany_atlag 1,1661 | 2026-10-25 |
| r = 0,736 | az Øresund kereskedelmi átkelés és a PortWatch n_total napi korrelációja, 128 közös nap (korábban: ~~0,720 (105 nap)~~) | outputs/kapuk_kiterjesztes/portwatch_osszevetes.csv r_napi | 2026-10-25 |
| r = 0,892 | a Drogden-kapu és a PortWatch napi korrelációja, 128 közös nap (korábban: ~~0,905~~) | portwatch_osszevetes.csv r_napi | 2026-10-25 |
| +25,0% / +30,4% | PortWatch Øresund eltérése július 15-én / 16-án (változatlan) | saját újraszámolás a PortWatch-fájlból: 0,250 / 0,304 | 2026-10-25 |
| 0,736 / 0,892; 1,29 / 1,17; 0,666 / 0,878; 1,03 és r = 0,882; 128 nap | PortWatch-összevetés: r (kereskedelmi), arány, r (tanker) a régi Øresund / Drogden kapun; átmenő Drogden; közös napok (korábban: ~~0,720 / 0,905; 1,29 / 1,15; 0,678 / 0,872; 1,02 és 0,885; 105 nap~~) | outputs/kapuk_kiterjesztes/portwatch_osszevetes.csv; saját újraszámolás az atkelesek.csv-ből | 2026-10-25 |
| 144 nap (2026-06-01 – 10-22) | a backtest és a placebo bemenete (fagyasztott monitorállapot) (korábban: ~~131 nap (06-01 – 10-09)~~) | python scripts/backtest.py --monitor outputs/fagyasztas_2026-10-22/monitor --portwatch data/portwatch_chokepoints_2026-10-25.csv --ki %TEMP%/bt_ell (15/15 fájl bájtra azonos az outputs/backtest/-tel; az aismonitor.py backtest burkon át is 15/15) | 2026-10-25 |
| r = 0,736; heti 0,755 (18 teljes hét); arány 1,29 (0,98–1,66); Drogden r = 0,892 | saját kereskedelmi Øresund-sorozat és a PortWatch n_total, 128 közös nap (korábban: ~~105 nap; 0,720; heti 0,760 (15 hét); 1,29 (0,98–1,65); 0,905~~) | outputs/kapuk_kiterjesztes/portwatch_osszevetes.csv; resample('W-SUN'), csak 7 napos hetek (a CSV r_heti 0,971 a 2 napos utolsó hét műterméke) | 2026-10-25 |
| 98 nap; r = 0,714; 89,8%; κ = 0,328; retro 119 nap, 89,9%, κ = 0,218; 11/5/3; 36,2% / 25,5%; tanker κ −0,06 / −0,03 | PortWatch-jelzésegyezés (korábban: ~~63 nap; 0,718; 90,5%; 0,357; 84 nap, 89,3%, 0,267; 7/3/2; 34,7% / 25,8%; −0,08 / −0,03~~) | portwatch_egyezes.csv (teljes pontosságú futással ellenőrizve) | 2026-10-25 |
| 144 nap (2026. június 1. – október 22.) | a backtest és a placebo bemenete (fagyasztott monitorállapot) (korábban: ~~131 nap (június 1. – október 9.)~~) | python scripts/backtest.py --monitor outputs/fagyasztas_2026-10-22/monitor --portwatch data/portwatch_chokepoints_2026-10-25.csv --ki %TEMP%/bt_ell (15/15 fájl bájtra azonos az outputs/backtest/-tel; az aismonitor.py backtest burkon át is 15/15) | 2026-10-25 |
| 98 nap; r = 0,714; 89,8%; κ = 0,328; retrospektív 119 nap, 89,9%, κ = 0,218; 11 / 5 / 3; 36,2% / 25,5%; tanker κ −0,06 / −0,03 | PortWatch-jelzésegyezés (korábban: ~~63 nap; 0,718; 90,5%; 0,357; 84 nap, 89,3%, 0,267; 7 / 3 / 2; 34,7% / 25,8%; −0,08 / −0,03~~) | outputs/backtest/portwatch_egyezes.csv (teljes pontosságú futással ellenőrizve) | 2026-10-25 |

### Tároló és lánc

| szám | jelentés | szkript / forrás | dátum |
|------|----------|------------------|-------|
| 36,7 millió sor; 6,1 GiB | a 2026-07-15-i teljes napi fájl: 36 650 571 sor, kicsomagolva 6 248,0 MiB = 6,10 GiB | outputs/pipeline_napok.csv, nap=2026-07-15: nyers_sor, csv_mib/1024 | 2026-10-25 |
| 54,6% | a 2026-07-15-i teljes napi fájlban a bitre azonos ismétlések aránya | outputs/pipeline_napok.csv, 2026-07-15, dup_arany 0.54601 | 2026-10-25 |
| 23,7% (negyedére) | a Parquet-tároló mérete a letöltött ZIP-hez képest (226,8 / 955,7 MiB) | outputs/pipeline_napok.csv, 2026-07-15: parquet_mib / zip_mib = 0,2373 | 2026-10-25 |
| 2,8–6,2 GiB (jún–aug); 2,7–6,2 GiB (128 nap) | napi kicsomagolt CSV-méret | pipeline_napok.csv csv_mib/1024: 2.820–6.165; 128 nap min 2.746 (09-05) | 2026-10-25 |
| 133–236 MiB (jún–aug); 124–236 MiB (128 nap) | napi Parquet-tároló mérete | pipeline_napok.csv parquet_mib: 132.9–236.4; 128 nap min 124.4 (09-05) | 2026-10-25 |
| 4,7 / 5,3 / 5,0 GiB; szept. 4,2 GiB; 15,1 GiB; 23,6% | Parquet-tároló havonta (jún, júl, aug, szept), jún–aug összesen, a ZIP-hez viszonyítva | pipeline_napok.csv havi parquet_mib-összeg/1024: 4.735/5.319/5.007/4.235; jún–aug 15.06; parquet/zip 0.2358 | 2026-10-25 |
| 6,1 GiB; 36,7 millió sor; 956 MiB | a 2026-07-15-i nap kicsomagolva, sorszám, ZIP | pipeline_napok.csv 07-15: csv_mib 6248.0, nyers_sor 36 650 571, zip_mib 955.7 | 2026-10-25 |
| 54,6% / 56,0% | bitre azonos duplikátum, 07-15, teljes fájl / vizsgált terület | pipeline_napok.csv 07-15: dup_arany 0.54601, bbox_dup_arany 0.56027 | 2026-10-25 |
| 36,7 millió sor | a 2026-07-15-i teljes napi fájl sorszáma (36 650 571) | outputs/pipeline_napok.csv, nap=2026-07-15, nyers_sor 36650571 | 2026-10-25 |
| 6,1 GiB | a 2026-07-15-i napi fájl kicsomagolva (6 248,0 MiB = 6,10 GiB) | outputs/pipeline_napok.csv, nap=2026-07-15, csv_mib 6248.0 / 1024 | 2026-10-25 |
| 54,6% | bitre azonos ismétlés a 2026-07-15-i teljes napi fájlban | outputs/pipeline_napok.csv, nap=2026-07-15, dup_arany 0.54601 | 2026-10-25 |
| 23,7% (negyedére) | a Parquet-tároló mérete a letöltött ZIP-hez képest, 2026-07-15 | outputs/pipeline_napok.csv, 2026-07-15: parquet_mib 226.8 / zip_mib 955.7 = 0,2373 | 2026-10-25 |
| 2,82–6,17 GiB (jún–aug); 2,75–6,17 GiB (128 nap) | napi kicsomagolt CSV-méret | pipeline_napok.csv csv_mib/1024, statusz=='validalt'; min 2026-08-07 ill. 2026-09-05, max 2026-08-14 | 2026-10-25 |
| 132,9–236,4 MiB (jún–aug); 124,4–236,4 MiB (128 nap) | napi Parquet-tároló mérete | pipeline_napok.csv parquet_mib; min 07-03 ill. 09-05, max 07-16 | 2026-10-25 |
| 4,73 / 5,32 / 5,01 GiB; 15,06 GiB; 23,58% | Parquet-tároló havonta (jún, júl, aug), három hónapra; a ZIP-hez viszonyítva | pipeline_napok.csv havi parquet_mib-összeg /1024; sum(parquet)/sum(zip) | 2026-10-25 |
| 6 248 MiB; 36 650 571 sor; 955,7 MiB; 54,6% / 56,0% | a 2026-07-15-i nap: kicsomagolt méret, sorszám, ZIP-méret, duplikátumarány (teljes / vizsgált terület) | pipeline_napok.csv, nap=='2026-07-15': csv_mib, nyers_sor, zip_mib, dup_arany=0.54601, bbox_dup_arany=0.56027 | 2026-10-25 |
| 128 nap (2026-06-01 – 2026-10-06) | a Parquet-tároló validált napjai, a 4.5 kísérleti kapuk ablaka | outputs/pipeline_napok.csv statusz == validalt (128; 2 nincs_adat) | 2026-10-25 |
| 1 979 – 1 999 sor (medián 1 994) | a napi H3-ellenőrző minta tényleges mérete (beállítás: 2000), mind egyezett | outputs/pipeline_napok.csv h3_minta_egyezik, 128 nap; scripts/pipeline.py H3_MINTA, USING SAMPLE a WHERE előtt | 2026-10-25 |
| 36 650 571 vs 36 752 804 sor | a mért nap (07-15) és a legnagyobb nap (08-14) nyers sorszáma a 128 napon | outputs/pipeline_napok.csv nyers_sor, nlargest | 2026-10-25 |
| 92 nap; 2 085 308 912 sor; 63,86 GiB | a skálázási minta (jún–aug.) validált napjai, nyers sorai és ZIP-mérete | outputs/pipeline_napok.csv 06-01 – 08-31: sum(nyers_sor), sum(zip_mib)/1024 | 2026-10-25 |
| 2,82–6,17 GiB (jún–aug.); 2,75–6,17 GiB (128 nap) | napi kicsomagolt CSV-méret | pipeline_napok.csv csv_mib/1024, statusz=='validalt'; min 2026-08-07 ill. 2026-09-05, max 2026-08-14 | 2026-10-25 |
| 132,9–236,4 MiB (jún–aug.); 124,4–236,4 MiB (128 nap) | napi Parquet-tároló mérete | pipeline_napok.csv parquet_mib; min 07-03 ill. 09-05, max 07-16 | 2026-10-25 |
| 4,73 / 5,32 / 5,01 GiB; 15,06 GiB; 23,58% | Parquet-tároló havonta (jún., júl., aug.), három hónapra; a ZIP-hez viszonyítva | pipeline_napok.csv havi parquet_mib-összeg /1024; sum(parquet)/sum(zip) | 2026-10-25 |
| 128 nap (2026. június 1. – október 6.) | a Parquet-tároló validált napjai, a 4.5 kísérleti kapuinak ablaka | outputs/pipeline_napok.csv, statusz == validalt (128; 2 nincs_adat) | 2026-10-25 |
| 1 979–1 999 sor (medián 1 994) | a napi H3-ellenőrző minta tényleges mérete (beállítás: 2000), mind egyezett | outputs/pipeline_napok.csv h3_minta_egyezik, 128 nap; scripts/pipeline.py H3_MINTA, USING SAMPLE a WHERE előtt | 2026-10-25 |
| 36 650 571, ill. 36 752 804 sor | a mért nap (07-15) és a legnagyobb nap (08-14) nyers sorszáma a 128 napon | outputs/pipeline_napok.csv nyers_sor, nlargest | 2026-10-25 |
| 92 nap; 2 085 308 912 sor; 63,86 GiB | a skálázási minta (jún.–aug.) validált napjai, nyers sorai és ZIP-mérete | outputs/pipeline_napok.csv 06-01 – 08-31: sum(nyers_sor), sum(zip_mib)/1024 | 2026-10-25 |

### Éles üzem és stabilitás (K1, K6, K10, K11, K13)

| szám | jelentés | szkript / forrás | dátum |
|------|----------|------------------|-------|
| 16/16 | ütemezett éles futás 2026-10-10 – 10-25, mind sikeres, futásidő 92–143 mp | outputs/eles_uzem/futasok.csv, event=schedule | 2026-10-25 |
| 3/128 | a „Mindkét kapu” sorozat múltbeli napjai közül ennyi minősült át három új nap alatt (dae2366 → 8954e7f; küszöb 0,2303 → 0,2093; 07-05, 08-29, 09-06) | python -X utf8 scripts/atminosites.py dae2366 8954e7f --ki $TEMP/ell21/x.csv | 2026-10-25 |
| 16 / 16 | ütemezett éles futás 2026-10-10 és 10-25 között, mind sikeres; futásidő 92–143 mp (medián 124), indulás 07:59–11:14 UTC | $TEMP/ell21/eles.py: outputs/eles_uzem/futasok.csv, event=='schedule' | 2026-10-25 |
| D+3 | mind a 16 éles lépés a futás napja előtti 3. napot dolgozta fel | $TEMP/ell21/eles.py: atminosites_lanc.csv, commit_datum − utolso_nap egyedi értékei = [3] | 2026-10-25 |
| 29 (14/16 lépés); 26 (9/16 lépés) | átminősítés az éles üzemben: forgalmi sorozatok összesen (Mindkét kapu 13/10, Øresund 14/10, Nagy-Balti-öv 2/2), illetve a megrakott tanker; a K13 tehát továbbra sem teljesül ([350]) | $TEMP/ell21/eles.py: atminosites_lanc.csv groupby fajl/uj/sorozat | 2026-10-25 |
| 16 / 16 | ütemezett éles futás 2026-10-10 – 10-25, mind sikeres (korábban: ~~3 / 3 (10-10 – 10-12)~~) | outputs/eles_uzem/futasok.csv, event == schedule, conclusion == success | 2026-10-25 |
| 16/16 | ütemezett éles futás 2026-10-10 – 10-25, mind sikeres | outputs/eles_uzem/futasok.csv, event=schedule, conclusion=success | 2026-10-25 |
| 3/128 | a „Mindkét kapu” sorozat átminősített múltbeli napjai három új nap alatt (dae2366 → 8954e7f; július 5., augusztus 29., szeptember 6.) | python -X utf8 scripts/atminosites.py dae2366 8954e7f (csak olvas) | 2026-10-25 |
| 29 átminősítés, a 16 napi lépésből 14-ben; megrakott tanker: 26, 9 lépésben | éles üzem, napi átminősítés-lánc (K13 nem teljesül, a [350] minősítése marad) | outputs/eles_uzem/atminosites_lanc.csv, groupby fajl/uj: jelzesek.csv sum 29, >0 lépés 14/16; jelzesek_megrakottsag.csv sum 26, 9/16 | 2026-10-25 |
| D+3 | mind a 16 éles lépés a futás előtti 3. napot dolgozta fel (a [332] marad) | outputs/eles_uzem/atminosites_lanc.csv: (commit_datum − utolso_nap).days = 3 mind a 96 sorban | 2026-10-25 |
| 16 / 16; 92–143 mp (medián 124) | ütemezett éles futások 2026. október 10. és 25. között, mind sikeres; futásidő | outputs/eles_uzem/futasok.csv, event = schedule: 16 sor, conclusion success 16; futasido_mp min 92, max 143, medián 124 | 2026-10-25 |
| 16 / 16 | ütemezett futás 2026-10-10 – 10-25, mind sikeres | outputs/eles_uzem/futasok.csv event == schedule, conclusion | 2026-10-25 |
| 07:59 – 11:14 UTC | a 16 ütemezett futás tényleges indulási sávja (korábban: ~~10:04–11:14 (javitando.md 9.)~~) | outputs/eles_uzem/futasok.csv inditas_utc (schedule): min 10-17 07:59, max 10-12 11:14 | 2026-10-25 |
| 29 átminősítés, a 16 napi lépésből 14-ben; megrakott tanker: 26, 9 lépésben | éles üzem, napi átminősítés-lánc (a K13 nem teljesül, a [350] minősítése marad) | outputs/eles_uzem/atminosites_lanc.csv, groupby fajl/uj: jelzesek.csv sum 29, >0 lépés 14/16; jelzesek_megrakottsag.csv sum 26, 9/16 | 2026-10-25 |
| 16 / 16 | ütemezett futás 2026. október 10. – 25., mind sikeres | outputs/eles_uzem/futasok.csv, event == schedule, conclusion | 2026-10-25 |
| 07:59–11:14 UTC | a 16 ütemezett futás tényleges indulási sávja (korábban: ~~10:04–11:14 (javitando.md 9.)~~) | outputs/eles_uzem/futasok.csv inditas_utc (schedule): min 10-17 07:59, max 10-12 11:14 | 2026-10-25 |
| 16 / 16 | ütemezett éles futás 2026. október 10. – 25., mind sikeres (korábban: ~~3 / 3 (október 10. – 12.)~~) | outputs/eles_uzem/futasok.csv, event == schedule, conclusion == success | 2026-10-25 |
| 3/128 nap (16 új nap alatt) | K13: a „Mindkét kapu” nettó átminősített múltbeli napjai, dae2366 → f8603b3 (07-05, 08-29, 09-06) (korábban: ~~3/128 nap három új nap alatt~~) | python scripts/atminosites.py dae2366 f8603b3 | 2026-10-25 |
| 16 / 16 | Sikeres ütemezett futás, 2026-10-10 – 10-25 (korábban: ~~3 / 3~~) | outputs/eles_uzem/futasok.csv event=schedule | 2026-10-25 |
| 07:59–11:14 UTC; 4,5–7,7 óra | Ütemezett futások indulása és késése 03:30-hoz képest (korábban: ~~10:04–11:14; 6,5–7,7 óra~~) | outputs/eles_uzem/futasok.csv inditas_utc | 2026-10-25 |
| 384 \| 0 \| 0 \| 256 \| 3 \| Mindkét kapu 9 → 12 | 21. táblázat forgalmi sor (dae2366 → f8603b3), változatlan | python scripts/atminosites.py dae2366 f8603b3; saját pandas-összevetés | 2026-10-25 |
| 366 \| 187 \| 158 \| 366 \| 3 \| Megrakott tanker 7 → 10 | 21. táblázat megrakottsági sor (dae2366 → f8603b3) (korábban: ~~366 \| 64 \| 64 \| 366 \| 5 \| 7 → 2~~) | python scripts/atminosites.py dae2366 f8603b3 --fajl jelzesek_megrakottsag.csv; saját összevetés (érték 187, alapszint 158; a módszer c091806 → 8954e7f-en 64 / 64-et ad) | 2026-10-25 |
| 29 átminősítés, 14/16 lépés, 7 pár | Forgalmi átminősítések a napi lépésekben | outputs/eles_uzem/atminosites_lanc.csv (jelzesek.csv) | 2026-10-25 |
| 26 átminősítés, 9/16 lépés, 10 nap; jelzett napok 2–10 | Megrakott tanker átminősítései a napi lépésekben | atminosites_lanc.csv; saját git show-lánc a 17 állapoton | 2026-10-25 |
| 16 / 16 | Sikeres ütemezett futás, 2026. október 10–25. (korábban: ~~3 / 3~~) | outputs/eles_uzem/futasok.csv event=schedule | 2026-10-25 |
| 92–143 s (1 perc 32 mp – 2 perc 23 mp) | Ütemezett futás teljes ideje (korábban: ~~105–143 s~~) | outputs/eles_uzem/futasok.csv futasido_mp | 2026-10-25 |
| #2: nyitva október 11., lezárva október 13., 2 megjegyzés | Az éles üzem egyetlen jelzés-issue-ja | gh issue view 2 --comments; gh issue list --state all; outputs/eles_uzem/issuek.csv | 2026-10-25 |
| 29 átminősítés, 14 / 16 lépés, 7 (nap, sorozat) pár | Forgalmi átminősítések a napi lépésekben | outputs/eles_uzem/atminosites_lanc.csv (jelzesek.csv) | 2026-10-25 |
| 26 átminősítés, 9 / 16 lépés, 10 nap; jelzett napok 2–10 | Megrakott tanker átminősítései a napi lépésekben | outputs/eles_uzem/atminosites_lanc.csv; saját git show-lánc a 17 állapoton | 2026-10-25 |
| 16/16 | sikeres ütemezett éles futás 2026-10-10 – 10-25, mindegyik egy új adatnappal (10-07 – 10-22) (korábban: ~~3/3~~) | outputs/eles_uzem/futasok.csv event=schedule; atminosites_lanc.csv utolso_nap | 2026-10-25 |
| 92–143 mp (1 perc 32 mp – 2 perc 23 mp) | éles futás teljes ideje, 16 ütemezett futás (korábban: ~~105–143 mp~~) | outputs/eles_uzem/futasok.csv futasido_mp | 2026-10-25 |
| 07:59–11:14 UTC | az ütemezett futások indulása (korábban: ~~10:04–11:14 UTC~~) | outputs/eles_uzem/futasok.csv inditas_utc | 2026-10-25 |
| 29 / 26 | K13: múltbeli napi átminősítés az éles üzem 16 lépésében, forgalmi sorozatok / megrakott tanker (korábban: ~~5 eltűnt jelzés (megrakott tanker, c091806 → 8954e7f)~~) | outputs/eles_uzem/atminosites_lanc.csv, atminositett összeg sorozatonként | 2026-10-25 |
| 16/16 | sikeres ütemezett éles futás 2026. október 10. – 25., mindegyik egy új adatnappal (10-07 – 10-22) (korábban: ~~3/3~~) | outputs/eles_uzem/futasok.csv event=schedule; outputs/eles_uzem/atminosites_lanc.csv utolso_nap | 2026-10-25 |
| #2: 2 megjegyzés, lezárva 2026. október 13.; új issue nem nyílt | az éles issue-k története október 25-ig (korábban: ~~1 megjegyzés~~) | outputs/eles_uzem/issuek.csv; gh issue view 2 --json comments; gh issue list --state all | 2026-10-25 |


### Éles üzem: napi sorszámok a futásnaplókból (2026-10-07 – 10-22)

A 16 nap Parquet-fájlja a futtatón törlődött, a számok csak a GitHub futásnaplóiban voltak meg (90 napos megőrzés). A naplók lementve: `outputs/eles_uzem/futasnaplok/<run_id>.txt` (`gh run view <id> --log`, 2026-10-28). Napi bontás: `outputs/eles_uzem/napi_sorok.csv`. A 16 napot független forrással nem lehetett összevetni, mert a helyi tárolóban nincsenek meg (az csak 06-01 – 10-06-ig tart). Az egyetlen ellenőrzés a futtató saját validálása: ZIP-sorszám = SUM(dup_db), a naplóban „VALIDALT”, és a közvetlen ZIP-sorszámlálás minden napon egyezik a nyers sorszámmal.

| szám | jelentés | szkript / forrás | dátum |
|------|----------|------------------|-------|
| 16 / 16 | validált nap a 10-10 – 10-25-i ütemezett futásokban, futásonként egy nap (10-07 – 10-22) | scripts/napi_sorok.py → outputs/eles_uzem/napi_sorok.csv | 2026-10-28 |
| 266 411 000 | nyers sor összesen, 10-07 – 10-22 (16 nap) | napi_sorok.csv, nyers_sor összege | 2026-10-28 |
| 165 812 066 | deduplikált sor összesen, 10-07 – 10-22 | napi_sorok.csv, dedup_sor összege | 2026-10-28 |
| 15 714 117 – 18 169 048; medián 16 545 703,5 | napi nyers sorszám, min. (10-09) – max. (10-07) és medián, 16 nap | napi_sorok.csv | 2026-10-28 |
| 2 058,9 MiB / 9 275,8 MiB | Parquet / ZIP összesen, 16 nap (a napló egy tizedesre kerekít; a ZIP-sor „MB” felirata valójában MiB, letoltes.py: / 1 048 576) | napi_sorok.csv | 2026-10-28 |
| 36 650 571 / 16 638 836 | 2026-07-15, a két erőforrás-mérési futás (37910491337, 37914275224) nyers / dedup. sora; DuckDB a helyi Parquet-fájlon (SUM(dup_db), count(*)): mindkettő egyezik | napi_sorok.py → outputs/eles_uzem/napi_sorok_ellenorzes.csv | 2026-10-28 |
| 227,0 vs. 226,8 MiB | 2026-07-15 Parquet-mérete: 1. futás 227,0 (−0,15 MiB eltérés a helyi 226,847 MiB-os fájltól, a kerekítési határon túl); 2. futás 226,8 (egyezik). Az eltérés megmarad, nincs kiigazítva. | napi_sorok_ellenorzes.csv | 2026-10-28 |


### Mérőszám-hatás a 144 napos idősoron (a 3.4 Kiel-esetének cseréje)

A 3.4 mérőszám-esete (+96 / +20 / +4%) a Kiel-napokra épült. A hallgató döntése (2026-10-28) szerint a Kiel-eset kikerül, és ugyanez az összehasonlítás a teljes fagyasztott idősoron fut, minden napra. Két kapu összesítve, 123 nap (amelyhez a hétnaphoz illesztett alapszint is van). A: minden hajó, a 123 nap mediánjához mérve; B: minden hajó, a monitor alapszintjéhez mérve; C: kereskedelmi, a monitor alapszintjéhez mérve (= a monitor „Mindkét kapu” sorozata, 144/144 napon egyezik a fagyasztott jelzesek.csv-vel). Küszöb: 2 × 1,4826 × MAD, a saját sorozatból. A régi +96/+20/+4% számok érvényesek maradnak (az ötnapos mintára), csak a dolgozat szövegéből kerülnek ki. Az óránkénti hajószám a fagyasztott állapotból nem számolható: NEM VIZSGÁLT.

| szám | jelentés | szkript / forrás | dátum |
|------|----------|------------------|-------|
| 123 / 144 | összevethető nap (B-nek és C-nek is van alapszintje) | scripts/mertekszam_hatas.py --ki outputs/kiel_csere/ (bemenet: outputs/fagyasztas_2026-10-22/monitor/kapuvonal_napi.csv) | 2026-10-28 |
| 35,4% / 25,8% / 10,6% | robusztus szórás, A / B / C | mertekszam_osszegzes.csv (0,3537 / 0,2577 / 0,1057) | 2026-10-28 |
| ±70,7% / ±51,5% / ±21,1% | jelzési küszöb, A / B / C | mertekszam_osszegzes.csv (0,7074 / 0,5153 / 0,2115) | 2026-10-28 |
| 2 / 5 / 12 | jelzett nap, A / B / C (C: 9 magas, 3 alacsony) | mertekszam_osszegzes.csv | 2026-10-28 |
| 18,2 / 23,8 / 14,1 szp | ugyanazon nap eltérésének medián abszolút különbsége, B–C / A–C / A–B | mertekszam_osszegzes.csv | 2026-10-28 |
| 57 / 54 / 22 | ellentétes előjelű nap a 123-ból, B–C / A–C / A–B | mertekszam_osszegzes.csv | 2026-10-28 |
| 0 / 0 / 1 | mindkét változatban jelzett nap, B–C / A–C / A–B | mertekszam_osszegzes.csv | 2026-10-28 |
| 17 / 14 / 5 | eltérően minősített nap (jelzett vs. normál), B–C / A–C / A–B | mertekszam_osszegzes.csv | 2026-10-28 |
| +39,8% (2026-08-18) | a C sorozat legnagyobb pozitív eltérése a 123 napon | mertekszam_napi.csv, elteres_C max = 0,3977 | 2026-10-28 |
| 0,813 / 0,252 / 0,221 | az eltérések korrelációja, A–B / A–C / B–C | mertekszam_napi.csv, pandas corr (kézi ellenőrzés) | 2026-10-28 |


### Hormuz-elemzés: 3. fázis (a minta feldolgozása) és 4. fázis (becslés, érzékenység)

Előzetes mérce: `dolgozat/hormuz_elozetes_merce.md` és két kiegészítése (2026-10-28, 2026-10-29), commitok: 0807fd3, 0e07d4e. A becslés a különbségek különbsége, (B26 − A26) − (B25 − A25), 95%-os heti blokkos bootstrap-intervallummal (2 000 ismétlés, seed 20261028) és Holm-korrekcióval (H1–H3). Hatásról akkor beszélünk, ha a H1 vagy a H2 Holm-korrigált intervalluma nem tartalmazza a nullát. A 4. fázist kétszer futtattam: az első futás az ábránál elszállt, a második az ábrajavítás után ment végig. A számok a két futásban azonosak.

| szám | jelentés | szkript / forrás | dátum |
|------|----------|------------------|-------|
| 76 / 76 | feldolgozott és validált mintanap (A26 14, B26 24, A25 14, B25 24); minden napon SUM(dup_db) = ZIP-sorszám; a 2026-05-14 a 2. kísérletre (1.: DuckDB OutOfMemory) | scripts/hormuz_napi.py --kozvetlen-zip → outputs/hormuz/feldolgozas.csv | 2026-10-30 |
| 1 465 611 774 / 812 936 600 | nyers / deduplikált AIS-sor, 76 nap | feldolgozas.csv (zip_sor, dedup_sor összege) | 2026-10-30 |
| 213 919 160 sor, 3 122,6 MiB | a szűrt (bbox) tároló, 76 nap | feldolgozas.csv; hormuz_napi.py --osszesito | 2026-10-30 |
| 10 279 / 2 398 | átkelés / ebből tanker a két monitorkapun (Nagy-Balti-öv, Øresund), 76 nap | feldolgozas.csv (atkeles_monitor, tanker_monitor) | 2026-10-30 |
| 7 383 / 986 | átkelés / ebből tanker az Øresund – Drogden kapun | feldolgozas.csv | 2026-10-30 |
| 76 / 76 | nap, amelyen a nyers és a súlyozatlan duplikátum-változat átkelésszáma egyezik a fő változatéval | feldolgozas.csv (atkeles_nyers, atkeles_sulyozatlan) | 2026-10-30 |
| 1 182 / 1 119 / 663 | kifelé haladó tanker-átkelés / ebből megrakottság szerint értékelhető / ebből megrakott (H1 összege) | scripts/hormuz_elemzes.py (b3606ac + ábrajavítás) → mintanap_mutatok.csv | 2026-10-30 |
| 11 666 | hajó, amelynek a max. merülése (P95) a régi (144 nap) és az új (76 nap) merülés-történetből számolva van | hormuz_elemzes.py, kimenet | 2026-10-30 |
| 7,93 / 8,54 / 9,21 / 9,08 | H1 ablakátlag, A26 / B26 / A25 / B25 (megrakott kifelé haladó tanker-átkelés / nap) | outputs/hormuz/eredmeny.csv | 2026-10-30 |
| +0,744 [−1,631; 3,113] | H1 DiD, 95% CI; Holm: [−2,224; 3,601], p_bootstrap 0,577, nem elvetett | eredmeny.csv | 2026-10-30 |
| 0,171 / 0,210 / 0,147 / 0,211 | H2 ablakarány, A26 / B26 / A25 / B25 (Szuez/Ázsia/Közel-Kelet a megrakott kifelé haladók között) | eredmeny.csv | 2026-10-30 |
| −0,025 [−0,132; 0,090] | H2 DiD, 95% CI; Holm: [−0,147; 0,107], p_bootstrap 0,698, nem elvetett | eredmeny.csv | 2026-10-30 |
| −33 467 [−301 471; 215 167] m³/nap | H3 DiD (volumenindex), 95% CI; p_bootstrap 0,786, nem elvetett | eredmeny.csv | 2026-10-30 |
| nem mutatható ki | a mérce szerinti fő következtetés (sem H1, sem H2 nem elvetett Holm után) | eredmeny.csv; hormuz_elemzes.py kimenet | 2026-10-30 |
| 0 / 16 sor | érzékenységi sor (a fő és az 1–6. változat), amelyben a fő következtetés megváltozik; egyikben sem kimutatható a hatás sem 95%-os CI-vel, sem Holm után | outputs/hormuz/erzekenyseg.csv | 2026-10-30 |
| +0,613 / −0,021 | 1. Drogden: H1 / H2 DiD (CI: [−1,982; 3,191] / [−0,132; 0,097]) | erzekenyseg.csv | 2026-10-30 |
| +0,744 / −0,025 | 2a. nyers duplikátumok: H1 / H2 DiD, a fő változattal azonos (H1 összeg 663 / 663) | erzekenyseg.csv; hormuz_elemzes.py kimenet | 2026-10-30 |
| +0,827 / −0,027 | 2b. súlyozatlan: H1 / H2 DiD (CI: [−1,554; 3,156] / [−0,135; 0,088]) | erzekenyseg.csv | 2026-10-30 |
| +0,530 / −0,015 | 3. küszöb 0,7648: H1 / H2 DiD (CI: [−2,067; 3,042] / [−0,112; 0,090]) | erzekenyseg.csv | 2026-10-30 |
| +0,863 / −0,026 | 3. küszöb 0,8648: H1 / H2 DiD (CI: [−1,620; 3,232] / [−0,137; 0,095]) | erzekenyseg.csv | 2026-10-30 |
| −0,030 [−0,150; 0,108] | 4. FOR ORDER nélküli nevező: H2 DiD | erzekenyseg.csv | 2026-10-30 |
| −0,021 [−0,138; 0,110] | 6. engedékeny úticél-olvasat: H2 DiD | erzekenyseg.csv | 2026-10-30 |
| 72,4 / 72,0 / 66,5 / 67,5% | úticél értelmezhető, szigorú (fő) olvasat, kifelé haladó tanker, A26 / B26 / A25 / B25 (144/199, 254/353, 147/221, 276/409) | outputs/hormuz/uticel_ertelmezhetoseg.csv | 2026-10-30 |
| 73,0 / 75,1 / 72,1 / 71,6% | ugyanez a H2 nevezőjében (megrakott, kifelé haladó): 81/111, 154/205, 93/129, 156/218 | uticel_ertelmezhetoseg.csv | 2026-10-30 |
| 85,4 / 85,8 / 81,5 / 84,4% | úticél értelmezhető, engedékeny olvasat, kifelé haladó tanker, A26 / B26 / A25 / B25 (170/199, 303/353, 180/221, 345/409) | uticel_ertelmezhetoseg.csv | 2026-10-30 |
| 82,9 / 84,9 / 81,4 / 84,4% | ugyanez a H2 nevezőjében: 92/111, 174/205, 105/129, 184/218 | uticel_ertelmezhetoseg.csv | 2026-10-30 |
| 0 | RU úticélú megrakott, kifelé haladó tanker-átkelés, mind a négy ablakban (szigorú olvasat) | outputs/hormuz/uticel_osszetetel.csv | 2026-10-30 |


### Hormuz-elemzés: az úticél-eltérés lefedettsége és a minimális kimutatható hatás

Az MDE utólagos számítás, nem a mérce része; a döntési szabályt és a fő eredményt nem érinti. MDE = (z(1−α/2) + z(0,80)) × SE, az SE a különbségek különbségének bootstrap-szórása (ugyanazok a húzások, mint a fő elemzésben; a szkript ellenőrzi az egyezést az eredmeny.csv-vel). Viszonyítási szint: az A26 ablakátlag.

| szám | jelentés | szkript / forrás | dátum |
|------|----------|------------------|-------|
| 11 293 / 11 359 (99,4%) | átkelés aznapi úticél-előzménnyel / összes (a monitor- és a Drogden-kapuk, minden hajótípus); a 24 órás ablak helyett aznapi keresés, a hallgató jóváhagyásával | outputs/hormuz/feldolgozas.csv (uticel_elotte_van, uticel_atkeles) | 2026-10-31 |
| 99,8 / 99,4 / 99,3 / 99,2% | ugyanez ablakonként, A26 / B26 / A25 / B25 (1 954/1 957, 3 492/3 512, 2 110/2 124, 3 737/3 766) | feldolgozas.csv | 2026-10-31 |
| 3,43 átkelés/nap (43,2%) | H1 MDE, 80% erő, α = 0,05 (SE 1,2228; A26-szint 7,9286) | scripts/hormuz_mde.py → outputs/hormuz/mde.csv | 2026-10-31 |
| 0,159 (93,1%) | H2 MDE, 80% erő, α = 0,05 (SE 0,0569; A26-szint 0,1712) | mde.csv | 2026-10-31 |
| 374 418 m³/nap (41,0%) | H3 MDE, 80% erő, α = 0,05 (SE 133 645; A26-szint 913 934) | mde.csv | 2026-10-31 |
| 3,96 (49,9%) / 0,184 (107,6%) / 432 422 (47,3%) | H1 / H2 / H3 MDE a Holm első lépcsőjén (α = 0,05/3), 80% erő | mde.csv (mde_holm1, mde_holm1_szint_arany) | 2026-10-31 |
| 3,39 / 0,159 / 369 243 | H1 / H2 / H3 MDE az SE percentilis-intervallumból számolt változatával (a normális közelítés ellenőrzése) | mde.csv (mde_percentilisbol) | 2026-10-31 |
