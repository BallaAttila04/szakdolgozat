"""
Beagyazott SVG-diagramok eloallitasa a weboldalhoz.

Miert SVG es nem PNG: a lap vilagos es sotet temat is tud, egy PNG viszont
egyik temahoz keszul. A beagyazott SVG a lap CSS-valtozoit hasznalja
(`fill="var(--sor-1)"`), igy a temavaltast automatikusan koveti, ezen felul
elesen skalazodik es kereshetok benne a cimkek.

A szinek nem itt dolnek el: a modul CSS-valtozo NEVEKET kap, az ertekuket a
lap sablonja definialja. Az ottani ertekek szinlatas-zavarra (protanopia,
deuteranopia) es feluleti kontrasztra ellenorizve lettek, egymas melletti
sorozatparokon, vilagos es sotet temaban egyarant.

Minden diagramhoz tartozik egy osszecsukott tablazat is. A vilagos temaban
harom szin 3:1 alatti kontraszttal ul a papirszinu feluleten; az ilyen esetet
lathato cimkevel vagy tablazatos nezettel kell ellensulyozni, itt mindketto
megvan.
"""

from html import escape

# Rajzolasi allandok. A modszertan szerint: vekony jelek, 2px vonal,
# 4px lekerekites az ADATVEGEN (az alapvonalnal szogletes marad).
VONAL_VASTAG = 2
SAROK_R = 4
RACS_SZIN = "var(--racs)"

# Kozelito karakterszelesseg a cimkek helyigenyehez. Nem pontos
# szovegmeres - SVG-ben az csak bongeszoben menne -, hanem OVATOS felso
# becsles, hogy a cimke biztosan ne lógjon ki. A fedezet a tulmeretezes.
KAR_SANS = 6.2    # IBM Plex Sans 11.5px
KAR_MONO = 7.1    # IBM Plex Mono 11.5px


def _sz(x) -> str:
    """Rovid szamformatum SVG-koordinatahoz."""
    return f"{x:.2f}".rstrip("0").rstrip(".")


def _ezres(n) -> str:
    return f"{n:,}".replace(",", " ")


def _sav_utvonal(x0, y, w, h, r=SAROK_R) -> str:
    """Vizszintes sav, csak a jobb (adat-) vege lekerekitve."""
    if w <= 0.5:
        return f'M{_sz(x0)},{_sz(y)}h0.5v{_sz(h)}h-0.5z'
    r = min(r, w, h / 2)
    x1 = x0 + w
    return (f'M{_sz(x0)},{_sz(y)}'
            f'H{_sz(x1 - r)}'
            f'A{_sz(r)},{_sz(r)} 0 0 1 {_sz(x1)},{_sz(y + r)}'
            f'V{_sz(y + h - r)}'
            f'A{_sz(r)},{_sz(r)} 0 0 1 {_sz(x1 - r)},{_sz(y + h)}'
            f'H{_sz(x0)}Z')


def savdiagram(sorok, szin_var="var(--sor-1)", szelesseg=390,
               cimke_szeles=126, sor_magassag=26, ertek_formatum=_ezres,
               max_ertek=None):
    """Vizszintes savdiagram.

    sorok: [(cimke, ertek)] - a sorrendet a hivo adja, itt nem rendezunk.
    Egyetlen adatsor, ezert egyetlen szin es nincs jelmagyarazat: a
    hosszusag hordozza az informaciot, nem a szin.
    """
    if not sorok:
        return ""
    csucs = max_ertek if max_ertek is not None else max(e for _, e in sorok)
    csucs = max(csucs, 1)

    # Az ertekcimke helyet a LEGHOSSZABB tenyleges ertekbol szamoljuk, nem
    # fix konstansbol - kulonben a nagy szamok (uzenetszam) kilognak.
    leghosszabb = max(len(ertek_formatum(e)) for _, e in sorok)
    ertek_ter = leghosszabb * KAR_MONO + 12
    sav_ter = szelesseg - cimke_szeles - ertek_ter
    magassag = len(sorok) * sor_magassag + 6

    # Vedokorlat: a cimke sosem lóghat ki balra. Ami nem fer el, azt
    # csonkoljuk - a teljes szoveg a <title>-ben es a tablazatban megmarad.
    max_kar = max(int((cimke_szeles - 8) / KAR_SANS), 6)

    r = [f'<svg viewBox="0 0 {szelesseg} {magassag}" width="100%" '
         f'height="{magassag}" role="img" class="abra">']
    for i, (cimke, ertek) in enumerate(sorok):
        y = i * sor_magassag + 3
        sav_m = sor_magassag - 11
        w = sav_ter * (ertek / csucs)
        rovid = cimke if len(cimke) <= max_kar else cimke[:max_kar - 1] + "…"
        cim = f'<title>{escape(cimke)}</title>' if rovid != cimke else ""
        r.append(
            f'<text class="a-cimke" x="{cimke_szeles - 8}" '
            f'y="{_sz(y + sav_m / 2 + 4)}" text-anchor="end">'
            f'{cim}{escape(rovid)}</text>')
        r.append(f'<path d="{_sav_utvonal(cimke_szeles, y, w, sav_m)}" '
                 f'fill="{szin_var}"/>')
        r.append(
            f'<text class="a-ertek" x="{_sz(cimke_szeles + w + 7)}" '
            f'y="{_sz(y + sav_m / 2 + 4)}">{escape(ertek_formatum(ertek))}</text>')
    r.append("</svg>")
    return "\n".join(r)


