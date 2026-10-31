# Hormuz-elemzés – 3. kiegészítés: kiterjesztett minta (robusztussági elemzés)

**Rögzítve:** 2026-10-31 12:29 UTC. A fő eredmény (76 mintanap, kedd és csütörtök) ekkor már ismert volt: hatás nem
mutatható ki (naplo.md, 2026-10-30 04:09). Ez a kiegészítés **utólagos**, a fő eredményt és az eredeti mércét
(`hormuz_elozetes_merce.md`, valamint a 2026-10-28-i és 2026-10-29-i kiegészítések) nem módosítja. A
kiterjesztett minta eredménye a dolgozatban kizárólag „kiterjesztett minta, a fő eredmény ismeretében, utólag
hozzáadva” címkével szerepelhet, robusztussági elemzésként.

**Minta:** ugyanaz a négy ablak (A26: 2026-01-12 – 02-27, B26: 2026-03-09 – 05-29, A25: 2025-01-13 – 02-28,
B25: 2025-03-10 – 05-30), de **minden nap**, összesen 258 nap. A már feldolgozott 76 nap újrafelhasználható, a
hiányzó 182 nap ugyanazzal a lánccal (`scripts/hormuz_napi.py`) dolgozandó fel. Hiányzó vagy sérült napot
nem pótolunk más nappal, csak naplózzuk.

**Változatlan:** a mutatók (H1–H3), a megrakottsági definíció és a 0,8148-es küszöb, az úticél-kategóriák (a fő,
szigorú olvasat), az aznapi úticél-szabály, a különbségek különbsége, a heti blokkos bootstrap (2 000 ismétlés,
ugyanaz a mag), a Holm-korrekció és a döntési szabály. Az MDE ugyanazzal a módszerrel számolandó.

**Közlendő:** a fő és a kiterjesztett minta becslése, 95%-os és Holm-korrigált intervalluma, a következtetés és az
MDE egymás mellett. Ha a két minta következtetése eltér, az eltérést közölni kell, a fő eredmény akkor is a
76 napos marad.
