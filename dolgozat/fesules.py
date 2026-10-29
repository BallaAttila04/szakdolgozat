"""
A dolgozat egy dokumentumba fesulese, a vegleges sorrendben.

Forrasok:
  szakdolgozat_piszkozat_1-3_fejezet.docx  az 1-3. fejezet es a Hivatkozasok
                                            (alap: stilusok, lablec, kovetett valtoztatasok)
  dsr_piszkozat.md                          Bevezetes, atdolgozott 2.1, 4-5. fejezet,
                                            Osszefoglalas, Uj hivatkozasok

Sorrend: Bevezetes - 1. - 2. (a 2.1 helyen az atdolgozott 2.1, a 6. tablazattal)
- 3. - 4. - 5. - Osszefoglalas - Hivatkozasok (a regi es az uj tetelek egy
abece-rendu listaban).

A md HTML-kommentjei (a szamok "forras:" jegyzetei es a szerkesztoi
megjegyzesek) a dokumentumbol kimaradnak; a szamforrasok.md-be kerulnek,
alfejezet es szovegkornyezet szerint, hogy a szamok eredete visszakeresheto
maradjon. A md "Javitando a meglevo fejezetekben" listaja nem resze a
dolgozatnak, kimarad (a md-ben megmarad).

A docx kovetett valtoztatasai (az 1. fejezet elfogadasra varo javaslatai)
valtozatlanul, elfogadatlanul atkerulnek.

Hasznalat:
    python fesules.py
    python fesules.py --docx X.docx --md Y.md --ki Z.docx --forrasok F.md
"""

import argparse
import copy
import re
import struct
import sys
import unicodedata
import zipfile
from datetime import datetime, timezone
from pathlib import Path

from lxml import etree

DOLGOZAT = Path(__file__).resolve().parent
GYOKER = DOLGOZAT.parent

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
W = "{%s}" % W_NS
R_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
WP = "{http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing}"
A = "{http://schemas.openxmlformats.org/drawingml/2006/main}"
PIC = "{http://schemas.openxmlformats.org/drawingml/2006/picture}"

# --- A docx szerkezete (indexek a body gyerekelemei kozott) -----------------
# Ellenorizve a 2026-10-09-i docx-en; a szkript a cimsorok szovegevel is
# ellenorzi, hogy a helyuk nem valtozott-e.
CIM_21 = "2.1 A kutatási kérdések és a módszertani keret"
CIM_22 = "2.2 A vizsgált adathalmaz"
CIM_HIV = "Hivatkozások"
TABLA6_FELIRAT = "6. táblázat:"

# A szoveg szelessege (A4, 2,5 cm-es margok): 9071 dxa = 16,0 cm; a meglevo
# 1. abra 5 486 400 EMU (15,24 cm) szeles - az uj abrak is ennyik.
TABLA_SZELESSEG = 9071
ABRA_SZELESSEG_EMU = 5486400

# Az atdolgozott 2.1 szerkesztoi megjegyzese a folyo szovegben; a vegleges
# szovegbol kimarad (a 6. tablazat valoban valtozatlan).
SZERKESZTOI_CSERE = [("A 6. táblázat (változatlanul) összefoglalja",
                      "A 6. táblázat összefoglalja")]
CIM_UTOTAG = " – ÁTDOLGOZOTT VÁLTOZAT"


def wq(tag):
    return W + tag


def elem(tag, attrib=None, *gyerek):
    e = etree.Element(wq(tag))
    for k, v in (attrib or {}).items():
        e.set(wq(k), str(v))
    for g in gyerek:
        e.append(g)
    return e


def szoveg(e):
    return "".join(x.text or "" for x in e.iter(wq("t")))


# --- Soron beluli md-formazas ----------------------------------------------

INLINE = re.compile(r"(\*\*.+?\*\*|`[^`]+`|(?<![*\w])\*(?![\s*])[^*]+?\*(?![*\w]))")