def vonaldiagram(x_cimkek, sorozatok, szelesseg=820, magassag=270,
                 y_cimke="", x_cimke="", y_max=None, x_lepes=4):
    """Tobbsorozatos vonaldiagram, kozvetlen cimkekkel a vonalak vegen.

    sorozatok: [(nev, [ertekek], szin_var)] - a szinek sorrendje a hivo
    felelossege; a lap sablonjaban rogzitett, validalt sorrend szerint jonnek.

    A kozvetlen cimke nem dizajn-dolog: vilagos temaban nehany szin 3:1 alatt
    van a feluleten, amit a modszertan csak lathato cimkevel enged at.
    """
    if not sorozatok:
        return ""
    bal, jobb, fent, lent = 40, 132, 14, 30
    px_sz = szelesseg - bal - jobb
    px_m = magassag - fent - lent

    csucs = max(max(ertekek) for _, ertekek, _ in sorozatok)
    # Felfele kerekites szep osztasra
    lepes = 10 ** (len(str(int(csucs))) - 1)
    while csucs / lepes > 5:
        lepes *= 2
    teto = (int(csucs / lepes) + 1) * lepes
    if y_max is not None:          # pl. szazalekos tengely: fixen 100
        teto = y_max

    n = len(x_cimkek)
    X = lambda i: bal + (px_sz * i / max(n - 1, 1))
    Y = lambda v: fent + px_m * (1 - v / teto)

    r = [f'<svg viewBox="0 0 {szelesseg} {magassag}" width="100%" '
         f'height="{magassag}" role="img" class="abra">']

    # Recesszív racs + y-tengely cimkek
    oszt = 4
    for k in range(oszt + 1):
        v = teto * k / oszt
        y = Y(v)
        r.append(f'<line x1="{bal}" y1="{_sz(y)}" x2="{_sz(bal + px_sz)}" '
                 f'y2="{_sz(y)}" stroke="{RACS_SZIN}" stroke-width="1"/>')
        r.append(f'<text class="a-tengely" x="{bal - 7}" y="{_sz(y + 3.5)}" '
                 f'text-anchor="end">{_ezres(int(v))}</text>')

    # x tengely cimkek - minden 4. ora, hogy ne torlodjon
    for i, c in enumerate(x_cimkek):
        if i % x_lepes and i != n - 1:
            continue
        r.append(f'<text class="a-tengely" x="{_sz(X(i))}" '
                 f'y="{magassag - 12}" text-anchor="middle">{escape(c)}</text>')
    if x_cimke:
        r.append(f'<text class="a-tengely" x="{_sz(bal + px_sz / 2)}" '
                 f'y="{magassag - 1}" text-anchor="middle">{escape(x_cimke)}</text>')
    if y_cimke:
        r.append(f'<text class="a-tengely" x="{bal - 7}" y="{fent - 4}" '
                 f'text-anchor="end">{escape(y_cimke)}</text>')

    # Vonalak
    for nev, ertekek, szin in sorozatok:
        pontok = " ".join(f"{_sz(X(i))},{_sz(Y(v))}" for i, v in enumerate(ertekek))
        r.append(f'<polyline points="{pontok}" fill="none" stroke="{szin}" '
                 f'stroke-width="{VONAL_VASTAG}" stroke-linejoin="round" '
                 f'stroke-linecap="round"/>')

    # Kozvetlen cimkek a jobb szelen, utkozesmentesitve
    vegek = sorted(((Y(ertekek[-1]), nev, szin)
                    for nev, ertekek, szin in sorozatok), key=lambda t: t[0])
    MIN_TAV = 13
    elozo = -1e9
    for y, nev, szin in vegek:
        y = max(y, elozo + MIN_TAV)
        elozo = y
        r.append(f'<text class="a-vegcimke" x="{_sz(bal + px_sz + 9)}" '
                 f'y="{_sz(y + 3.5)}" fill="{szin}">{escape(nev)}</text>')
    r.append("</svg>")
    return "\n".join(r)


def tablazat(fejlec, sorok, osszecsukva=True, cimke="Számok táblázatban"):
    """A diagram adatai tablazatban - a modszertan altal kert alternativ nezet."""
    fej = "".join(f"<th>{escape(str(c))}</th>" for c in fejlec)
    test = "".join(
        "<tr>" + "".join(f"<td>{escape(str(c))}</td>" for c in sor) + "</tr>"
        for sor in sorok)
    nyit = "" if osszecsukva else " open"
    return (f'<details class="abra-tabla"{nyit}><summary>{escape(cimke)}</summary>'
            f'<table><thead><tr>{fej}</tr></thead><tbody>{test}</tbody></table>'
            f'</details>')
