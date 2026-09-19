# Szakdolgozat – projektszabályok

BSc szakdolgozat, Budapesti Corvinus Egyetem, gazdaságinformatika.
Adatelemzésre épülő munka: online forrásokból származó adat
megszerzése, feldolgozása, értelmezése.

A dolgozat szövegét a hallgató írja. Ne írj fejezeteket vagy
bekezdéseket a dolgozatba. Kódot, elemzést, vizualizációt igen.

---

## Mappaszerkezet

```
data/          letöltött nyers adat (git-ignore)
scripts/       minden futtatható szkript
outputs/       ábrák, táblázatok, köztes CSV-k
naplo.md       munkanapló  <- MINDEN LÉPÉS UTÁN FRISSÍTENDŐ
szamok.md      validált számok és honnan jöttek
```

Amíg a mappák nem jönnek létre ténylegesen, a szkriptek a gyökérben
futnak (pl. `letoltes.py`) – ez átmeneti állapot, nem a végleges
elrendezés.

---

## Adatforrás: AIS

A nyers AIS adat forrása a dán AIS-szolgáltatás publikus szervere
(az üzemeltetés a DMA-tól a Dán Katasztrófavédelmi Hatósághoz,
Beredskabsstyrelsen-hez került):

```
http://aisdata.ais.dk/aisdk-YYYY-MM-DD.zip
```

**Figyelem: `http`, nem `https`** – a szerver ezen a címen nem
szolgáltat TLS-t. Ez nem tanúsítvány-megkerülés: natívan titkosítatlan
végpontról van szó.

A korábban itt dokumentált `https://web.ais.dk/aisdata/...` cím
**halott** – lejárt (2025-06-12) és rossz domainre (`*.govcloud.dk`)
kiállított tanúsítványt ad, így minden letöltés `CERTIFICATE_VERIFY_FAILED`
hibára fut. Ne állítsd vissza. Részletes diagnózis: `naplo.md`,
2026-09-18 21:50 és 22:05.

**`letoltes.py`** – napi ZIP fájlok letöltése erről a szerverről:

```
python letoltes.py                                   # alapértelmezett: 2026-07-15 - 2026-07-16
python letoltes.py 2026-09-05                        # egy nap
python letoltes.py 2026-09-01 2026-09-07              # tartomány
python letoltes.py 2026-09-05 --cel data             # célkönyvtár
python letoltes.py 2026-09-05 --felulir              # újratöltés
```

Dátum nélkül a megbeszélt csúcsforgalmi ablakot tölti le (2026-07-15 –
2026-07-16, Kiel-csatorna tervezett teljes lezárása – ld. `naplo.md`,
2026-09-18 21:20).

Kihagyja a már meglévő, érvényes ZIP-eket; sérült vagy hiányos
letöltést CRC-ellenőrzéssel szűr ki és újrapróbál (max. 3 kísérlet).

**Élesben validálva** 2026-09-18-án a hallgató gépéről: a 2026-09-05,
2026-07-15 és 2026-07-16 napok ténylegesen letöltve (560–1036 MB/nap,
0 hiba). Ld. `naplo.md`, 22:05.

---

## A legfontosabb szabály: naplózz

Minden érdemi lépés után **fűzz hozzá** egy bejegyzést a
`naplo.md`-hez. Soha ne írd felül és ne töröld a korábbiakat.

Érdemi lépés: új szkript, adatletöltés, futtatás eredménnyel,
hiba amibe beleütköztünk, módszertani döntés, elvetett irány.

Bejegyzés formátuma:

```markdown
## 2026-09-17 14:30 – [egy mondat, mi volt a cél]

**Mit futtattam:** scripts/parositas.py --scene abc123

**Nyers kimenet:**
```
[ide a tényleges terminálkimenet, változatlanul másolva]
```

**Mit jelent:** [1-3 mondat]

**Döntés:** [ha volt; ha nem, hagyd el]

**Nyitott kérdés:** [ha van]
```

Ha valami **nem működött**, azt is naplózd. A zsákutcák a
dolgozat módszertani fejezetének anyagát adják.

---

## Számok kezelése

Minden szám, ami bekerül a `szamok.md`-be, kapjon forrást:
melyik szkript, milyen paraméterrel, mikor futott.

```markdown
| szám | jelentés | szkript | dátum |
|------|----------|---------|-------|
| 2267 | hajódetektálás szűrés után | scripts/szures.py | 2026-09-16 |
```

Ha egy szám megváltozik, ne írd felül: húzd át és írd mellé az
újat az indoklással. A dolgozatban meg kell tudni védeni, miért
az a szám szerepel, ami.

---

## Validálás

- Kódot futtass le, mielőtt azt mondod, hogy működik. A tényleges
  kimenetet mutasd, ne azt, aminek lennie kellene.
- Számot az adatból számolj, ne becsülj.
- Adatforrást, linket, könyvtárat ellenőrizz, mielőtt ajánlod.
- Ha valamit nem tudtál ellenőrizni, írd le, hogy nem ellenőrizted.
- Ha korábbi állítás tévesnek bizonyul, javítsd ki a naplóban is.

---

## Szkriptekkel szemben

- Minden szkript fusson önmagában, parancssorból.
- Fájlútvonalak ne legyenek bedrótozva; paraméterként jöjjenek.
- A szűrési küszöböket a fájl tetején, elnevezett konstansként
  tartsd, kommenttel arról, miért az az érték.
- Nagy fájlt chunkolva olvass.
- Minden szkript írjon ki egy rövid összefoglalót arról, hány sort
  dolgozott fel és mennyi maradt szűrés után.

---

## Munkamenet vége

Session végén írj a `naplo.md` végére egy 3-5 soros összefoglalót:
mi lett kész, mi nem, mi a következő lépés. Ez az, amit a
hallgató átvisz a chat-felületre.