def futasok(md_szoveg, alap=None):
    """**felkover**, *dolt*, `kod` -> w:r elemek. alap: kozos rPr-beallitasok."""
    alap = alap or {}
    ki = []
    for darab in INLINE.split(md_szoveg):
        if not darab:
            continue
        f = dict(alap)
        if darab.startswith("**") and darab.endswith("**") and len(darab) > 4:
            darab, f["b"] = darab[2:-2], True
        elif darab.startswith("`") and darab.endswith("`"):
            darab, f["kod"] = darab[1:-1], True
        elif darab.startswith("*") and darab.endswith("*") and len(darab) > 2:
            darab, f["i"] = darab[1:-1], True
        ki.append(futas(darab, **f))
    return ki


def futas(t, b=False, i=False, sz=None, kod=False):
    rpr = elem("rPr")
    if kod:
        rpr.append(elem("rFonts", {"ascii": "Courier New", "hAnsi": "Courier New",
                                   "cs": "Courier New"}))
    if b:
        rpr.extend([elem("b"), elem("bCs")])
    if i:
        rpr.extend([elem("i"), elem("iCs")])
    if kod and not sz:
        sz = 20
    if sz:
        rpr.extend([elem("sz", {"val": sz}), elem("szCs", {"val": sz})])
    te = elem("t")
    te.text = t
    te.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
    return elem("r", None, rpr, te)


def ppr(spacing=None, ind=None, jc=None, keep_next=False):
    p = elem("pPr", None, elem("pStyle", {"val": "Normal"}))
    if keep_next:
        p.append(elem("keepNext", {"val": "true"}))
    if spacing:
        p.append(elem("spacing", spacing))
    if ind:
        p.append(elem("ind", ind))
    if jc:
        p.append(elem("jc", {"val": jc}))
    p.append(elem("rPr"))
    return p


TORZS = dict(spacing={"lineRule": "auto", "line": 360, "before": 0, "after": 160}, jc="both")
LISTA = dict(spacing={"lineRule": "auto", "line": 360, "before": 0, "after": 120},
             ind={"left": 567, "hanging": 283}, jc="both")
FELIRAT = dict(spacing={"before": 200, "after": 80}, keep_next=True)
FORRAS = dict(spacing={"before": 60, "after": 240})
ABRA = dict(spacing={"before": 60, "after": 60}, jc="center", keep_next=True)
HIV = dict(spacing={"lineRule": "auto", "line": 360, "before": 0, "after": 60},
           ind={"hanging": 567, "left": 567})


def bekezdes(md_szoveg, beall, alap=None, elotag=None):
    p = elem("p", None, ppr(**beall))
    if elotag:
        r = futas(elotag)
        p.append(r)
        p.append(elem("r", None, elem("rPr"), elem("tab")))
    p.extend(futasok(md_szoveg, alap))
    return p


# --- Tablazat -------------------------------------------------------------

def cellak(sor):
    s = sor.strip()
    if s.startswith("|"):
        s = s[1:]
    if s.endswith("|"):
        s = s[:-1]
    return [c.strip() for c in s.split("|")]


# 10 pt-os Times New Roman: legfeljebb kb. 110 dxa egy karakter (nagybetu,
# szamjegy, felkover); a cella
# bal+jobb margoja 200 dxa (a minta tblCellMar-ja), plusz 60 tartalek.
KAR_DXA = 110
CELLA_MARGO = 260
# egy nagyon hosszu szo (pl. URL) ne vigye el az egesz tablazatot
MIN_OSZLOP_MAX = 2600


