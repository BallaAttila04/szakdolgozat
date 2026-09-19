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
