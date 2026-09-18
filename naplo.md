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

## Munkamenet vége – összefoglaló

- Kész: `letoltes.py` (letöltő szkript + alapértelmezett csúcsablak és a
  javított, ténylegesen működő `http://aisdata.ais.dk` forrás, ld. a
  21:50-es és 22:05-ös bejegyzést), frissített `CLAUDE.md`, ez a
  `naplo.md`, `.gitignore` a git repóhoz, GitHub repó létrehozva és
  feltöltve (https://github.com/BallaAttila04/szakdolgozat).
- Nincs kész: a 07-15/07-16-i forgalmi hipotézis igazolása a tényleges
  letöltött adatból (a letöltés maga már működik).
- Következő lépés: `python letoltes.py --cel data` futtatása a teljes
  csúcsablakra (2026-07-15 – 2026-07-16), a kimenet bemásolása egy új
  naplóbejegyzésbe, majd a forgalmi hipotézis kiértékelése az adatból.