def oszlopszelesseg(sorok):
    """Elobb minden oszlop megkapja a leghosszabb, nem torheto szavanak
    megfelelo minimumot, a maradek a tartalom hossza szerint oszlik el."""
    n = len(sorok[0])
    minimum, suly = [], []
    for j in range(n):
        h = [len(r[j].replace("**", "")) for r in sorok]
        szo = max((len(w) for r in sorok for w in r[j].replace("**", "").split()), default=2)
        minimum.append(min(szo * KAR_DXA + CELLA_MARGO, MIN_OSZLOP_MAX))
        suly.append(0.5 * max(h) + 0.5 * sum(h) / len(h))
    marad = TABLA_SZELESSEG - sum(minimum)
    if marad < 0:
        w = [int(m * TABLA_SZELESSEG / sum(minimum)) for m in minimum]
    else:
        w = [int(m + marad * s / sum(suly)) for m, s in zip(minimum, suly)]
    w[-1] += TABLA_SZELESSEG - sum(w)
    return w


def tablazat(md_sorok, tblpr_minta):
    sorok = [cellak(s) for s in md_sorok]
    fej, test = sorok[0], sorok[2:]
    if not re.fullmatch(r"[\s|:-]+", md_sorok[1]):
        raise ValueError(f"Nem tablazat-elvalaszto: {md_sorok[1]}")
    n = len(fej)
    for r in test:
        if len(r) != n:
            raise ValueError(f"Oszlopszam-elteres ({len(r)} vs {n}): {r}")
    szel = oszlopszelesseg([fej] + test)
    tbl = elem("tbl", None, copy.deepcopy(tblpr_minta))
    grid = elem("tblGrid")
    for x in szel:
        grid.append(elem("gridCol", {"w": x}))
    tbl.append(grid)
    for k, r in enumerate([fej] + test):
        tr = elem("tr")
        if k == 0:
            tr.append(elem("trPr", None, elem("tblHeader", {"val": "true"})))
        for j, c in enumerate(r):
            tcpr = elem("tcPr", None, elem("tcW", {"w": szel[j], "type": "dxa"}))
            hat = elem("tcBorders")
            for o in ("top", "left", "bottom", "right"):
                hat.append(elem(o, {"val": "single", "sz": 4, "space": 0, "color": "808080"}))
            tcpr.append(hat)
            if k == 0:
                tcpr.append(elem("shd", {"color": "auto", "fill": "E7E6E6", "val": "clear"}))
            p = elem("p", None, ppr())
            p.extend(futasok(c, {"sz": 20, "b": k == 0}))
            tr.append(elem("tc", None, tcpr, p))
        tbl.append(tr)
    return tbl


# --- Abra -----------------------------------------------------------------

