# Hormuz-elemzés – a mérce második kiegészítése (2026-10-29 21:33)

**Ok:** az úticél-osztályozás a fő változatban szigorú: a Destination mező csak akkor
értelmezhető UN/LOCODE-ként, ha a teljes mező egyetlen érvényes kód („NLRTM” vagy „NL RTM”).
Az „X VIA Y”, a „KÓD + szöveg” és a több kódot tartalmazó mezők ezért „Nem értelmezhető”
kategóriába kerülnek. Ez a H2 nevezőjét és számlálóját is érintheti.

**Ez a kiegészítés sem az eredeti mércét (`hormuz_elozetes_merce.md`), sem az első
kiegészítést (`hormuz_merce_kiegeszites_2026-10-28.md`) nem módosítja.** A szigorú olvasat
marad a fő változat, és a fő elemzés döntési szabálya változatlan. Az alábbi változatot a
teljes minta feldolgozása közben, de a 4. fázis (a mutatók és a becslés) futtatása előtt
rögzítettem. A 4. fázis szkriptje (`scripts/hormuz_elemzes.py`) addig nem futott, ezért sem
a H1–H3 becslése, sem az úticél-kategóriák megoszlása, sem az értelmezhetőségi arány nem volt
ismert. A 2. fázis kétnapos próbája csak az átkelések számát és az úticél-előzmény meglétét
számolta. A szabályt csak az alábbi, kézzel írt példákon próbáltam ki.

## 6. érzékenységi változat: engedékeny úticél-olvasat

**Szabály:** a Destination mező első UN/LOCODE-szerű része számít.

1. A mezőt ugyanúgy normalizálom, mint a fő változatban (nagybetű, a szóközök összevonása,
   a szélek levágása).
2. A mezőben balról jobbra megkeresem az első UN/LOCODE-szerű részt:
   2 betű, legfeljebb egy szóköz, majd 3 karakter (betű vagy 2–9). Előtte és utána nem állhat
   betű vagy számjegy. Reguláris kifejezéssel:
   `(?<![A-Z0-9])([A-Z]{2}) ?([A-Z2-9]{3})(?![A-Z0-9])`.
3. Ha van ilyen rész, és az érvényes UN/LOCODE (ugyanabban a kódlistában, mint a fő
   változatban), akkor az országkódja adja a kategóriát, a fő változat országcsoportjai
   szerint.
4. Ha nincs ilyen rész, vagy az első ilyen rész nem érvényes kód, akkor a fő változat
   szabályai érvényesek a teljes mezőre (Szuez-szövegek, majd ORDER, egyébként „Nem
   értelmezhető”). Egy későbbi, érvényes kódot ilyenkor nem keresek: csak az első
   UN/LOCODE-szerű rész számít.

**Példák** (a fő változat → az engedékeny olvasat):

| Destination | fő (szigorú) | engedékeny |
|---|---|---|
| `NLRTM`, `NL RTM` | EU/EGT/UK | EU/EGT/UK |
| `BEANR VIA DENOK` | Nem értelmezhető | EU/EGT/UK (BEANR) |
| `EGPSD VIA SKAW` | Nem értelmezhető | Szuez/Ázsia/Közel-Kelet (EGPSD) |
| `RU ULU>NL RTM` | Nem értelmezhető | RU (RUULU) |
| `CNSHA/SGSIN` | Nem értelmezhető | Szuez/Ázsia/Közel-Kelet (CNSHA) |
| `TO NLRTM` | Nem értelmezhető | EU/EGT/UK (NLRTM) |
| `NLRTM FOR ORDERS` | FOR ORDER | EU/EGT/UK (NLRTM) |
| `FOR ORDERS` | FOR ORDER | FOR ORDER |
| `PORT SAID` | Szuez/Ázsia/Közel-Kelet | Szuez/Ázsia/Közel-Kelet |
| `SKAGEN`, `AT SEA` | Nem értelmezhető | Nem értelmezhető |

A „KÓD + szöveg” mezőkben a kód elsőbbséget kap az ORDER szöveggel szemben is
(`NLRTM FOR ORDERS` → EU/EGT/UK). Ezért ez a változat a FOR ORDER kategória méretét is
megváltoztathatja, nem csak a „Nem értelmezhető” kategóriáét.

**Mit kell közölni:**

- **H2:** becslés (különbségek különbsége), 95%-os bootstrap-intervallum, és hogy a fő
  következtetés (kimutatható vagy nem) megváltozik-e. Az `erzekenyseg.csv` sora, ugyanúgy,
  mint az 1–5. változatnál.
- **H1 és H3:** nem függenek az úticéltől, ezért ebben a változatban konstrukció szerint
  azonosak a fő változattal. Külön sort nem kapnak.
- **Értelmezhetőségi arány, mindkét olvasatnál, ablakonként** (A25, B25, A26, B26):
  - a kifelé haladó tanker-átkelések között;
  - a megrakott, kifelé haladó tanker-átkelések között (a H2 nevezője).

  Kimenet: `uticel_ertelmezhetoseg.csv`, olvasatonként külön sorokkal.
