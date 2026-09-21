"""
A GitHub Pages oldal osszeallitasa a docs/ mappaba.

A konzulensnek egyetlen linket kell tudnia megnyitni, telepites es
bejelentkezes nelkul. A GitHub Pages a main ag docs/ mappajat szolgalja ki
statikusan, ezert ide kell masolni a mar legeneralt kimeneteket, es ide kell
beagyazni a diagramokat.

Mi honnan jon:
  docs/index.html   <- scripts/oldal_sablon.html + a hajo_statisztika.json-bol
                       generalt SVG-diagramok (helyorzok cserelve)
  docs/terkep.html  <- outputs/terkep.html      (terkep_epit.py allitja elo)
  docs/abrak/*.png  <- outputs/*.png            (a rajzolo szkriptek)

A diagramok SZAMAI kizarolag a mert JSON-bol jonnek, kezzel beirt szam nincs
bennuk - igy ha a meres valtozik, a lap is valtozik, es nem csuszhatnak szet.

Hasznalat:
    python oldal_epit.py
    python oldal_epit.py --oldal docs --stat outputs/hajo_statisztika.json
"""

import argparse
import json
import shutil
import sys
from pathlib import Path

from utak import KIMENET, OLDAL, SABLONOK
from abrak_svg import savdiagram, vonaldiagram, tablazat, _ezres

# (forras az outputs/-bol, celutvonal a docs/-on belul)
MASOLANDO = [
    ("terkep.html", "terkep.html"),
    ("forgalmi_profil.png", "abrak/forgalmi_profil.png"),
    ("tomorites_tradeoff.png", "abrak/tomorites_tradeoff.png"),
]

# Az oranként abra sorozatai: (stat-csoportnevek osszevonva, megjelenő nev,
# szin-valtozo). Az elso ot sajat hue-t kap - ennyi kulonitheto el biztonsagosan
# szomszedos parokon -, az "egyeb" semleges szurket.
MUNKA_SOROZATOK = [
    (["Teherhajó", "Tanker"], "Áruszállítás", "var(--sor-1)"),
    (["Személyszállító"],     "Személyszállító", "var(--sor-2)"),
    (["Szolgálati"],          "Szolgálati",   "var(--sor-3)"),
    (["Halászhajó"],          "Halászhajó",   "var(--sor-4)"),
    (["Egyéb / ismeretlen"],  "Egyéb",        "var(--sor-0)"),
]

# A navigacios statusz angol szabvanyertekei magyarul. Ami nincs a listan,
# az valtozatlanul jelenik meg - nem talalunk ki forditast.
STATUSZ_HU = {
    "Under way using engine": "Géppel úton",
    "Under way sailing": "Vitorlával úton",
    "Moored": "Kikötve",
    "At anchor": "Horgonyon",
    "Engaged in fishing": "Halászik",
    "Restricted maneuverability": "Korlátozott manőverképesség",
    "Constrained by her draught": "Merülése korlátozza",
    "Power-driven vessel towing astern": "Hátul vontat",
    "Power-driven vessel pushing ahead or towing alongside": "Tol vagy oldalt vontat",
    "Not under command": "Kormányképtelen",
    "Aground": "Zátonyon",
    "Reserved for future amendment [HSC]": "(fenntartott kód, HSC)",
    "Reserved for future amendment [WIG]": "(fenntartott kód, WIG)",
    "Reserved for future use": "(fenntartott kód)",
    "(nem jelentett)": "(nem jelentett)",
}

OSZTALY_MAGYARAZAT = {
    "Class A": "kereskedelmi hajók kötelező jeladója",
    "Class B": "kisebb és szabadidős hajók egyszerűsített jeladója",
    "AtoN": "navigációs jelző (bója) – nem hajó",
    "Base Station": "parti bázisállomás – nem hajó",
    "SAR Airborne": "mentőrepülőgép",
    "Search and Rescue Transponder": "mentő-jeladó – nem hajó",
}


def statusz_hu(nev: str) -> str:
    return STATUSZ_HU.get(nev, nev)


def szazalek(resz, egesz) -> str:
    return f"{resz / max(egesz, 1) * 100:.1f}%".replace(".", ",")


