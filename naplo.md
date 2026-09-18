# Munkanapló

---

## 2026-09-18 21:05 – `letoltes.py` és `CLAUDE.md` létrehozása a gyökérben

**Mit futtattam:** `python letoltes.py 2026-09-05 --cel /tmp/ais_test_dl` (Claude
oldali felhő-munkakörnyezetből, éles cél: `web.ais.dk`)

**Nyers kimenet:**
```
Letoltendo napok: 1 (2026-09-05 - 2026-09-05)
Celkonyvtar: /tmp/ais_test_dl

  aisdk-2026-09-05.zip: hiba a(z) 1. kiserletnel: HTTPSConnectionPool(host='web.ais.dk', port=443):
  Max retries exceeded with url: /aisdata/aisdk-2026-09-05.zip
  (Caused by ProxyError('Unable to connect to proxy', OSError('Tunnel connection failed: 403 Forbidden')))
  [... 2 további kísérlet, ugyanaz a hiba ...]
  aisdk-2026-09-05.zip: nem sikerult 3 kiserlet utan sem

Osszesites: 0 uj letoltes, 0 mar megvolt, 1 hiba (1 nap osszesen)
```

**Mit jelent:** A Claude felhős munkakörnyezetének hálózati kimenete nincs
engedélyezve a `web.ais.dk` domainre (proxy 403), ezért az éles letöltés innen
nem tesztelhető. Emiatt a letöltő/ellenőrző/hibakezelő logikát helyi HTTP
szerverrel, valódi ZIP fájllal validáltam:

```
127.0.0.1 - - "GET /aisdk-2026-09-05.zip HTTP/1.1" 200 -
  aisdk-2026-09-05.zip: kesz (0.0 MB)
eredmeny: kesz
letezik: True
ervenyes zip: True
  aisdk-2026-09-05.zip: mar megvan, ervenyes ZIP - kihagyva
masodik eredmeny: mar_megvan
127.0.0.1 - - code 404, message File not found
  aisdk-2099-01-01.zip: 404 - ehhez a naphoz nincs adat a szerveren
404 eredmeny: hiba
```

Mindhárom eset (sikeres letöltés + ZIP-ellenőrzés, "már megvan" kihagyás,
404-es hiányzó nap) hibátlanul lefutott.

Az URL-mintázatot (`https://web.ais.dk/aisdata/aisdk-YYYY-MM-DD.zip`)
független forrásból igazoltam: a PyMEOS dokumentáció AIS példája pontosan
ezt a mintát használja (`aisdk-2023-08-01.zip`) –
https://pymeos.readthedocs.io/en/develop/src/examples/AIS.html. A kézzel
letöltött `aisdk-2026-09-05.zip` fájlnév is ezzel egyezik.

**Döntés:** `letoltes.py` és a frissített `CLAUDE.md` a mappa gyökerébe
kerül (nem `scripts/` alá), mert a `data/`/`scripts/`/`outputs/`
mappaszerkezet még nincs ténylegesen létrehozva – ez átmeneti állapot.

**Nyitott kérdés:** Az éles letöltést (valódi `web.ais.dk` szerverrel) a
Claude felhős környezetéből nem lehet elvégezni (proxy blokkolja), a helyi
gépről irányított futtatás (`device_bash`) pedig jelenleg egy 2026.09.08-i
Windows-frissítés miatt nem éri el a mappát Claude oldaláról. Az első éles
`letoltes.py` futtatást a hallgatónak kell elindítania a saját gépén (vagy
később, ha a device_bash-hozzáférés helyreáll), és az eredményt ide,
a naplóba bemásolni.

---

## 2026-09-18 21:20 – Melyik napokra töltsünk le AIS adatot: forgalmi csúcs keresése

**Mit jelent:** A cél egy olyan 1–2 napos ablak, amikor a dán szorosokban
(Great Belt / Fehmarnbelt / nyugati Balti-tenger – a `letoltes.py`/
`ais_teszt.py` bounding boxa: 54.5–56.5°N, 10.0–13.0°E) a szokásosnál
nagyobb volt a hajóforgalom, hogy a letöltött adat érdemi elemzési anyagot
adjon (csúcsterhelés, torlódás, útvonal-eltérülés).

