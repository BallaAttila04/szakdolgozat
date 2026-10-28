# Hormuz-elemzés – a mérce kiegészítése (2026-10-28 12:20)

**Ok:** a Kiel-eset kikerült, ezért a KK2 („mennyiben határozzák meg a feldolgozási döntések az
eredményt”) esetpéldája a Hormuz-elemzés lesz.

**Ez a kiegészítés az eredeti mércét nem módosítja** (`hormuz_elozetes_merce.md`). A fő elemzés
döntési szabálya változatlan. Az alábbiak másodlagos, érzékenységi elemzések, és az adatok
feldolgozása előtt kerültek rögzítésre.

A H1 és a H2 becslését (különbségek különbsége, 95%-os bootstrap-intervallum) az alábbi
változatokkal is el kell végezni. Mindegyiknél azt kell közölni, hogy a fő következtetés
(kimutatható vagy nem) megváltozik-e:

1. **Mérési hely:** az Øresund-kapu helyett az „Øresund – Drogden” kapu (scripts/kapuk.json).
2. **Duplikátumszűrés:** az átkelésszám a deduplikált adaton (fő változat), illetve a nyers
   ismétlődésekkel (dup_db szerint súlyozott pozíciók). Ha ez a kapuvonal-logikában nem
   értelmezhető, annak indoklása kerüljön a naplóba.
3. **Megrakottsági küszöb:** 0,8148 helyett 0,7648 és 0,8648.
4. **Úticél:** a FOR ORDER kategória a fő változatban külön szerepel; ebben a változatban
   kimarad a nevezőből.
5. **Mérőszám:** megrakott átkelések száma (H1) kontra volumenindex (H3). Ez már a fő elemzésben
   szerepel, itt csak az összevetés kell.

**Kimenet:** `outputs/hormuz/erzekenyseg.csv`, változatonként egy sor: becslés, intervallum,
következtetés.