def tipus_abrak(stat) -> str:
    """Ket savdiagram egymas mellett: hajoszam es uzenetszam ugyanarra."""
    cs = [c for c in stat["csoportok"] if c["hajo"] or c["uzenet"]]
    hajo_sorrend = sorted(cs, key=lambda c: -c["hajo"])

    bal = savdiagram([(c["nev"], c["hajo"]) for c in hajo_sorrend],
                     szin_var="var(--sor-1)")
    # A jobb oldali panel UGYANABBAN a sorrendben all, hogy a ket abra
    # sorrol sorra osszevetheto legyen - kulonben nem a kulonbseget mutatna.
    jobb = savdiagram([(c["nev"], c["uzenet"]) for c in hajo_sorrend],
                      szin_var="var(--sor-2)")

    tabla = tablazat(
        ["Típus", "Hajó", "Hajó %", "Üzenet", "Üzenet %"],
        [[c["nev"], _ezres(c["hajo"]), szazalek(c["hajo"], stat["hajo_db"]),
          _ezres(c["uzenet"]), szazalek(c["uzenet"], stat["uzenet_db"])]
         for c in hajo_sorrend])

    return (f'<div class="parosabra">'
            f'<div><p class="abra-alcim">Hány hajó</p>{bal}</div>'
            f'<div><p class="abra-alcim">Hány üzenet</p>{jobb}</div>'
            f'</div>{tabla}')


def osztaly_kartyak(stat) -> str:
    ki = []
    for o in stat["osztalyok"]:
        if o["hajo"] < 5:            # az egyedi darabok a tablazatba valok
            continue
        arany = szazalek(o["hajo"], stat["hajo_db"])
        magyarazat = OSZTALY_MAGYARAZAT.get(o["nev"], "")
        stat_arany = szazalek(o["statusszal"], o["hajo"])
        ki.append(
            f'<div class="kartya"><span class="szam">{_ezres(o["hajo"])}</span>'
            f'<span class="cimke"><b>{o["nev"]}</b> ({arany})<br>{magyarazat}<br>'
            f'státuszt jelent: {stat_arany}</span></div>')
    return "\n".join(ki)


def statusz_abra(stat) -> str:
    sorok = [(statusz_hu(s["nev"]), s["hajo"]) for s in stat["class_a_statusz"]]
    svg = savdiagram(sorok, szin_var="var(--sor-3)", szelesseg=820,
                     cimke_szeles=232)
    tabla = tablazat(
        ["Státusz (eredeti)", "Magyarul", "Hajó", "Arány"],
        [[s["nev"], statusz_hu(s["nev"]), _ezres(s["hajo"]),
          szazalek(s["hajo"], stat["class_a_db"])]
         for s in stat["class_a_statusz"]])
    return svg + tabla


def ora_abrak(stat):
    orak = stat["orank"]
    cimkek = [f'{s["ora"]:02d}' for s in orak]

    kedv = [s.get("Kedvtelési", 0) for s in orak]
    kedv_svg = vonaldiagram(
        cimkek, [("Kedvtelési", kedv, "var(--sor-5)")],
        y_cimke="hajó", x_cimke="óra")

    sorozatok = []
    for stat_nevek, nev, szin in MUNKA_SOROZATOK:
        ertekek = [sum(s.get(n, 0) for n in stat_nevek) for s in orak]
        sorozatok.append((nev, ertekek, szin))
    munka_svg = vonaldiagram(cimkek, sorozatok, y_cimke="hajó", x_cimke="óra")

    fejlec = ["Óra", "Összes hajó", "Üzenet", "Kedvtelési"] + \
             [nev for _, nev, _ in MUNKA_SOROZATOK]
    tabla_sorok = []
    for i, s in enumerate(orak):
        tabla_sorok.append(
            [f'{s["ora"]:02d}', _ezres(s["hajo"]), _ezres(s["uzenet"]),
             _ezres(kedv[i])] + [_ezres(sor[1][i]) for sor in sorozatok])
    tabla = tablazat(fejlec, tabla_sorok, cimke="Óránkénti számok táblázatban")

    return kedv_svg, munka_svg + tabla


