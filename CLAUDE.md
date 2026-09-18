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

A nyers AIS adat forrása a Dán Tengerészeti Hatóság (DMA) publikus
szervere:

```
https://web.ais.dk/aisdata/aisdk-YYYY-MM-DD.zip
```

Ellenőrizve 2026-09-18-án (független forrás: PyMEOS dokumentáció
példája, `aisdk-2023-08-01.zip`), mert a `web.ais.dk` domain közvetlen
lekérése ebben a munkakörnyezetben robots.txt-hibával elutasításra
került. A kézzel letöltött `aisdk-2026-09-05.zip` fájlnév megegyezik
ezzel a mintázattal.

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
A tényleges hálózati letöltés ebből a munkakörnyezetből nem volt
tesztelhető (a `web.ais.dk` cél nincs az egress-listán) – a
letöltő/ellenőrző/hibakezelő logika helyi HTTP szerverrel, valódi ZIP
fájllal validálva (sikeres letöltés, már-megvan eset, 404 eset mind
lefutott). Első éles futtatáskor a kimenetet naplózni kell a
`naplo.md`-ben.

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