Megvizsgált lehetőségek és miért esett/nem esett rájuk a választás:

- **Balti-tengeri kábelrongálási esetek (2024–2025), NATO "Baltic Sentry"
  művelet** – megnövelt haditengerészeti/parti őrségi jelenlét a Balti-
  tengeren általában, de a konkrét események (pl. Eagle S, Newnew Polar
  Bear) főként a Finn-öbölben és a keleti Balti-tengeren történtek, nem a
  bounding boxban lévő dán szorosokban – elvetve.
  (https://en.wikipedia.org/wiki/2024_Baltic_Sea_submarine_cable_disruptions,
  https://www.cnn.com/2025/01/27/europe/nato-defense-baltic-undersea-cables-intl-cmd/index.html)

- **Kiel-csatorna tervezett teljes lezárásai, 2026 július** – ez illeszkedik
  a bounding boxra: a Kiel-csatorna (Brunsbüttel–Kiel) az Északi- és a
  Balti-tenger közti fő alternatív útvonal a dán szorosokhoz képest; amikor
  lezár, a hajók kénytelenek megkerülni Dánián keresztül (Great Belt vagy
  Öresund), ami pontosan a vizsgált területen okoz többletforgalmat. Ez már
  2013-ban is dokumentált hatás volt ("all traffic went via Denmark" egy
  korábbi teljes lezáráskor – https://theloadstar.com/congestion-plague-kiel-canal-another-seven-years/).
  A 2026-os menetrend szerint két teljes lezárás volt:
  - **2026.07.14., 07:00–16:00** (Rendsburg, ~9 óra)
  - **2026.07.15. 17:00 – 2026.07.16. 09:00** (Rader Hochbrücke, ~16 óra,
    ez a hosszabb és valószínűleg nagyobb hatású)
  Forrás: https://www.yacht.de/en/travel-and-charter/germany/the-kiel-canal-two-complete-closures-in-july/

**Döntés:** Az első letöltendő adatablak: **2026-07-15 és 2026-07-16**
(2 nap), a hosszabb (16 órás) csatornalezárás napjai – ez az az esemény,
ahol a legvalószínűbb, hogy a dán szorosokban mérhetően megnőtt a
forgalom a Kiel-csatorna felől átterelt hajók miatt.
Parancs: `python letoltes.py 2026-07-15 2026-07-16 --cel data`
Összehasonlításként érdemes lehet egy "átlagos" napot is letölteni
(pl. a már meglévő 2026-09-05), hogy legyen viszonyítási alap a
forgalom-számhoz.

**Nyitott kérdés:** A forgalomnövekedés (hajószám, üzenetszám) csak az
adat tényleges letöltése és kiértékelése után igazolható – ez egy
**hipotézis a dátumválasztás indoklására**, nem validált tény. Ha a
letöltött adat nem mutat kimutatható eltérést az átlagos naphoz képest, ezt
itt kell rögzíteni és más dátumot kell keresni (pl. a 07-14-i rövidebb
lezárás, vagy egy másik gazdasági esemény).

**Nyitott kérdés (GitHub):** Felmerült, hogy a projektet git/GitHub
repóban érdemes-e vezetni. Döntés: igen, publikus repó (ld. lentebb).

---

## 2026-09-18 21:35 – `letoltes.py` frissítve: alapértelmezett csúcsablak

**Mit jelent:** A dátum argumentumok mostantól opcionálisak. Ha a szkriptet
dátum nélkül futtatjuk (`python letoltes.py`), automatikusan a 2026-09-18
21:20-as bejegyzésben eldöntött csúcsforgalmi ablakot tölti le
(`ALAP_KEZDO_DATUM = 2026-07-15`, `ALAP_VEG_DATUM = 2026-07-16`, a fájl
tetején elnevezett konstansként, a döntés forrására mutató kommenttel). Az
explicit dátum megadás (egy nap vagy tartomány) továbbra is felülírja ezt.

**Mit futtattam:** helyi mock HTTP szerverrel, `python letoltes.py --cel
<ideiglenes mappa>` (dátum nélkül), hogy az alapértelmezett ág is
lefusson.

**Nyers kimenet:**
```
Nincs datum megadva - alapertelmezett csucsforgalmi ablak: 2026-07-15 - 2026-07-16
(Kiel-csatorna lezaras, ld. naplo.md).

Letoltendo napok: 2 (2026-07-15 - 2026-07-16)
Celkonyvtar: /tmp/ais_test_default

  aisdk-2026-07-15.zip: kesz (0.0 MB)
  aisdk-2026-07-16.zip: kesz (0.0 MB)

Osszesites: 2 uj letoltes, 0 mar megvolt, 0 hiba (2 nap osszesen)
```

**Döntés:** `CLAUDE.md` frissítve az új alapértelmezett használati móddal.

---

## 2026-09-18 21:40 – Git/GitHub repó létrehozása

**Döntés:** A projekt publikus GitHub repóban lesz verziózva. `data/`
mappa `.gitignore`-olva (nyers ZIP-ek 100+ MB, nem valók git-be).

**Nyitott kérdés:** A repó tényleges létrehozása és az első push a
hallgató saját gépén/böngészőjében történik (a Claude felhős
munkakörnyezete nem fér hozzá a GitHub fiókhoz) – a pontos lépések a
chat-felületen.

---

## 2026-09-18 21:50 – Éles letöltés a saját gépről: miért failel a `letoltes.py`

**Mit futtattam:** `python letoltes.py 2026-09-05 --cel /tmp/ais_test_real`
(most már a hallgató saját gépéről, nem a Claude felhős munkakörnyezetéből –
tehát a korábbi proxy-403 gyanú kizárva).

**Nyers kimenet:**
```
aisdk-2026-09-05.zip: hiba a(z) 1. kiserletnel: HTTPSConnectionPool(host='web.ais.dk', port=443):
Max retries exceeded with url: /aisdata/aisdk-2026-09-05.zip
(Caused by SSLError(SSLCertVerificationError(1, "[SSL: CERTIFICATE_VERIFY_FAILED]
certificate verify failed: Hostname mismatch, certificate is not valid for
'web.ais.dk'. (_ssl.c:1020)")))
[... 2 tovabbi kiserlet, ugyanaz a hiba ...]
aisdk-2026-09-05.zip: nem sikerult 3 kiserlet utan sem

Osszesites: 0 uj letoltes, 0 mar megvolt, 1 hiba (1 nap osszesen)
```

**Diagnózis:** A hiba nem hálózati/proxy eredetű, hanem a `web.ais.dk`
szerver TLS-tanúsítványa a valódi ok. `openssl s_client`-tel közvetlenül
lekérdezve a `185.153.153.66`-on futó szerver tanúsítványát:

```
subject=CN=*.govcloud.dk
issuer=C=GB, ST=Greater Manchester, L=Salford, O=Sectigo Limited,
       CN=Sectigo RSA Domain Validation Secure Server CA
notBefore=Jun 12 00:00:00 2024 GMT
notAfter=Jun 12 23:59:59 2025 GMT
Subject Alternative Name: DNS:*.govcloud.dk, DNS:*.govcloud.faellesweb.dk,
                           DNS:govcloud.dk, DNS:govcloud.faellesweb.dk
```

Két külön probléma egyszerre:
1. **Rossz domain a tanúsítványon** – a `web.ais.dk`-ra kiszolgált
   tanúsítvány a `*.govcloud.dk`-ra (és rokon domainjeire) van kiállítva,
   nem `web.ais.dk`/`*.ais.dk`-ra. A `185.153.153.66` IP-n láthatóan egy
   megosztott/más célra használt szerver fut, aminek nincs érvényes,
   `web.ais.dk`-ra szóló tanúsítványa.
2. **Lejárt tanúsítvány** – a bemutatott tanúsítvány érvényessége
   2025-06-12-én lejárt, azaz több mint egy éve érvénytelen (a mai dátum
   2026-09-18).

`curl`/Windows schannel más hibaüzenetet ad ugyanerre
(`SEC_E_CERT_EXPIRED`), mert a schannel elsőként a lejáratot ellenőrzi,
míg Python `ssl`/OpenSSL a hostname-egyezést jelzi elsőként – de a
gyökérok ugyanaz: a szerver oldali tanúsítvány érvénytelen.

**Mit jelent:** A `letoltes.py` retry/hibakezelő logikája helyesen
működik (3 kísérlet, egyértelmű hibaüzenet, `hiba` állapot, nem-nulla
kilépési kód) – ez **nem kódhiba**, hanem a DMA (vagy az azt kiszolgáló
harmadik fél) szerverének infrastrukturális problémája. TLS-ellenőrzés
kikapcsolása (`verify=False`) **nem** javasolt megoldás, mert a
tanúsítvány szerint a kapcsolat egy teljesen más domainhez
(`govcloud.dk`) tartozó szerverhez megy – ez akár DNS-hibát, akár rosszul
konfigurált/megosztott hosztolást, akár (elvi lehetőségként) man-in-the-
middle helyzetet is jelenthet, és éles adatletöltés esetén nem lehet
vakon megbízni benne.

**Döntés:** A `letoltes.py`-t egyelőre nem módosítjuk a tanúsítvány-
ellenőrzés megkerülésére. A éles letöltés blokkolva marad, amíg a
domain/tanúsítvány állapota nem tisztázódik.

**Nyitott kérdés:** Ellenőrizni kell, hogy a `web.ais.dk` a DMA jelenlegi
hivatalos AIS-adat domainje-e (lehet, hogy a DMA időközben átköltöztette
az adatokat egy másik domainre/URL-re, és a `web.ais.dk` DNS-bejegyzése
mára egy más célra használt szerverre mutat). Ezt a DMA hivatalos
oldalán (dma.dk) vagy a PyMEOS/más friss dokumentáción kell utánanézni,
mielőtt bármilyen megkerülő megoldást (pl. új URL, kézi tanúsítvány-
pinning) bevezetnénk.

---

## 2026-09-18 22:05 – Helyes URL megtalálva: `aisdata.ais.dk` (HTTP, nem HTTPS)

**Mit jelent:** A hallgató a saját böngészőjében ellenőrizte a domaint, és
kiderült, hogy az AIS-adatok üzemeltetése időközben átkerült a Dán
Katasztrófavédelmi Hatósághoz (Beredskabsstyrelsen). A korábban használt
`https://web.ais.dk/aisdata/...` cím a fenti (rossz domainre kiállított,
lejárt) tanúsítvány miatt nem használható. A böngészős valódi könyvtár-
listázás (több hónapnyi napi ZIP fájllal) alapján a jelenleg élő,
helyes cím:

```
http://aisdata.ais.dk/aisdk-YYYY-MM-DD.zip
peldaul: http://aisdata.ais.dk/aisdk-2026-09-05.zip
```

Fontos: ez a cím **HTTP-n** szolgál, nem HTTPS-en – a szerver ezen a
címen nem is kínál TLS-t, tehát ez nem megkerülés/tanúsítvány-figyelmen
kívül hagyás, hanem a szerver által ténylegesen kiszolgált, natívan
titkosítatlan végpont.

**Mit futtattam:** `letoltes.py`-ban a `BASE_URL` átírva
`https://web.ais.dk/aisdata`-ról `http://aisdata.ais.dk`-ra, majd
`python letoltes.py 2026-09-05 --cel /tmp/ais_test_http` a saját gépről.

**Nyers kimenet:**
```
Letoltendo napok: 1 (2026-09-05 - 2026-09-05)
Celkonyvtar: C:\Users\Hp\AppData\Local\Temp\ais_test_http

  aisdk-2026-09-05.zip: kesz (560.6 MB)

Osszesites: 1 uj letoltes, 0 mar megvolt, 0 hiba (1 nap osszesen)
```

**Döntés:** Az éles letöltés a `http://aisdata.ais.dk` címmel működik,
a blokkolás (ld. 21:50-es bejegyzés) feloldva. A `letoltes.py` fejléc-
kommentje frissítve az új forrásra és a döntés indoklására mutató
hivatkozással.

**Nyitott kérdés:** A HTTP (titkosítatlan) átvitel azt jelenti, hogy a
letöltött adat integritása kizárólag a szkript ZIP-CRC ellenőrzésén
(`ellenoriz_zip`) múlik, aktív hálózati manipuláció ellen nincs
védelem. Nagyobb (több napos/hetes) letöltés előtt érdemes megfontolni
egy checksum-forrás (ha a DMA/Beredskabsstyrelsen közöl ilyet) hozzáadását.

---

## 2026-09-18 22:10 – Forgalmi kiértékelés: csúcsnapok vs átlagos nap

**Mit futtattam:** Új szkript, `forgalom_elemzes.py` – a bounding boxban
(54.5–56.5°N, 10.0–13.0°E) óránkénti egyedi hajószámot (MMSI) és
üzenetszámot számol napi AIS ZIP-ekből (streamelt olvasással, `zf.open()`,
nem `zf.read()`, hogy az 1 GB-os fájlok ne fussanak ki a memóriából).

```
python forgalom_elemzes.py --csucs data/aisdk-2026-07-15.zip data/aisdk-2026-07-16.zip --atlag aisdk-2026-09-05.zip
```

**Eredmény (napi összesítés, `forgalmi_osszefoglalo.csv`):**

| dátum | típus | napi üzenet | csúcsóra | csúcsórai hajószám | átlagos órai hajószám |
|---|---|---|---|---|---|
| 2026-07-15 | csúcs | 10 860 221 | 09:00 | 2971 | 2275.5 |
| 2026-07-16 | csúcs | 10 968 080 | 09:00 | 2943 | 2245.8 |
| 2026-09-05 | átlag | 6 030 204 | 10:00 | 1261 | 1144.5 |

Óránkénti bontás: `forgalmi_profil_oranankent.csv`, ábra: `forgalmi_profil.png`.

Mindkét csúcsnapon (07-15, 07-16) az átlagos órai hajószám kb. **2×** akkora,
mint a 09-05-i referencianapon (2275/2246 vs 1145), a csúcsórai (09:00)
egyedi hajószám pedig kb. **2,3–2,4×** (2971/2943 vs 1261). A napi
üzenetszám is kb. **1,8×** magasabb.

**Fontos módszertani probléma – a hipotézis még NEM tekinthető
igazoltnak:** Az ábrán (`forgalmi_profil.png`) a 07-15 és 07-16 görbéje
gyakorlatilag egybeesik, és a 09-05-i görbétől **a nap MINDEN órájában**
nagyjából arányosan (kb. azonos szorzóval) magasabb – beleértve az
éjszakai órákat is, amikor a Kiel-csatorna még nem is volt lezárva (a
lezárás csak 07-15 17:00 – 07-16 09:00 között volt). Ha a többletforgalom
kifejezetten a csatornalezárás miatti átterelés lenne, azt várnánk, hogy
a különbség konkrétan a lezárási ablakban ugrik meg, nem pedig egyenletes
szorzóként jelentkezik a teljes napon át.

Ennek jóval valószínűbb magyarázata: **szezonalitás** – július (nyári
turista-/vitorlás-szezon, hosszabb nappalok, több komp-/kedvtelési célú
hajóforgalom) és szeptember eleje eleve nem összehasonlítható bázis, a
mért különbség nagy része feltehetően ennek tudható be, nem a
csatornalezárásnak.

**Döntés:** A Kiel-csatorna-hipotézist egyelőre **nem tekintjük
igazoltnak**. A jelenlegi adatokból csak annyi állítható biztosan, hogy
a dán szorosokban 2026-07-15/16-án kb. kétszer annyi hajó volt látható
óránként, mint 2026-09-05-én – az ok (szezonalitás vs csatornalezárás)
szétválasztása további adatot igényel.

**Nyitott kérdés / következő lépés:** Kontrollnapra van szükség: egy
**másik júliusi nap, amikor a Kiel-csatorna NEM volt lezárva** (pl. egy
"átlagos" 2026 júliusi hétköznap, lehetőleg azonos hét napja, mint 07-15
[szerda] vagy 07-16 [csütörtök], hogy a hét napja szerinti hatás is ki
legyen szűrve). Ha ezen a kontrollnapon a forgalom közelebb van a 09-05-i
szinthez, mint a csúcsnapokhoz, az a szezonalitást erősíti. Ha a
kontrollnap is magasan van, de a csúcsnapok MÉG magasabbak (főleg a
lezárási ablakban), az a csatornalezárás hatását igazolja. Emellett érdemes
lenne a 07-14-i (rövidebb, 9 órás) lezárás napját is letölteni
összehasonlításként.

---

## Munkamenet vége – összefoglaló

- Kész: `letoltes.py` (letöltő szkript + alapértelmezett csúcsablak és a
  javított, ténylegesen működő `http://aisdata.ais.dk` forrás, ld. a
  21:50-es és 22:05-ös bejegyzést), frissített `CLAUDE.md`, ez a
  `naplo.md`, `.gitignore` a git repóhoz, GitHub repó létrehozva és
  feltöltve (https://github.com/BallaAttila04/szakdolgozat), a
  07-15/07-16 csúcsnapok és a 09-05-i referencianap ténylegesen
  letöltve, `forgalom_elemzes.py` az óránkénti forgalmi kiértékeléshez.
- Nincs kész: a Kiel-csatorna-hipotézis **nincs igazolva** – a mért
  ~2×-es forgalomnövekedés (ld. 22:10-es bejegyzés) valószínűleg
  keveredik a nyár/ősz szezonalitással; kontroll júliusi nap (lezárás
  nélküli) letöltése és összevetése szükséges a szétválasztáshoz.
- Következő lépés: egy kontroll júliusi (lehetőleg lezárás nélküli,
  azonos hét napjára eső) nap letöltése és bevonása a
  `forgalom_elemzes.py` futtatásába, hogy a szezonalitás és a
  csatornalezárás hatása szétválasztható legyen.

---

## 2026-09-18 22:35 – Konzulenssel megbeszélt tárolási irány pótlólag naplózva

**Mit jelent:** Egy másik (böngészős) Cowork-beszélgetésben a hallgató a
konzulenssel (2026-09-17-i konzultáció) megbeszélt konkrét
tárolási/feldolgozási irányt is átbeszélte, de ez eddig **csak abban a
beszélgetésben** volt meg, sem ide (`naplo.md`), sem `CLAUDE.md`-be nem
került be – a beszélgetések között nincs automatikus adatmegosztás. A
hallgató az `atadas_cowork.md` fájlban (a mappa gyökerében) hozta át a
tartalmát, innen pótolva:

**A konzulens által jóváhagyott új irány (2026-09-17):** a cím szabadon
módosítható, a SAR-rész elejthető (az xView3-SAR adathalmaz 2020-as és
nincs balti/szoros jelenet benne – ez korábban külön megvalósíthatósági
teszttel is alátámasztva: 10 dán jelenet, 4585 detektálás, 2304 nem hajó,
a maradék 2267 hajóból 46% AIS nélküli). Az **új hangsúly a nagy AIS-
adathalmaz modern tárolási/feldolgozási módszereinek vizsgálatán van**,
konkrétan felmerült megoldások:

- **CSV → Parquet és/vagy DuckDB** – oszlopos tárolás, gyorsabb
  lekérdezés, kisebb méret a nyers CSV-hez képest.
- **H3 térbeli index** – esetlegesen, térbeli lekérdezések
  gyorsítására/particionálására.
- **Spark** – esetlegesen, ha az adat mérete miatt egy gépen nem
  kezelhető hatékonyan (a konzulens ezt inkább példaként, nem
  kőbe vésett elvárásként említette).

Tervezett mérési irány: CSV vs. Parquet vs. DuckDB összehasonlítása
**méretben, beolvasási időben és lekérdezési időben** – ez lenne a
dolgozat első mérhető, számszerű eredménye.

**Nyitott kérdés (a hallgatótól átvéve, nem lezárt):**
- A konzulens jegyzetében szereplő "geopods" szó tisztázatlan –
  valószínűleg GeoPandas vagy GeoParquet, de ezt még nem erősítették meg
  vele.
- Nem tisztázott, hogy a Spark-ot ténylegesen elvárja-e a konzulens, vagy
  csak illusztrációként hangzott el.
- A pontos szakdolgozat-cím még nincs véglegesítve, csak az irány (AIS
  nagy adat tárolás/feldolgozás modernizálása) áll.

**Megjegyzés az `atadas_cowork.md` és a tényleges állapot közti
eltérésről:** az a fájl a `letoltes.py`-t még egy korábbi tervként írja
le (S3-tükör elsődleges forrás + `web.ais.dk` tartalék, `.part` fájl,
magic-byte+méret ellenőrzés) – ez **nem egyezik** a jelenleg a mappában
lévő, ténylegesen működő verzióval (`http://aisdata.ais.dk` egyetlen
forrás, ZIP-CRC ellenőrzés, ld. 21:35/22:05-ös bejegyzés). A ténylegesen
futó, validált kód a mérvadó, nem az átadó dokumentum korábbi leírása –
de érdemes tudni, hogy legalább két külön munkamenet (ez a Cowork-chat és
egy VS Code/Claude Code munkamenet) is dolgozott/dolgozik ugyanezen a
mappán, így a `naplo.md` rendszeres, gyors frissítése (mindkét oldalról)
különösen fontos az ütközések elkerüléséhez.

**Döntés:** A fenti tárolási irány mostantól itt, a `naplo.md`-ben is
szerepel, hogy bármelyik beszélgetésből/munkamenetből elérhető legyen.

---

## 2026-09-18 22:47 – Tárolási benchmark lefuttatva: CSV vs Parquet vs DuckDB

**Mit futtattam:**
```
pip install duckdb          # duckdb-1.5.5
python -u tarolas_benchmark.py data/aisdk-2026-07-15.zip data/aisdk-2026-07-16.zip
```

**Első futás elszállt – bug a szkriptben (javítva):**
```
_duckdb.BinderException: Binder Error: No function matches the given name and
argument types 'strptime(TIMESTAMP, STRING_LITERAL)'.
```
Ok: a DuckDB `read_csv_auto` a `# Timestamp` oszlopot **már TIMESTAMP
típusúra** konvertálja beolvasáskor, a lekérdezés viszont `strptime()`-ot
hívott rá, ami VARCHAR bemenetet vár. (A pandas-ág addigra hibátlanul
lefutott, a hiba a DuckDB rész 4. lekérdezésénél jött.)

Javítás: új `ora_kifejezes()` segédfüggvény, ami `typeof()`-fal megnézi az
oszlop tényleges típusát, és TIMESTAMP-nál `date_part('hour', ...)`-ot
használ, szöveges oszlopnál marad a `strptime`. Füstteszttel (200 000 soros
minta) validálva, mielőtt a teljes 12 GB-os futás újraindult.

**Méret (a lényeg):**

| formátum | 2026-07-15 | 2026-07-16 | arány a CSV-hez |
|---|---|---|---|
| CSV (nyers, kicsomagolt) | 6248.0 MB | 6137.7 MB | 100% |
| Parquet | 1061.2 MB | 1059.5 MB | **~17%** |
| DuckDB natív tábla | 1537.3 MB | 1507.8 MB | **~25%** |

**Lekérdezési idő (mind a négy lekérdezés együtt, másodperc):**

| motor | 2026-07-15 | 2026-07-16 | gyorsulás a pandas-hoz |
|---|---|---|---|
| pandas_csv (egy chunkolt menet) | 151.4 | 141.2 | 1× |
| duckdb_csv (4 külön lekérdezés) | 56.2 | 60.9 | ~2,5× |
| duckdb_parquet | 3.10 | 1.64 | ~49–86× |
| duckdb_tabla | 0.99 | 1.05 | ~134–153× |

**Egyszeri konverziós költség:**

| művelet | 2026-07-15 | 2026-07-16 |
|---|---|---|
| CSV → Parquet | 66.2 mp | 54.4 mp |
| CSV → DuckDB natív tábla | 114.1 mp | 124.2 mp |

Részletes soronkénti mérés: `tarolas_benchmark.csv`, nyers futási napló:
`tarolas_benchmark.log`.

**Mit jelent:**
1. **A Parquet a legkompaktabb** (~17% a CSV-nek, tehát kb. 6-szoros
   helymegtakarítás), a DuckDB natív tábla valamivel nagyobb (~25%), de
   cserébe a leggyorsabb lekérdezés.
2. **A konverzió egyetlen lekérdezési menet alatt megtérül:** a
   CSV→Parquet konverzió 54–66 mp, ami kevesebb, mint egyetlen pandas
   végigolvasás (141–151 mp). Tehát már az első elemzésnél nyerünk vele,
   és onnantól minden további lekérdezés ~50–150× gyorsabb.
3. A nyers CSV-n futtatott DuckDB is gyorsabb a pandas-nál (~2,5×), de a
   nagyságrendi különbséget az oszlopos tárolás (Parquet / natív tábla)
   adja, nem önmagában a motor.

**Keresztvalidáció (fontos, mert két független implementáció):** a
benchmark DuckDB-eredményei **pontosan egyeznek** a `forgalom_elemzes.py`
(pandas, chunkolt) korábbi számaival – bounding box találat 10 860 221
(07-15) és 10 968 080 (07-16), a csúcsóra mindkét napon 09:00, 2971 ill.
2943 egyedi hajóval. Két teljesen külön kódúton (pandas chunk vs SQL)
azonos eredmény jött ki, ez erős megerősítés a 22:10-es kiértékelés
számaira.

**Nyitott kérdés / a mérés korlátai:**
- **Egyetlen futás, ismétlés nélkül**, és az operációs rendszer
  fájl-cache-e nincs kontrollálva. Ez látszik is az adatokon: ugyanaz a
  Parquet-lekérdezéscsomag 3.10 mp (07-15) vs 1.64 mp (07-16) – közel
  2× szórás azonos munkára. A nagyságrendi következtetéseket ez nem
  érinti, de **publikálható számokhoz ismételt mérés kell** (pl. 3–5
  futás, hideg/meleg cache külön jelölve).
- A pandas-ág az **összes oszlopot** beolvassa, a Parquet/tábla motorok
  csak a lekérdezéshez kellőket – ez pont az oszlopos tárolás lényege,
  tehát jogos összehasonlítás, de a dolgozatban explicit ki kell mondani,
  nem szabad elhallgatni.
- **H3 térbeli index és Spark még nincs mérve** – a 22:35-ös bejegyzésben
  szereplő három irányból csak az első (Parquet/DuckDB) van kész.
- **DuckDB dátum-felismerés csapdája:** a `read_csv_auto` ezen a fájlon
  helyesen ismerte fel a nap/hónap sorrendet (15/07/2026 → július 15.),
  mert a 15-ös nap egyértelművé teszi. Olyan napnál viszont, ahol a nap
  ≤ 12 (pl. `aisdk-2026-09-05` → "05/09/2026"), a sniffer akár
  hónap/napként is értelmezhetné. Az **órastatisztikát ez nem rontaná el**
  (az óra rész egyértelmű), de dátum-szintű elemzésnél csendes hibaforrás
  – több napos összefűzésnél explicit `dateformat`-ot kell megadni.

**Lemezhasználat figyelmeztetés:** a `bench_workdir` a futás után **18 GB**
(2 kicsomagolt CSV + 2 Parquet + 2 .duckdb), a lemez 96%-on áll, 24 GB
szabad. A könyvtár teljes tartalma bármikor újragenerálható a ZIP-ekből,
tehát törölhető – és `.gitignore`-ba is fel kell venni.