def main():
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--kimenet", default=KIMENET,
                    help="A generalt fajlok forrasa (alap: outputs/)")
    ap.add_argument("--oldal", default=OLDAL,
                    help="Az oldal celmappaja (alap: docs/)")
    ap.add_argument("--sablon", default=SABLONOK / "oldal_sablon.html")
    ap.add_argument("--stat", default=KIMENET / "hajo_statisztika.json")
    args = ap.parse_args()

    forras = Path(args.kimenet)
    cel = Path(args.oldal)
    sablon_fajl = Path(args.sablon)
    stat_fajl = Path(args.stat)

    for f, mi in [(sablon_fajl, "a lap sablonja"), (stat_fajl, "a statisztika")]:
        if not f.exists():
            sys.exit(f"Hianyzik {mi}: {f}\n"
                     f"Futtasd le eloszor: python scripts/hajo_statisztika.py <zip>")

    stat = json.loads(stat_fajl.read_text(encoding="utf-8"))
    print(f"Statisztika: {stat_fajl.name} "
          f"({stat['nap']}, {stat['hajo_db']:,} hajo)")

    kedv = next((c for c in stat["csoportok"] if c["nev"] == "Kedvtelési"),
                {"hajo": 0, "uzenet": 0})
    aru = sum(c["hajo"] for c in stat["csoportok"]
              if c["nev"] in ("Teherhajó", "Tanker"))
    ora_hajo = [s["hajo"] for s in stat["orank"]]
    ingadozas = max(ora_hajo) / max(min(ora_hajo), 1)

    kedv_svg, munka_svg = ora_abrak(stat)

    csere = {
        "<!--NAP-->": stat["nap"],
        "<!--HAJO_DB-->": _ezres(stat["hajo_db"]),
        "<!--TIPUS_SAVOK-->": tipus_abrak(stat),
        "<!--KEDV_HAJO_SZAZ-->": szazalek(kedv["hajo"], stat["hajo_db"]),
        "<!--KEDV_UZENET_SZAZ-->": szazalek(kedv["uzenet"], stat["uzenet_db"]),
        "<!--OSZTALY_KARTYAK-->": osztaly_kartyak(stat),
        "<!--CLASS_A_DB-->": _ezres(stat["class_a_db"]),
        "<!--STATUSZ_SAVOK-->": statusz_abra(stat),
        "<!--NAPI_INGADOZAS-->": f"{ingadozas:.2f}".replace(".", ","),
        "<!--ORA_KEDV-->": kedv_svg,
        "<!--ORA_MUNKA-->": munka_svg,
        "<!--ARU_DB-->": _ezres(aru),
        "<!--NEM_HAJO_DB-->": _ezres(stat["nem_hajo_db"]),
    }

    lap = sablon_fajl.read_text(encoding="utf-8")
    hianyzo_helyorzo = [k for k in csere if k not in lap]
    if hianyzo_helyorzo:
        sys.exit("A sablonban nincs meg ez a helyorzo: "
                 + ", ".join(hianyzo_helyorzo))
    for kulcs, ertek in csere.items():
        lap = lap.replace(kulcs, ertek)

    maradek = [k for k in csere if k in lap]
    if maradek:
        sys.exit(f"Kicsereletlen helyorzo maradt: {maradek}")

    cel.mkdir(parents=True, exist_ok=True)
    (cel / "index.html").write_text(lap, encoding="utf-8")
    print(f"  index.html generalva ({len(lap)/1024:.0f} KB, "
          f"{len(csere)} helyorzo cserelve)")

    masolva, hianyzo, osszes_bajt = 0, [], 0
    for honnan, hova in MASOLANDO:
        f = forras / honnan
        c = cel / hova
        if not f.exists():
            hianyzo.append(honnan)
            continue
        c.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(f, c)
        osszes_bajt += c.stat().st_size
        masolva += 1
        print(f"  {honnan:<28} -> {hova:<32} {c.stat().st_size/1024:>8,.0f} KB")

    print(f"\n  {masolva} fajl masolva, osszesen {osszes_bajt/1_048_576:.1f} MB")

    if hianyzo:
        print(f"\n  FIGYELEM - {len(hianyzo)} forrasfajl hianyzik, "
              f"az oldalon torott hivatkozas lesz:")
        for h in hianyzo:
            print(f"    {h}")
        print("  Futtasd le eloszor az ezeket eloallito szkripteket "
              "(ld. README.md).")

    print(f"\n-> {cel} kesz. Helyi ellenorzes:")
    print(f"     python -m http.server 8000 --directory {cel}")

    return 1 if hianyzo else 0


if __name__ == "__main__":
    sys.exit(main())
