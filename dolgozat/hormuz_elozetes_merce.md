# Hormuz-elemzés – előre rögzített mérce

**Rögzítve:** 2026-10-28, mielőtt a zár előtti AIS-napok le lettek volna töltve, illetve feldolgozva.
A már megnézett adatok (amelyek ezt a tervet befolyásolhatták) a naplo.md 2026-10-28 11:00-s
bejegyzésében szerepelnek: a PortWatch havi Øresund-sorai, a saját monitor június–októberi
szakaszai és a 2026-07-es úticél-összesítés. Ez a fájl utólag nem módosítható. Ha mégis
változtatni kell rajta, az új változat külön fájlba kerül, dátummal és indoklással, a régi pedig
megmarad.

## Kérdés
Megváltozott-e a balti tankerforgalom mennyisége, megrakottsága és úticélja a dán szorosokon a
Hormuzi-szoros 2026. február 28-i lezárása után?

## Feltételezett mechanizmus
Az ázsiai vevők elvesztik az öböl-menti olajat, ezért több balti, főleg orosz olajat vesznek.
Ennek a Balti-tengerből kifelé („észak”) haladó, megrakott, Szuez/Ázsia úticélú tankereken kell
látszania.

## Időszakok
- **A (zár előtt):** 2026-01-12 – 2026-02-27.
- **B (zárva):** 2026-03-09 – 2026-05-29. Az első, átmeneti hét kimarad.
- **Kontroll:** ugyanezek a naptári ablakok 2025-ben (A25: 2025-01-13 – 2025-02-28,
  B25: 2025-03-10 – 2025-05-30).
- **Mintavétel:** minden kedd és csütörtök az ablakokon belül. Hiányzó vagy sérült napot nem
  pótolunk más nappal, csak naplózzuk.
- **Másodlagos, nem döntő ellenőrzés:** a 2026-06-18 – 07-08 közötti részleges újranyitás a
  meglévő monitoradatban (0–30 napos késleltetéssel, leíró jelleggel).

## Mutatók (a kapuk: Nagy-Balti-öv és Øresund, ahogy a scripts/kapuk.json-ban szerepelnek)
- **H1:** a napi megrakott, kifelé („észak”) haladó tanker-átkelések száma (a két kapu összege).
- **H2:** a Szuez/Ázsia úticélú átkelések aránya a kifelé haladó, megrakott tanker-átkelésekben.
- **H3:** a kifelé haladó tankerek napi volumenindexe (Σ hossz × szélesség × merülés).

A megrakottság definíciója a megrakottsag.py szerinti. A hajó maximális merülése a teljes
(régi + új) minta napi merüléseinek 95. percentilise MMSI-nként. A tankerküszöb **rögzítve:
0,8148** (a fagyasztott állapot Otsu-értéke). Ezt nem számoljuk újra.

**Úticél:** a hajó utolsó nem üres Destination-értéke az átkelés előtti 24 órában. A
kategóriák előre rögzítve:
- **RU:** UN/LOCODE-országkód RU.
- **EU/EGT/UK:** EU-tagállamok, NO, IS, GB, CH.
- **Szuez/Ázsia/Közel-Kelet:** EG, SA, AE, OM, IN, PK, LK, BD, CN, SG, MY, ID, TH, VN, KR, JP, TW,
  PH, valamint a következő szövegek: PORT SAID, SUEZ, SINGAPORE, FUJAIRAH.
- **FOR ORDER:** a szövegben „ORDER” szerepel.
- **Egyéb:** minden más értelmezhető kód.
- **Nem értelmezhető.**

A LOCODE-ot a data/unlocode_code-list.csv-vel ellenőrizzük. A szóköz a kód két része
között megengedett.

## Becslés és döntési szabály
- **Különbségek különbsége:** (B26 − A26) − (B25 − A25), a napi átlagokon. H2-nél az arányokon.
- **Konfidenciaintervallum:** 95%-os, heti blokkos bootstrappel (2 000 ismétlés, a blokkok
  időszakon belül húzva).
- **Döntés:** H1–H3 együtt, Holm-korrekcióval. Hatásról akkor beszélünk, ha legalább a H1-nek
  vagy a H2-nek a korrigált intervalluma nem tartalmazza a nullát. Ellenkező esetben az
  eredmény: „a mintában Hormuz-hatás nem mutatható ki”. Ezt ugyanúgy megírjuk.
- **Külső kontroll (csak PortWatch, napi, 2019–2026):** az Øresund tankerforgalmát a Dover- és
  a Gibraltári-szoroséhoz viszonyítjuk, ugyanezzel a különbségek különbsége módszerrel.
- **Előzetes trend:** az Øresund tankerforgalma 2026 januárjában már −18%-kal alacsonyabb volt
  az előző évinél (PortWatch). Ezt a különbségek különbsége csak részben kezeli, ezért a
  szövegben kötelező kimondani.

## Ismert zavaró tényezők (a dátumokat ellenőrizni kell, és mindegyiket meg kell nevezni a szövegben)
- Az EU 20. szankciós csomagja (2026 tavasza) és 21. csomagja (2026 nyara).
- Az EU XLII. mellékletének listabővítései (például 2026-04-24, 2026-07-24).
- A dán hatósági ellenőrzések szigorítása az árnyékflotta ellen (2025-től).
- A Vörös-tenger és a Szuezi-csatorna forgalmának változása.
