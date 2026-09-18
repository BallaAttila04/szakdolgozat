# Szakdolgozat – átadás a Cowork beszélgetésnek

## Alapadatok
- Gazdaságinformatikus BSc, Budapesti Corvinus Egyetem.
- Regisztrált téma: AIS hajókövetési adatok és Sentinel-1 SAR felvételek
  együttes elemzése (eredetileg SAR-alapú, ld. lent, miért változott).
- Leadás: 2026.11.23–12.04 (Neptun). Záróvizsga: 2027.01.18–22.
- Mérföldkövek: 09.21 vázlat+problémaleírás+források, 10.05 irodalmi
  fejezet (min. 10 o.), 10.19 60% (min. 20 o.), 11.04 majdnem kész.
- Kutatásalapú dolgozattípus, min. 30 oldal, APA hivatkozás,
  Times New Roman 12, másfeles sortáv. AI-t csak ötletelésre, forrás-
  keresésre, saját szöveg/kód javítására és vizualizációra szabad
  használni; a szöveget a hallgató írja, a végén AI-nyilatkozat kell.

## Hogyan jutottunk el idáig
1. Eredeti irány: AIS + Sentinel-1 SAR, dark vessel detektálás
   (xView3-SAR adathalmaz). Megvalósíthatósági tesztet futtattunk:
   - AIS oldal működik (DMA napi CSV, dán szorosok).
   - xView3 validation splitben 10 dán jelenet, 4585 detektálás,
     ebből 2304 NEM hajó (fix infrastruktúra, valószínűleg
     szélerőműpark) — csak is_vessel=True szűrés után marad 2267
     hajó, 46%-uk AIS nélküli.
   - DE: minden xView3 felvétel 2020-as, és nincs balti/szoros
     jelenet, csak Északi-tenger / Jylland körüli vizek.
2. Konzultáció a konzulenssel (2026.09.17): **a cím teljesen
   szabadon módosítható, a SAR-rész elejthető** (2020-as adat +
   nincs friss felvétel miatt). Új irány, amit jóváhagyott:
   **kizárólag AIS-adat feldolgozása, a hangsúly a nagy AIS-adat
   modern tárolási/feldolgozási módszereinek vizsgálatán van**
   (CSV → Parquet/DuckDB, esetleg H3 térbeli index, esetleg Spark
   ha nem fér el egy gépen).
3. Jelenlegi cél: automatikus letöltő az AIS napi fájlokhoz (2 nap
   elég most), utána a tárolás összehasonlítása (méret, beolvasási
   idő, lekérdezési idő CSV vs. Parquet vs. DuckDB).

## Amit eddig legyártottunk (fájlok, ezen a chat-felületen)
- `ais_teszt.py` — AIS CSV chunkolt beolvasása, bounding box +
  időablak szűrés, pillanatkép CSV + térkép PNG kimenettel.
  Sikeresen tesztelve a felhasználó gépén (2026-09-05, dán szorosok,
  1162 hajó a 10 perces ablakban).
- `letoltes.py` — DMA napi AIS ZIP-ek letöltője. Két forrás
  (S3-tükör elsődleges, web.ais.dk tartalék), .part-ba tölt,
  ZIP-magic-byte + méret ellenőrzés, újrafuttatható. **Nálam nincs
  internet, a tényleges letöltést a felhasználónak még tesztelnie
  kell.**
- `CLAUDE.md` — projektszabályok a VS Code-os Claude Code-nak:
  mappaszerkezet (data/scripts/outputs/naplo.md/szamok.md),
  kötelező munkanapló-vezetés minden lépés után (nyers terminál-
  kimenettel), számok forrás szerinti dokumentálása, validálási
  szabályok, szkript-konvenciók.

## Nyitott kérdések / következő lépések
- A "geopods" szó a konzulens jegyzetéből tisztázatlan — valószínűleg
  GeoPandas vagy GeoParquet, de nem erősítettük meg vele.
- Nem tisztázott, hogy a Spark-ot ténylegesen elvárja-e a konzulens,
  vagy csak példaként mondta ("ha nem fér el egy gépen").
- A letöltés (2 nap AIS adat) még nincs ténylegesen lefuttatva /
  visszaigazolva.
- A tárolási összehasonlítás (CSV vs. Parquet vs. DuckDB, mérés
  méretben és sebességben) még nem indult el — ez lesz a dolgozat
  első mérhető eredménye.
- A pontos szakdolgozat-cím még nincs végleges formában megfogalmazva,
  csak az irány (AIS nagy adat tárolás/feldolgozás modernizálása).

## Munkamegosztás, ami eddig kialakult
Ezen a (böngészős) chat-felületen: módszertan, struktúra, kritikai
visszajelzés, forráskeresés, a konzulenssel való kommunikáció.
Coworkban / VS Code-ban: tényleges kódolás, adatletöltés, futtatás.
A `naplo.md` és `szamok.md` fájlok (ld. CLAUDE.md) hivatottak hidat
képezni a kettő között — érdemes ezeket rendszeresen ideátölteni.