def png_meret(adat: bytes):
    if adat[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError("nem PNG")
    return struct.unpack(">II", adat[16:24])


def abra_bekezdes(minta, rid, nev, docpr_id, szel_px, mag_px):
    p = copy.deepcopy(minta)
    cy = int(ABRA_SZELESSEG_EMU * mag_px / szel_px)
    for e in p.iter(WP + "extent", A + "ext"):
        e.set("cx", str(ABRA_SZELESSEG_EMU))
        e.set("cy", str(cy))
    for e in p.iter(WP + "docPr", PIC + "cNvPr"):
        e.set("id", str(docpr_id))
        e.set("name", nev)
    for e in p.iter(A + "blip"):
        e.set("{%s}embed" % R_NS, rid)
    return p


# --- md blokkokra bontasa -------------------------------------------------

KOMMENT = re.compile(r"<!--(.*?)-->", re.S)
CIMSOR = re.compile(r"^(#{1,4})\s+(.*)$")
FELIRAT_RE = re.compile(r"^\*\*(\d+\. táblázat: .*)\*\*$")
ABRA_RE = re.compile(r"^\[(\d+\. ábra: .*?) – fájl: (\S+)\]$")
LISTA_RE = re.compile(r"^-\s+(.*)$")
SZAMOZOTT_RE = re.compile(r"^(\d+)\.\s+(.*)$")


def kommentek_ki(md: str):
    """A kommenteket kiveszi, es visszaadja oket kornyezettel."""
    jegyzet = []
    utolso_cim = ""
    poz = 0
    for m in KOMMENT.finditer(md):
        elotte = md[poz:m.start()]
        for sor in md[:m.start()].splitlines()[::-1]:
            c = CIMSOR.match(sor)
            if c:
                utolso_cim = c.group(2).replace(CIM_UTOTAG, "")
                break
        kornyezet = KOMMENT.sub("", md[max(0, m.start() - 400):m.start()])
        kornyezet = kornyezet.splitlines()[-1] if kornyezet.splitlines() else ""
        kornyezet = kornyezet.strip().lstrip("|").strip()
        jegyzet.append((utolso_cim, kornyezet[-110:], " ".join(m.group(1).split())))
        poz = m.end()
    return KOMMENT.sub("", md), jegyzet


def blokkok(sorok):
    ki, i = [], 0
    while i < len(sorok):
        s = sorok[i].rstrip()
        if not s.strip() or s.strip() == "---":
            i += 1
            continue
        if s.startswith("|"):
            t = []
            while i < len(sorok) and sorok[i].startswith("|"):
                t.append(sorok[i].rstrip())
                i += 1
            ki.append(("tabla", t))
            continue
        m = CIMSOR.match(s)
        if m:
            ki.append(("cim", len(m.group(1)), m.group(2).replace(CIM_UTOTAG, "").strip()))
        elif FELIRAT_RE.match(s):
            ki.append(("felirat", FELIRAT_RE.match(s).group(1)))
        elif ABRA_RE.match(s):
            ki.append(("abra",) + ABRA_RE.match(s).groups())
        elif s.startswith("Forrás:"):
            ki.append(("forras", s))
        elif LISTA_RE.match(s):
            ki.append(("lista", "–", LISTA_RE.match(s).group(1)))
        elif SZAMOZOTT_RE.match(s):
            m = SZAMOZOTT_RE.match(s)
            ki.append(("lista", m.group(1) + ".", m.group(2)))
        else:
            ki.append(("bek", s.strip()))
        i += 1
    return ki


def szakasz(sorok, kezdo, zaro):
    """A kezdo cimsortol (bele) a zaro cimsorig (nem bele)."""
    def hol(cim):
        for k, s in enumerate(sorok):
            if s.rstrip() == cim:
                return k
        sys.exit(f"Nincs ilyen cimsor a md-ben: {cim!r}")
    a = hol(kezdo)
    b = hol(zaro) if zaro else len(sorok)
    return sorok[a:b]


# --- Fo program -----------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--docx", type=Path, default=DOLGOZAT / "szakdolgozat_piszkozat_1-3_fejezet.docx")
    ap.add_argument("--md", type=Path, default=DOLGOZAT / "dsr_piszkozat.md")
    ap.add_argument("--abrak", type=Path, default=GYOKER, help="az abrak fajlutvonalainak gyokere")
    ap.add_argument("--ki", type=Path, default=DOLGOZAT / "szakdolgozat_teljes_piszkozat.docx")
    ap.add_argument("--forrasok", type=Path, default=DOLGOZAT / "szamforrasok.md")
    ap.add_argument("--szerzo", default="Attila Balla")
    args = ap.parse_args()

    with zipfile.ZipFile(args.docx) as z:
        reszek = {n: z.read(n) for n in z.namelist()}
    doc = etree.fromstring(reszek["word/document.xml"])
    body = doc.find(wq("body"))
    els = list(body)

    def index(felt, nev):
        talalat = [k for k, e in enumerate(els) if felt(e)]
        if len(talalat) != 1:
            sys.exit(f"{nev}: {len(talalat)} talalat a docx-ben (1 kell)")
        return talalat[0]

    i21 = index(lambda e: szoveg(e) == CIM_21, CIM_21)
    i22 = index(lambda e: szoveg(e) == CIM_22, CIM_22)
    ihiv = index(lambda e: szoveg(e) == CIM_HIV, CIM_HIV)
    it6 = index(lambda e: szoveg(e).startswith(TABLA6_FELIRAT), TABLA6_FELIRAT)
    if not (i21 < it6 < i22 < ihiv):
        sys.exit("A docx szerkezete valtozott")
    tabla6 = els[it6:it6 + 3]          # felirat, tablazat, forrassor
    if tabla6[1].tag != wq("tbl") or not szoveg(tabla6[2]).startswith("Forrás:"):
        sys.exit("A 6. tablazat blokkja nem felirat-tablazat-forras")
    oldaltores = els[ihiv - 1]
    if 'w:type="page"' not in etree.tostring(oldaltores, encoding="unicode"):
        sys.exit("A Hivatkozasok elott nincs oldaltores")
    cim_minta = {}
    for e in els:
        ps = e.find(f"{wq('pPr')}/{wq('pStyle')}")
        if ps is not None and ps.get(wq("val")).startswith("Heading"):
            cim_minta.setdefault(int(ps.get(wq("val"))[-1]), e)
    tblpr_minta = next(e for e in els if e.tag == wq("tbl")).find(wq("tblPr"))
    abra_minta = next(e for e in els if e.find(f".//{wq('drawing')}") is not None)
    hiv_regi = [e for e in els[ihiv + 1:] if e.tag == wq("p")]
    sectpr = els[-1]
    assert sectpr.tag == wq("sectPr")

    md_nyers = args.md.read_text(encoding="utf-8")
    md, jegyzet = kommentek_ki(md_nyers)
    for regi, uj in SZERKESZTOI_CSERE:
        if md.count(regi) != 1:
            sys.exit(f"Szerkesztoi csere: {md.count(regi)} talalat: {regi!r}")
        md = md.replace(regi, uj)
    sorok = md.splitlines()
    bev = blokkok(szakasz(sorok, "# Bevezetés", "## 2.1 A kutatási kérdések és a módszertani keret" + CIM_UTOTAG))
    uj21 = blokkok(szakasz(sorok, "## 2.1 A kutatási kérdések és a módszertani keret" + CIM_UTOTAG,
                           "# 4. Az artefaktum értékelése"))
    f45 = blokkok(szakasz(sorok, "# 4. Az artefaktum értékelése", "# Összefoglalás"))
    ossz = blokkok(szakasz(sorok, "# Összefoglalás", "# Új hivatkozások"))
    ujhiv = blokkok(szakasz(sorok, "# Új hivatkozások", "# Javítandó a meglévő fejezetekben"))

    # kepek
    rels = etree.fromstring(reszek["word/_rels/document.xml.rels"])
    docpr = 9002
    stat = {"bek": 0, "lista": 0, "tabla": 0, "abra": 0, "cim": 0, "felirat": 0, "forras": 0}

    def word(bl, elso_dok=False):
        ki = []
        nonlocal docpr
        for b in bl:
            fajta = b[0]
            stat[fajta] += 1
            if fajta == "cim":
                szint, cim = b[1], b[2]
                if szint == 1 and not (elso_dok and not ki):
                    ki.append(copy.deepcopy(oldaltores))
                minta = cim_minta[szint]
                p = elem("p", None, copy.deepcopy(minta.find(wq("pPr"))))
                p.append(futas(cim))
                ki.append(p)
            elif fajta == "bek":
                ki.append(bekezdes(b[1], TORZS))
            elif fajta == "lista":
                ki.append(bekezdes(b[2], LISTA, elotag=b[1]))
            elif fajta == "felirat":
                ki.append(bekezdes(b[1], FELIRAT, {"b": True, "sz": 22}))
            elif fajta == "forras":
                ki.append(bekezdes(b[1], FORRAS, {"i": True, "sz": 20}))
            elif fajta == "tabla":
                ki.append(tablazat(b[1], tblpr_minta))
            elif fajta == "abra":
                felirat, ut = b[1], b[2]
                adat = (args.abrak / ut).read_bytes()
                sz, mg = png_meret(adat)
                nev = Path(ut).name
                media = f"word/media/{nev}"
                if media in reszek:
                    sys.exit(f"Mar letezik: {media}")
                reszek[media] = adat
                rid = f"rIdKep{docpr - 9000}"
                rels.append(etree.Element("{http://schemas.openxmlformats.org/package/2006/relationships}Relationship",
                                          Id=rid, Type=R_NS + "/image", Target=f"media/{nev}"))
                ki.append(bekezdes(felirat, FELIRAT, {"b": True, "sz": 22}))
                ki.append(abra_bekezdes(abra_minta, rid, nev, docpr, sz, mg))
                docpr += 1
        return ki

    uj_body = []
    uj_body += word(bev, elso_dok=True)
    uj_body.append(copy.deepcopy(oldaltores))
    uj_body += els[:i21]
    # az atdolgozott 2.1; a 6. tablazat az "A 6. tablazat osszefoglalja" bekezdes utan
    uj21_word = word(uj21)
    hely = [k for k, e in enumerate(uj21_word) if szoveg(e).startswith("A 6. táblázat összefoglalja")]
    if len(hely) != 1:
        sys.exit("A 6. tablazat helye nem egyertelmu az atdolgozott 2.1-ben")
    uj21_word[hely[0] + 1:hely[0] + 1] = tabla6
    uj_body += uj21_word
    uj_body += els[i22:ihiv - 1]
    uj_body += word(f45)
    uj_body += word(ossz)
    uj_body.append(oldaltores)
    uj_body.append(els[ihiv])

    # irodalomjegyzek: regi + uj, abece-rendben
    uj_hiv_p = []
    for b in ujhiv:
        if b[0] == "cim":
            continue
        if b[0] != "bek":
            sys.exit(f"Varatlan elem az Uj hivatkozasok kozott: {b}")
        if b[1].startswith("A meglévő hivatkozáslistából"):
            jegyzet.append(("Új hivatkozások", "", b[1]))
            continue
        uj_hiv_p.append(bekezdes(b[1], HIV))

    def kulcs(p):
        t = unicodedata.normalize("NFKD", szoveg(p)).encode("ascii", "ignore").decode().casefold()
        return re.sub(r"[^a-z0-9 ]", "", t)

    def szerzo_ev(p):
        t = szoveg(p)
        m = re.match(r"\s*([^,(]+).*?\((\d{4}|é\. n\.)", t)
        return (m.group(1).strip(), m.group(2)) if m else (t[:20], "")

    regi_kulcs = {szerzo_ev(p) for p in hiv_regi if szoveg(p).strip()}
    dupla = [szerzo_ev(p) for p in uj_hiv_p if szerzo_ev(p) in regi_kulcs]
    ures = [p for p in hiv_regi if not szoveg(p).strip()]
    hiv = sorted([p for p in hiv_regi if szoveg(p).strip()] + uj_hiv_p, key=kulcs)
    uj_body += hiv + ures
    uj_body.append(sectpr)

    # dupla oldaltores (a forras 1. fejezetenek utolso bekezdese oldaltoressel
    # zarul, es utana egy kulon oldaltores-bekezdes jon -> ures oldal): a
    # bekezdes vegi torest elhagyjuk, ha utana kulon oldaltores kovetkezik
    def csak_tores(r):
        return (r is not None and r.tag == wq("r") and r.find(wq("br")) is not None
                and r.find(wq("br")).get(wq("type")) == "page" and not szoveg(r))
    dupla_tores = 0
    for k in range(len(uj_body) - 1):
        e, kov = uj_body[k], uj_body[k + 1]
        if e.tag != wq("p") or not szoveg(e).strip():
            continue
        utolso = e.findall(wq("r"))[-1] if e.findall(wq("r")) else None
        kov_tores = kov.tag == wq("p") and not szoveg(kov).strip() and \
            any(csak_tores(r) for r in kov.findall(wq("r")))
        if csak_tores(utolso) and kov_tores:
            e.remove(utolso)
            dupla_tores += 1

    for e in list(body):
        body.remove(e)
    for e in uj_body:
        body.append(e)

    reszek["word/document.xml"] = etree.tostring(doc, xml_declaration=True, encoding="UTF-8", standalone=True)
    reszek["word/_rels/document.xml.rels"] = etree.tostring(rels, xml_declaration=True, encoding="UTF-8", standalone=True)

    # nyelv: magyar (a helyesiras-ellenorzeshez); a forrasban en-GB volt
    nyelv = 0
    for n in ("word/styles.xml", "word/settings.xml"):
        s = reszek[n].decode("utf-8")
        nyelv += s.count('w:val="en-GB"')
        reszek[n] = s.replace('w:val="en-GB"', 'w:val="hu-HU"').encode("utf-8")
    core = reszek["docProps/core.xml"].decode("utf-8")
    most = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    core = re.sub(r"<dc:creator>.*?</dc:creator>", f"<dc:creator>{args.szerzo}</dc:creator>", core)
    core = re.sub(r"<cp:lastModifiedBy>.*?</cp:lastModifiedBy>|<cp:lastModifiedBy/>",
                  f"<cp:lastModifiedBy>{args.szerzo}</cp:lastModifiedBy>", core)
    core = re.sub(r"<dc:title>.*?</dc:title>|<dc:title/>", "<dc:title>Szakdolgozat – piszkozat</dc:title>", core)
    core = re.sub(r"<dc:language>.*?</dc:language>", "<dc:language>hu-HU</dc:language>", core)
    core = re.sub(r'(<dcterms:modified[^>]*>).*?(</dcterms:modified>)', rf"\g<1>{most}\g<2>", core)
    reszek["docProps/core.xml"] = core.encode("utf-8")

    args.ki.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(args.ki, "w", zipfile.ZIP_DEFLATED) as z:
        if "[Content_Types].xml" in reszek:
            z.writestr("[Content_Types].xml", reszek.pop("[Content_Types].xml"))
        for n, adat in reszek.items():
            z.writestr(n, adat)

    # kiseroallomany: a szamok forrasai
    t = ["# A számok forrásai a dolgozatban",
         "",
         f"A `fesules.py` generálja a `{args.md.name}` HTML-kommentjeiből ({len(jegyzet)} db), "
         f"{most[:10]}. A dolgozat szövegéből ezek kimaradtak; itt alfejezetenként, a "
         "megjegyzés előtti szövegrész végével együtt szerepelnek. Az 1–3. fejezet "
         "számainak forrása a `szamok.md` és a `naplo.md`.", ""]
    cim = None
    for c, k, j in jegyzet:
        if c != cim:
            t += ["", f"## {c or '(a fájl eleje)'}", ""]
            cim = c
        t.append(f"- …{k} → {j}" if k else f"- {j}")
    args.forrasok.write_text("\n".join(t) + "\n", encoding="utf-8")

    print(f"Bemenet: {args.docx.name} ({len(els)} elem), {args.md.name} ({len(md_nyers.splitlines())} sor)")
    print(f"md-blokkok: " + ", ".join(f"{k} {v}" for k, v in stat.items()))
    print(f"Kommentek kiveve: {len(jegyzet)} (-> {args.forrasok.name})")
    print(f"Hivatkozasok: {len([p for p in hiv_regi if szoveg(p).strip()])} regi + {len(uj_hiv_p)} uj = {len(hiv)}"
          + (f"; LEHETSEGES DUPLIKATUM: {dupla}" if dupla else "; duplikatum nincs"))
    print(f"Nyelv en-GB -> hu-HU: {nyelv} helyen; szerzo: {args.szerzo}")
    print(f"Dupla oldaltores (ures oldal) megszuntetve: {dupla_tores}")
    print(f"Kimenet: {args.ki} ({len(uj_body) - 1} elem a torzsben)")


if __name__ == "__main__":
    main()
