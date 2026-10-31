"""
Tablazat- es abrafeliratok szamanak atalakitasa Word-felirattama (SEQ mezove).

A felirat elso szama ("7. táblázat: ...", "2. ábra: ...") kovetett valtoztataskent
SEQ-mezore cserelodik, a mezo gyorsitotarazott erteke a jelenlegi szam, igy a
szoveg nem valtozik, es a TOC \\c jegyzekek megtalaljak. Ha a szam mar kovetett
beszuras (ujraszamozas vagy uj felirat), a mezo a beszurason belulre kerul.
A settings.xml-be bekerul az updateFields, hogy a Word megnyitaskor frissitse a mezoket.
Felirat az a bekezdes, amely keepNext-es, es a szoveg eleje "N. táblázat:" vagy "N. ábra:".

Hasznalat:
    python feliratok_mezo.py be.docx ki.docx [--szerzo "Attila Balla"]
"""

import argparse
import copy
import re
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path

from lxml import etree

sys.path.insert(0, str(Path(__file__).resolve().parent))
from javitas_beiras import XML_SPACE, futas_szoveg, kettevag, valtozas, w  # noqa: E402

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except AttributeError:
    pass

FELIRAT_RE = re.compile(r"^(\d+)\. (táblázat|ábra):")


def seq_futasok(cimke, szam, rpr):
    """A SEQ-mezo futasai a felirat formazasaval; az ertek a jelenlegi szam."""
    def futas():
        r = etree.Element(w("r"))
        if rpr is not None:
            r.append(copy.deepcopy(rpr))
        return r
    ki = []
    for tipus in ("begin", None, "separate", "ertek", "end"):
        r = futas()
        if tipus is None:
            it = etree.SubElement(r, w("instrText"))
            it.text = f" SEQ {cimke} \\* ARABIC "
            it.set(XML_SPACE, "preserve")
        elif tipus == "ertek":
            t = etree.SubElement(r, w("t"))
            t.text = szam
        else:
            etree.SubElement(r, w("fldChar")).set(w("fldCharType"), tipus)
        ki.append(r)
    return ki


def elfogadott_futasok(p):
    """A bekezdes elfogadott nezetu, szoveges futasai (torles nelkul)."""
    return [r for r in p.iter(w("r"))
            if r.getparent().tag != w("del") and r.find(w("t")) is not None]


def atalakit(p, szerzo, datum, azon):
    """Visszaadja a felhasznalt azonositok szamat; 0, ha nem felirat vagy mar mezo."""
    fut = elfogadott_futasok(p)
    szoveg = "".join(futas_szoveg(r) for r in fut)
    m = FELIRAT_RE.match(szoveg)
    if not m or p.find(f".//{w('instrText')}") is not None:
        return 0
    szam = m.group(1)
    elso = fut[0]
    if not futas_szoveg(elso).startswith(szam):
        raise ValueError(f"a felirat szama nem az elso futasban van: {szoveg[:40]!r}")
    if len(futas_szoveg(elso)) > len(szam):
        kettevag(elso, len(szam))
    rpr = elso.find(w("rPr"))
    uj = seq_futasok(m.group(2), szam, rpr)
    if elso.getparent().tag == w("ins"):
        for r in uj:
            elso.addprevious(r)
        elso.getparent().remove(elso)
        return 1
    torles = valtozas("del", szerzo, datum, azon)
    elso.addprevious(torles)
    for t in elso.findall(w("t")):
        t.tag = w("delText")
        t.set(XML_SPACE, "preserve")
    torles.append(elso)
    ins = valtozas("ins", szerzo, datum, azon + 1)
    for r in uj:
        ins.append(r)
    torles.addnext(ins)
    return 2


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("be")
    ap.add_argument("ki")
    ap.add_argument("--szerzo", default="Attila Balla")
    args = ap.parse_args()
    with zipfile.ZipFile(args.be) as z:
        reszek = {n: z.read(n) for n in z.namelist()}
    doc = etree.fromstring(reszek["word/document.xml"])
    datum = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    azon = max([int(e.get(w("id"))) for e in doc.iter(w("ins"), w("del")) if e.get(w("id"))] + [0]) + 1000
    kesz, szamok = 0, {"táblázat": [], "ábra": []}
    osszes = 0
    for p in doc.find(w("body")).findall(w("p")):
        if p.find(f"{w('pPr')}/{w('rPr')}/{w('del')}") is not None:
            continue
        m = FELIRAT_RE.match("".join(futas_szoveg(r) for r in elfogadott_futasok(p)))
        if not m:
            continue
        osszes += 1
        szamok[m.group(2)].append(int(m.group(1)))
        db = atalakit(p, args.szerzo, datum, azon)
        azon += db
        kesz += 1 if db else 0
    beall = etree.fromstring(reszek["word/settings.xml"])
    if beall.find(w("updateFields")) is None:
        uf = etree.Element(w("updateFields"))
        uf.set(w("val"), "true")
        beall.find(w("footnotePr")).addprevious(uf)
        reszek["word/settings.xml"] = etree.tostring(beall, xml_declaration=True, encoding="UTF-8", standalone=True)
    reszek["word/document.xml"] = etree.tostring(doc, xml_declaration=True, encoding="UTF-8", standalone=True)
    with zipfile.ZipFile(args.ki, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", reszek.pop("[Content_Types].xml"))
        for n, a in reszek.items():
            z.writestr(n, a)
    print(f"Felirat: {osszes}, mezove alakitva: {kesz}")
    for cimke, sz in szamok.items():
        folytonos = sz == list(range(1, len(sz) + 1))
        print(f"  {cimke}: {sz[0]}..{sz[-1]} ({len(sz)} db), folytonos: {folytonos}")
        if not folytonos:
            print(f"    SORREND: {sz}")
            sys.exit(1)


if __name__ == "__main__":
    main()
