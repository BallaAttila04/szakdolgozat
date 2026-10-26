# Dán szorosok monitor – adat-feed

A napi forgalmi monitor gépi felülete. A fájlok a napi futással együtt frissülnek
(GitHub Actions → GitHub Pages), és változatlan URL-en érhetők el.

- Kódolás: UTF-8; CSV: vesszővel tagolt, fejléccel, tizedesjel: pont.
- Dátum: ÉÉÉÉ-HH-NN (a napi AIS-fájl napja, UTC).
- Üres mező: nincs érték (pl. nincs alapszint).
- A szerkezet verziója: 1 (a `katalogus.json` és a `legutobbi.json` `sema_verzio` mezője). Visszafelé nem kompatibilis változásnál nő.
- A `katalogus.json` minden fájl méretét, sorszámát és SHA-256 ujjlenyomatát tartalmazza.

## Fájlok

| fájl | leírás | méret | sorok |
|---|---|---|---|
| `legutobbi.json` | Az utolsó feldolgozott nap: sorozatonként érték, alapszint, eltérés, küszöb, jelzés; aktív jelzések; az utolsó futás állapota. | 4,3 KB | – |
| `jelzesek.csv` | A monitor összes jelzés-sora (forgalom és megrakottság). | 64,0 KB | 852 |
| `idosor_forgalom.csv` | Napi kapuvonal-átkelések kapu, irány és hajócsoport szerint. | 144,6 KB | 3318 |
| `idosor_megrakottsag.csv` | Napi megrakottsági tábla (tanker, teherhajó). | 68,7 KB | 1159 |
| `kiserleti_kapuk_napi.csv` | A kísérleti kapuk napi kereskedelmi (teher + tanker) átkelései – kísérleti, nem a monitor része. | 60,6 KB | 1742 |
| `backtest.json` | A jelzési szabály backtestjének összefoglalója (pillanatkép). | 186,7 KB | – |
| `kiserleti_kapuk.json` | A kísérleti kapuk blokkja: sorozatok, statisztika, PortWatch-összevetés (pillanatkép). | 43,4 KB | – |

## `jelzesek.csv`

| oszlop | jelentés |
|---|---|
| `datum` | nap (ÉÉÉÉ-HH-NN, UTC) |
| `tipus` | forgalom | megrakottsag |
| `sorozat` | a sorozat neve |
| `ertek` | a nap értéke (átkelés; a 7 napos sorozatoknál gördülő összeg) |
| `alapnapok` | az alapszinthez talált korábbi azonos hétnapok száma (0–4) |
| `alapszint` | az előző 4 hét azonos napjainak mediánja (üres: kevesebb mint 3 nap) |
| `elteres` | ertek / alapszint − 1 |
| `kuszob` | a sorozat jelzési küszöbe (relatív) |
| `jelzes` | normál | szokatlanul magas | szokatlanul alacsony | nincs alapszint |

## `idosor_forgalom.csv`

| oszlop | jelentés |
|---|---|
| `datum` | nap |
| `kapu` | Nagy-Balti-öv | Øresund |
| `irany` | átkelési irány |
| `csoport` | hajócsoport (AIS Ship type alapján) |
| `atkeles` | átkelések száma |

## `idosor_megrakottsag.csv`

| oszlop | jelentés |
|---|---|
| `datum` | nap |
| `kapu` | kapu |
| `irany` | irány |
| `csoport` | Tanker | Teherhajó |
| `atkeles` | átkelés |
| `ertekelheto` | értékelhető merülésű átkelés |
| `megrakott` | megrakottnak minősített átkelés |
| `volumenindex` | Σ hossz × szélesség × merülés (m³) |
| `megrakott_arany` | megrakott / értékelhető |

## `kiserleti_kapuk_napi.csv`

| oszlop | jelentés |
|---|---|
| `datum` | nap |
| `kapu` | kapu |
| `irany` | irány |
| `kereskedelmi_atkeles` | teherhajó + tanker átkelés |
| `kiserleti` | 1 = kísérleti kapu, 0 = monitor-kapu |

## `legutobbi.json`

| mező | jelentés |
|---|---|
| `utolso_nap` | az utolsó feldolgozott nap |
| `frissitve_utc` | a monitor utolsó számolása |
| `utolso_futas` | a napi futás állapota: `statusz` (ok / reszleges / hiba), `uzenet`, `ido_utc` |
| `szabaly` | a jelzési szabály paraméterei |
| `sorozatok[]` | sorozatonként az utolsó nap: `ertek`, `alapszint`, `elteres`, `kuszob`, `jelzes` |
| `aktiv_jelzesek[]` | a `sorozatok` közül azok, amelyek az utolsó napon jeleznek |
| `jelzesek_utolso_napok[]` | az utolsó 30 nap jelzései |

A `backtest.json` és a `kiserleti_kapuk.json` pillanatkép: a dashboard megfelelő
nézetének adatai, a `keszult` mező szerinti állapotban; naponta nem frissülnek.
