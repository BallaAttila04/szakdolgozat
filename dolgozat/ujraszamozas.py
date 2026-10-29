"""
Fejezet-, alfejezet- es tablazatszamok atszamozasa a docx-ben KOVETETT VALTOZTATASKENT.

Csak az eredeti szoveget szamozza at: azokat a futasokat, amelyek nem w:ins-ben
es nem w:del-ben vannak. A korabbi beszurasok (pl. a Kiel-torlesi kor uj
szovegei) mar a vegleges szamokkal keszultek, ezert azokhoz nem nyul.

A lekepezes JSON-ban jon:
  {"fejezet": {"4": "5", "5": "6"},            "N. fejezet" es Heading1 "N. " eleje
   "alfejezet": {"4.1": "5.1", ...},            X.Y es X.Y.Z (a hosszabb kulcs elonyben)
   "tablazat": {"12": "7", ...},                "N. táblázat"
   "abra": {}}                                  "N. ábra"
Ha a megvaltozott szam elott "a"/"az" (vagy "A"/"Az") nevelo all, a nevelo is
igazodik az uj szam kiejtesehez (5 -> az, egyebkent a).
Kihagyott, kezi atnezesre kiirt esetek: a lekepezesben nem szereplo X.Y.Z alak
(pl. verzioszam), torolt alfejezetre mutato szam (a lekepezesben null), a
toldalekos alak, ha az utolso szamjegy valtozik ("4.6-ban" -> "5.5-ben"), es a
futashataron atnyulo talalat.

Hasznalat:
    python ujraszamozas.py lekepezes.json be.docx ki.docx [--szerzo "Attila Balla"] [--tabla csere.csv]
"""

import argparse
import copy
import csv
import json
import re
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path

from lxml import etree

sys.path.insert(0, str(Path(__file__).resolve().parent))
from javitas_beiras import W, XML_SPACE, futas_szoveg, kettevag, valtozas, w  # noqa: E402

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except AttributeError:
    pass

# Nevelo elott allhat; a szam utan alfejezetnel nem allhat szamjegy, pont+szamjegy
# vagy vesszo+szamjegy (tizedes), hogy a verzioszamok es a tizedesek kimaradjanak.
NEVELO = r"(?:(?P<nev>\b(?:[Aa]z|[Aa])) )?"
ALFEJ_RE = re.compile(NEVELO + r"(?<![\d.,])(?P<sz>\d+\.\d+(?:\.\d+)?)(?![\d]|\.\d|,\d)(?P<told>-[a-záéíóöőúüű]+)?")
FEJEZET_RE = re.compile(NEVELO + r"(?<![\d.])(?P<sz>\d+)\.(?= fejezet)")
TABLA_RE = re.compile(NEVELO + r"(?<![\d.])(?P<sz>\d+)\.(?= táblázat)")
ABRA_RE = re.compile(NEVELO + r"(?<![\d.])(?P<sz>\d+)\.(?= ábr)")
H1_RE = re.compile(r"^(?P<sz>\d+)\.(?= )")


def nevelo(regi, uj_szam):
    """Az uj szamhoz illo nevelo: "az", ha a szam kiejtese maganhangzoval kezdodik
    (1 = egy, 5 = öt, 50-59 = ötven...), kulonben "a"; a regi nagybetuje megmarad."""
    if not regi:
        return ""
    elso = uj_szam.split(".")[0]
    kell = "az" if elso == "1" or elso.startswith("5") else "a"
    return (kell.capitalize() if regi[0].isupper() else kell) + " "


def eredeti_futasok(p):
    """A bekezdes eredeti (nem beszurt, nem torolt) futasai, szegmensekre bontva:
    a szegmenshatar egy w:ins / w:del vagy nem w:t tartalom."""
    szegm, akt = [], []
    for el in p.iter(w("r")):
        sz = el.getparent()
        if sz.tag not in (w("p"), w("hyperlink")):
            if akt:
                szegm.append(akt); akt = []
            continue
        akt.append(el)
    if akt:
        szegm.append(akt)
    return szegm


def talalatok(szoveg, lek, h1):
    """(eleje, vege, uj, regi_szam, megjegyzes) a szovegben; megjegyzes != None -> kihagyva."""
    ki = []
    def add(m, uj_szam, kulcs, megj=None):
        e = m.start("nev") if m.group("nev") else m.start("sz")
        v = m.end("sz") + (1 if kulcs in ("fejezet", "tabla", "abra", "h1") else 0)
        regi = szoveg[e:v]
        if megj is None and uj_szam is not None:
            pont = "." if kulcs in ("fejezet", "tabla", "abra", "h1") else ""
            uj = nevelo(m.group("nev"), uj_szam) + uj_szam + pont
            if uj != regi:
                ki.append((e, v, uj, regi, None))
        elif megj:
            ki.append((e, v, None, regi, megj))
    if h1:
        m = H1_RE.match(szoveg)
        if m and m.group("sz") in lek["fejezet"]:
            m2 = re.match(r"(?P<nev>)(?P<sz>\d+)", szoveg)
            add(m2, lek["fejezet"][m.group("sz")], "h1")
        return ki
    for m in ALFEJ_RE.finditer(szoveg):
        sz = m.group("sz")
        if sz.split(".")[0] not in lek["fejezet"]:
            continue
        if sz not in lek["alfejezet"]:
            add(m, None, "alfej", "nincs a lekepezesben (verzioszam?)")
            continue
        uj = lek["alfejezet"][sz]
        if uj is None:
            add(m, None, "alfej", "torolt alfejezetre mutat")
        elif m.group("told") and uj[-1] != sz[-1]:
            add(m, None, "alfej", f"toldalek ({m.group('told')}) -> kezzel: {uj}")
        else:
            add(m, uj, "alfej")
    for rx, kulcs, nev in ((FEJEZET_RE, "fejezet", "fejezet"), (TABLA_RE, "tablazat", "tabla"), (ABRA_RE, "abra", "abra")):
        for m in rx.finditer(szoveg):
            sz = m.group("sz")
            if sz in lek[kulcs]:
                if lek[kulcs][sz] is None:
                    add(m, None, nev, "torolt tetelre mutat")
                else:
                    add(m, lek[kulcs][sz], nev)
    ki.sort()
    return ki


