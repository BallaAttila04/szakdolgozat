# Validált számok

Minden szám ide csak akkor kerül, ha ténylegesen lefuttatott szkript
eredménye — forrással (szkript, paraméterek, dátum). Ha egy szám
megváltozik, ne írd felül: húzd át és írd mellé az újat, indoklással.

## Forgalmi kiértékelés (dán szorosok, 54.5–56.5°N, 10.0–13.0°E)

Forrás: `forgalom_elemzes.py`, kimenet `forgalmi_osszefoglalo.csv`,
lefuttatva 2026-09-18 (ld. `naplo.md`, 22:10-es bejegyzés).

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
különbség felbontható (ld. `naplo.md`, 2026-09-19 20:44):

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
duckdb 1.5.5 (ld. `naplo.md`, 22:47-es bejegyzés).

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
lefuttatva 2026-09-19 a `data/aisdk-2026-07-15.zip` fájlon (ld. `naplo.md`,
2026-09-19 21:07-es bejegyzés). Bounding box: 54.5–56.5°N, 10.0–13.0°E.
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
2026-09-19, 5 ismétlés / medián (ld. `naplo.md`, 2026-09-19 21:13).
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
