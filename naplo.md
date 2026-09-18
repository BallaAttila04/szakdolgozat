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

## Munkamenet vége – összefoglaló

- Kész: `letoltes.py` (letöltő szkript + alapértelmezett csúcsablak,
  validálva mock szerverrel), frissített `CLAUDE.md`, ez a `naplo.md`,
  `.gitignore` a git repóhoz.
- Nincs kész: éles adatletöltés (hálózati korlátozás miatt a hallgatónak
  kell futtatnia), a 07-15/07-16-i forgalmi hipotézis igazolása az adatból,
  a GitHub repó tényleges létrehozása és feltöltése.
- Következő lépés: repó létrehozása github.com-on + `git init`/push a
  saját gépen (lépések a chatben), majd `python letoltes.py --cel data`
  futtatása és a kimenet bemásolása egy új naplóbejegyzésbe.