def futasban_cserel(r, eleje, vege, uj, szerzo, datum, azon):
    """A futas [eleje, vege) reszet torli, es utana beszurja az uj szoveget."""
    # a w:lastRenderedPageBreak csak a Word tordelesi gyorsitotara (ujraszamolja),
    # a kettevagasnal duplikalodna, ezert a modositott futasbol kikerul
    for e in r.findall(w("lastRenderedPageBreak")):
        r.remove(e)
    if [e.tag for e in r if e.tag != w("rPr")] != [w("t")]:
        raise ValueError("a futasban nem csak egy w:t van")
    hossz = len(futas_szoveg(r))
    if vege < hossz:
        kettevag(r, vege)
    if eleje > 0:
        _, r = kettevag(r, eleje)
    rpr = r.find(w("rPr"))
    torles = valtozas("del", szerzo, datum, azon)
    r.addprevious(torles)
    for t in r.findall(w("t")):
        t.tag = w("delText"); t.set(XML_SPACE, "preserve")
    torles.append(r)
    ins = valtozas("ins", szerzo, datum, azon + 1)
    ur = etree.SubElement(ins, w("r"))
    if rpr is not None:
        ur.append(copy.deepcopy(rpr))
    ut = etree.SubElement(ur, w("t")); ut.text = uj; ut.set(XML_SPACE, "preserve")
    torles.addnext(ins)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("lekepezes")
    ap.add_argument("be")
    ap.add_argument("ki")
    ap.add_argument("--szerzo", default="Attila Balla")
    ap.add_argument("--tabla", type=Path, help="a cserek listaja CSV-ben (bekezdes, regi, uj, kontextus)")
    args = ap.parse_args()

    lek = json.load(open(args.lekepezes, encoding="utf-8"))
    for k in ("fejezet", "alfejezet", "tablazat", "abra"):
        lek.setdefault(k, {})
    with zipfile.ZipFile(args.be) as z:
        reszek = {n: z.read(n) for n in z.namelist()}
    doc = etree.fromstring(reszek["word/document.xml"])
    datum = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    azon = max([int(e.get(w("id"))) for e in doc.iter(w("ins"), w("del")) if e.get(w("id"))] + [0]) + 1000

    kesz, kihagyva, atnyulo, sorok = 0, [], [], []
    for pid, p in enumerate(doc.iter(w("p"))):
        if p.find(f"{w('pPr')}/{w('rPr')}/{w('del')}") is not None:
            continue                                   # torolt bekezdes
        st = p.find(f"{w('pPr')}/{w('pStyle')}")
        h1 = st is not None and st.get(w("val")) == "Heading1"
        for szegm in eredeti_futasok(p):
            szoveg = "".join(futas_szoveg(r) for r in szegm)
            hatarok, poz = [], 0
            for r in szegm:
                hatarok.append((poz, poz + len(futas_szoveg(r)), r)); poz += len(futas_szoveg(r))
            for eleje, vege, uj, regi, megj in reversed(talalatok(szoveg, lek, h1)):
                kont = szoveg[max(0, eleje - 35):vege + 20]
                if megj:
                    kihagyva.append((pid, regi, megj, kont)); continue
                r = next((x for a, b, x in hatarok if a <= eleje and vege <= b), None)
                if r is None:
                    atnyulo.append((pid, regi, uj, kont)); continue
                a = next(a for a, b, x in hatarok if x is r)
                try:
                    futasban_cserel(r, eleje - a, vege - a, uj, args.szerzo, datum, azon)
                except ValueError as e:
                    kihagyva.append((pid, regi, str(e), kont)); continue
                azon += 2; kesz += 1
                sorok.append({"bekezdes": pid, "regi": regi, "uj": uj, "kontextus": kont})

    reszek["word/document.xml"] = etree.tostring(doc, xml_declaration=True, encoding="UTF-8", standalone=True)
    with zipfile.ZipFile(args.ki, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", reszek.pop("[Content_Types].xml"))
        for n, a in reszek.items():
            z.writestr(n, a)
    if args.tabla:
        with open(args.tabla, "w", encoding="utf-8", newline="") as f:
            wr = csv.DictWriter(f, fieldnames=["bekezdes", "regi", "uj", "kontextus"])
            wr.writeheader(); wr.writerows(sorted(sorok, key=lambda s: s["bekezdes"]))
    print(f"Atszamozva: {kesz}; kihagyva (kezi atnezes): {len(kihagyva)}; futashataron atnyulo: {len(atnyulo)}")
    for pid, regi, megj, kont in kihagyva:
        print(f"  KIHAGYVA [{pid}] {regi!r}: {megj} | …{kont}…")
    for pid, regi, uj, kont in atnyulo:
        print(f"  ATNYULO [{pid}] {regi!r} -> {uj!r} | …{kont}…")


if __name__ == "__main__":
    main()
