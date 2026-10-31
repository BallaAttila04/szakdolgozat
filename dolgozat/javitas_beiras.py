"""
Ellenorzott szovegcserek beirasa a docx-be KOVETETT VALTOZTATASKENT.

Bemenet: JSON-lista, elemenkent {"id": <bekezdes-azonosito>, "regi": ..., "uj": ...},
vagy objektum: {"valtozasok": [ugyanez], "uj_bekezdesek": [{"utan_id", "sorrend",
"stilus": Heading2|Heading3|torzs|lista|hivatkozas, "szoveg"}]}. Az uj bekezdes
kovetett beszuraskent kerul a megadott (torzs-szintu) bekezdes utan; a szovegben
**felkover** es *dolt* jeloles hasznalhato, a formazas a fesules.py-e.
A bekezdes-azonosito a dokumentum w:p elemeinek sorszama dokumentumsorrendben
(ugyanaz, mint a munka/bekezdesek.txt-ben). A "regi" a bekezdes elfogadott
nezetu szovegenek (w:t, a w:del nelkul) pontosan egyszer elofordulo reszlete.

A csere: a "regi" szoveget lefedo futasok w:del-be kerulnek (w:t -> w:delText),
utanuk egy w:ins jon az "uj" szoveggel, az elso torolt futas formazasaval.
Ha egy reszlet egy meglevo w:ins-en vagy w:del-en belul van, vagy nem egyedi,
a csere kimarad, es a kimenet jelzi (kezi javitas).

Teljes torles (az objektum-bemenetben):
  "torolt_bekezdesek": [id, ...]  a bekezdes minden futasa w:del-be kerul, es a
                                  bekezdesjel is torolt (w:pPr/w:rPr/w:del), igy
                                  elfogadas utan a bekezdes eltunik
  "torolt_tablak": [id, ...]      az id a tablazat barmely cellabekezdese; minden
                                  sor torolt (w:trPr/w:del), a cellak tartalma is
Az uj bekezdes stilusa "oldaltores" is lehet (ures bekezdes egy oldaltoressel).
A futas vegen az elfogadott nezetet szimulalja (torles elhagyva, beszuras
megtartva, torolt bekezdesjel es sor eltavolitva), es kiirja a bekezdesszamot.

Az uj bekezdes "utan_id" helyett "elott_id"-t is kaphat, tovabbi stilusai:
  "felirat", "forras"   tablazat- es abrafelirat, forrassor (a meglevok formazasaval)
  "abra"                a "kep" mezoben megadott PNG, kovetett beszuraskent
  "tabla"               a "sorok" mezoben Markdown-tablazat, minden sora kovetett
  "kozep"               kozepre zart sor, opcionalis "meret" (pont), "felkover", "elotte", "utana"
  "felkover"            felkover cimke, nem cimsor (nem kerul a tartalomjegyzekbe)
  "szakasztores"        a bekezdes zarja az elozo szakaszt (lablec nelkul, igy oldalszam nelkul)
  "mezo"                Word-mezo: "utasitas" (pl. TOC), "szoveg" a frissites elotti helyorzo

Hasznalat:
    python javitas_beiras.py valtozasok.json be.docx ki.docx
    python javitas_beiras.py valtozasok.json be.docx ki.docx --szerzo "Attila Balla"
"""

import argparse
import copy
import json
import sys
import zipfile
from collections import defaultdict
from datetime import datetime, timezone

from pathlib import Path

from lxml import etree

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fesules  # noqa: E402  (formazasi mintak: futasok, ppr, TORZS, LISTA, HIV)

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
W = "{%s}" % W_NS
XML_SPACE = "{http://www.w3.org/XML/1998/namespace}space"


def w(tag):
    return W + tag


def futas_szoveg(r):
    return "".join(t.text or "" for t in r.findall(w("t")))


def bekezdes_futasok(p):
    """A bekezdes elfogadott nezetu futasai sorrendben: (futas, szulo-tipus)."""
    ki = []
    for el in p.iter(w("r")):
        szulo = el.getparent()
        if szulo.tag == w("del"):
            continue
        ki.append((el, szulo.tag))
    return ki


def kettevag(r, poz):
    """A futast a poz. karakternel ketteosztja (egyetlen w:t-s futasra)."""
    ts = r.findall(w("t"))
    if len(ts) != 1:
        raise ValueError("tobb w:t egy futasban")
    t = ts[0].text or ""
    if poz <= 0 or poz >= len(t):
        return r, None
    masodik = copy.deepcopy(r)
    ts[0].text = t[:poz]
    ts[0].set(XML_SPACE, "preserve")
    t2 = masodik.find(w("t"))
    t2.text = t[poz:]
    t2.set(XML_SPACE, "preserve")
    r.addnext(masodik)
    return r, masodik


def csere(p, regi, uj, szerzo, datum, azon):
    teljes = "".join(futas_szoveg(r) for r, _ in bekezdes_futasok(p))
    db = teljes.count(regi)
    if db != 1:
        return f"a reszlet {db}x szerepel"
    eleje = teljes.index(regi)
    vege = eleje + len(regi)
    # vagas a ket hataron (elobb a vegen, hogy az eleje indexei ne csusszanak)
    for hatar in (vege, eleje):
        poz = 0
        for r, _ in bekezdes_futasok(p):
            h = len(futas_szoveg(r))
            if poz < hatar < poz + h:
                kettevag(r, hatar - poz)
                break
            poz += h
    erintett, poz = [], 0
    for r, szulo in bekezdes_futasok(p):
        h = len(futas_szoveg(r))
        if h and poz >= eleje and poz + h <= vege:
            erintett.append((r, szulo))
        poz += h
    if not erintett or "".join(futas_szoveg(r) for r, _ in erintett) != regi:
        return "a futasok nem fedik pontosan a reszletet"
    def sajat_ins(e):
        return e.tag == w("ins") and e.get(w("author")) == szerzo

    for r, s in erintett:
        if s not in (w("p"), w("hyperlink")) and not sajat_ins(r.getparent()):
            return "a reszlet mas szerzo kovetett valtoztatasan belul van"
    rpr = erintett[0][0].find(w("rPr"))

    def uj_futas():
        ur = etree.Element(w("r"))
        if rpr is not None:
            ur.append(copy.deepcopy(rpr))
        ut = etree.SubElement(ur, w("t"))
        ut.text = uj
        ut.set(XML_SPACE, "preserve")
        return ur

    # az uj szoveg kulon w:ins-kent az utolso erintett futas utan kerul. Ha az
    # egy korabbi (meg el nem fogadott) beszurason belul van, azt a beszurast
    # ott kettevagjuk (a darabok megtartjak a szerzot es a datumot), es az uj
    # w:ins a ket darab koze kerul - igy a korabbi beszuras szovege valtozatlan.
    utolso = erintett[-1][0]
    beszuras = None
    if uj:
        beszuras = etree.Element(w("ins"))
        beszuras.set(w("id"), str(azon + 1))
        beszuras.set(w("author"), szerzo)
        beszuras.set(w("date"), datum)
        beszuras.append(uj_futas())
        szulo = utolso.getparent()
        if sajat_ins(szulo):
            maradek = list(utolso.itersiblings())
            if maradek:
                masodik = etree.Element(w("ins"), dict(szulo.attrib))
                masodik.set(w("id"), str(azon + 250))
                for e in maradek:
                    masodik.append(e)
                szulo.addnext(masodik)
            szulo.addnext(beszuras)
        else:
            utolso.addnext(beszuras)
    # torles: az eredeti szoveg w:del-be kerul; egy korabbi beszurason belul a
    # w:del a beszurasba agyazva (a korabbi beszuras "elutasitasa")
    for k, (r, _) in enumerate(erintett):
        torles = etree.Element(w("del"))
        torles.set(w("id"), str(azon + 2 + k))
        torles.set(w("author"), szerzo)
        torles.set(w("date"), datum)
        r.addprevious(torles)
        for t in r.findall(w("t")):
            t.tag = w("delText")
            t.set(XML_SPACE, "preserve")
        torles.append(r)
    return None


def valtozas(tag, szerzo, datum, azon):
    e = etree.Element(w(tag))
    e.set(w("id"), str(azon)); e.set(w("author"), szerzo); e.set(w("date"), datum)
    return e


def bekezdesjel_torol(p, szerzo, datum, azon):
    """A bekezdesjel torlese: w:pPr/w:rPr elejere egy w:del."""
    ppr = p.find(w("pPr"))
    if ppr is None:
        ppr = etree.Element(w("pPr"))
        p.insert(0, ppr)
    rpr = ppr.find(w("rPr"))
    if rpr is None:
        rpr = etree.SubElement(ppr, w("rPr"))
    rpr.insert(0, valtozas("del", szerzo, datum, azon))


def futasok_torol(p, szerzo, datum, azon):
    """A bekezdes minden (meg nem torolt) futasat w:del-be teszi. Visszaadja a
    hasznalt azonositok szamat; ha egy futas mas kovetett valtoztatasban van, hibat ad."""
    db = 0
    for r, szulo in bekezdes_futasok(p):
        if szulo not in (w("p"), w("hyperlink")):
            raise ValueError("a bekezdesben kovetett valtoztatas van")
        torles = valtozas("del", szerzo, datum, azon + db)
        r.addprevious(torles)
        for t in r.findall(w("t")):
            t.tag = w("delText")
            t.set(XML_SPACE, "preserve")
        for t in r.findall(w("instrText")):
            t.tag = w("delInstrText")
        torles.append(r)
        db += 1
    return db


def torol_bekezdes(p, szerzo, datum, azon):
    db = futasok_torol(p, szerzo, datum, azon)
    bekezdesjel_torol(p, szerzo, datum, azon + db)
    return db + 1


def torol_tabla(tbl, szerzo, datum, azon):
    db = 0
    for tr in tbl.iterchildren(w("tr")):
        trpr = tr.find(w("trPr"))
        if trpr is None:
            trpr = etree.Element(w("trPr"))
            elotte = tr.find(w("tblPrEx"))
            if elotte is not None:
                elotte.addnext(trpr)
            else:
                tr.insert(0, trpr)
        trpr.append(valtozas("del", szerzo, datum, azon + db))
        db += 1
        for p in tr.iter(w("p")):
            db += futasok_torol(p, szerzo, datum, azon + db)
    return db


def elfogadott_nezet(doc):
    """Az elfogadott nezet szovegei (bekezdesenkent), a dokumentum masolatan."""
    d = copy.deepcopy(doc)
    for e in list(d.iter(w("del"))):
        szulo = e.getparent()
        if szulo.tag == w("rPr") and szulo.getparent().tag == w("pPr"):
            continue                       # bekezdesjel-torles: lent kezeljuk
        if szulo.tag == w("trPr"):
            continue
        szulo.remove(e)
    for e in list(d.iter(w("ins"))):
        szulo = e.getparent()
        if szulo.tag == w("rPr"):
            szulo.remove(e)
            continue
        for gy in list(e):
            e.addprevious(gy)
        szulo.remove(e)
    for tr in list(d.iter(w("tr"))):
        if tr.find(f"{w('trPr')}/{w('del')}") is not None:
            tr.getparent().remove(tr)
    for tbl in list(d.iter(w("tbl"))):
        if tbl.find(w("tr")) is None:
            tbl.getparent().remove(tbl)
    maradt = []
    for p in list(d.iter(w("p"))):
        if p.find(f"{w('pPr')}/{w('rPr')}/{w('del')}") is not None:
            if p.find(f".//{w('t')}") is not None or p.find(f".//{w('drawing')}") is not None:
                maradt.append(p)           # osszeolvadna a kovetkezovel
            p.getparent().remove(p)
    return ["".join(t.text or "" for t in p.iter(w("t"))) for p in d.iter(w("p"))], len(maradt)


STILUS = {"torzs": fesules.TORZS, "lista": fesules.LISTA, "hivatkozas": fesules.HIV}


def mezo_futasok(utasitas, helyorzo):
    """Word-mezo futasai; a w:dirty miatt a Word megnyitaskor frissiti."""
    def fld(tipus, dirty=False):
        r = etree.Element(w("r"))
        c = etree.SubElement(r, w("fldChar"))
        c.set(w("fldCharType"), tipus)
        if dirty:
            c.set(w("dirty"), "true")
        return r
    ur = etree.Element(w("r"))
    it = etree.SubElement(ur, w("instrText"))
    it.text = f" {utasitas} "
    it.set(XML_SPACE, "preserve")
    return [fld("begin", True), ur, fld("separate"), fesules.futas(helyorzo), fld("end")]


def uj_bekezdes(doc, stilus, szoveg, szerzo, datum, azon, u=None):
    u = u or {}
    if stilus == "oldaltores":
        ppr = etree.Element(w("pPr"))
        futasok = [etree.Element(w("r"))]
        etree.SubElement(futasok[0], w("br")).set(w("type"), "page")
    elif stilus.startswith("Heading"):
        minta = next(p for p in doc.iter(w("p"))
                     if p.find(f"{w('pPr')}/{w('pStyle')}") is not None
                     and p.find(f"{w('pPr')}/{w('pStyle')}").get(w("val")) == stilus)
        ppr = copy.deepcopy(minta.find(w("pPr")))
        futasok = [fesules.futas(szoveg)]
    elif stilus == "felirat":
        ppr = fesules.ppr(**fesules.FELIRAT)
        futasok = fesules.futasok(szoveg, {"b": True, "sz": 22})
    elif stilus == "forras":
        ppr = fesules.ppr(**fesules.FORRAS)
        futasok = fesules.futasok(szoveg, {"i": True, "sz": 20})
    elif stilus == "kozep":
        ppr = fesules.ppr(spacing={"before": u.get("elotte", 0), "after": u.get("utana", 240)}, jc="center")
        futasok = fesules.futasok(szoveg, {"b": u.get("felkover", False), "sz": u.get("meret", 12) * 2})
    elif stilus == "felkover":
        ppr = fesules.ppr(spacing={"before": 240, "after": 120}, keep_next=True)
        futasok = fesules.futasok(szoveg, {"b": True, "sz": 28})
    elif stilus == "szakasztores":
        ppr = etree.Element(w("pPr"))
        futasok = []
    elif stilus == "mezo":
        ppr = fesules.ppr(**fesules.TORZS)
        futasok = mezo_futasok(u["utasitas"], szoveg)
    else:
        ppr = fesules.ppr(**STILUS[stilus])
        futasok = fesules.futasok(szoveg)
        if stilus == "lista":
            futasok = [fesules.futas("–"), etree.Element(w("r"))] + futasok
            futasok[1].append(etree.Element(w("tab")))
    rpr = ppr.find(w("rPr"))
    if rpr is None:
        rpr = etree.SubElement(ppr, w("rPr"))
    jel = etree.Element(w("ins"))
    jel.set(w("id"), str(azon)); jel.set(w("author"), szerzo); jel.set(w("date"), datum)
    rpr.insert(0, jel)
    if stilus == "szakasztores":
        szak = copy.deepcopy(doc.find(w("body")).find(w("sectPr")))
        for e in szak.findall(w("footerReference")) + szak.findall(w("headerReference")):
            szak.remove(e)
        ppr.append(szak)
    p = etree.Element(w("p"))
    p.append(ppr)
    if futasok:
        ins = etree.SubElement(p, w("ins"))
        ins.set(w("id"), str(azon + 1)); ins.set(w("author"), szerzo); ins.set(w("date"), datum)
        for r in futasok:
            ins.append(r)
    return p


def uj_abra(doc, reszek, u, szerzo, datum, azon):
    """A PNG bekerul a csomagba, es egy kovetett beszuras hivatkozik ra."""
    utvonal = Path(u["kep"])
    adat = utvonal.read_bytes()
    szel, mag = fesules.png_meret(adat)
    nev = f"uj_{utvonal.name}"
    if f"word/media/{nev}" in reszek:
        sys.exit(f"Mar letezik: word/media/{nev}")
    reszek[f"word/media/{nev}"] = adat
    rels = etree.fromstring(reszek["word/_rels/document.xml.rels"])
    rid = f"rIdUjKep{len(rels) + 1}"
    etree.SubElement(rels, "{http://schemas.openxmlformats.org/package/2006/relationships}Relationship",
                     Id=rid, Type=fesules.R_NS + "/image", Target=f"media/{nev}")
    reszek["word/_rels/document.xml.rels"] = etree.tostring(rels, xml_declaration=True, encoding="UTF-8", standalone=True)
    minta = next(p for p in doc.iter(w("p")) if p.find(f".//{w('drawing')}") is not None
                 and p.find(w("ins")) is None)
    docpr = 20000 + azon % 40000
    p = fesules.abra_bekezdes(minta, rid, nev, docpr, szel, mag)
    for e in p.iter():                          # a minta Word-azonositoi nem duplikalodhatnak
        for k in list(e.attrib):
            if k.endswith(("}paraId", "}textId", "}anchorId", "}editId")):
                del e.attrib[k]
    ppr = p.find(w("pPr"))
    rpr = ppr.find(w("rPr"))
    if rpr is None:
        rpr = etree.SubElement(ppr, w("rPr"))
    rpr.insert(0, valtozas("ins", szerzo, datum, azon))
    ins = valtozas("ins", szerzo, datum, azon + 1)
    for r in p.findall(w("r")):
        ins.append(r)
    p.append(ins)
    return p


def uj_tabla(doc, sorok, szerzo, datum, azon):
    """Markdown-tablazat, minden sora es cellabekezdese kovetett beszuras.
    Visszaadja a tablazatot es a felhasznalt azonositok szamat."""
    minta = next(doc.iter(w("tbl"))).find(w("tblPr"))
    tbl = fesules.tablazat(sorok, minta)
    db = 0
    for tr in tbl.findall(w("tr")):
        trpr = tr.find(w("trPr"))
        if trpr is None:
            trpr = etree.Element(w("trPr"))
            tr.insert(0, trpr)
        trpr.append(valtozas("ins", szerzo, datum, azon + db))
        db += 1
        for p in tr.iter(w("p")):
            p.find(f"{w('pPr')}/{w('rPr')}").insert(0, valtozas("ins", szerzo, datum, azon + db))
            ins = valtozas("ins", szerzo, datum, azon + db + 1)
            db += 2
            for r in p.findall(w("r")):
                ins.append(r)
            p.append(ins)
    return tbl, db


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("valtozasok")
    ap.add_argument("be")
    ap.add_argument("ki")
    ap.add_argument("--szerzo", default="Attila Balla")
    args = ap.parse_args()

    bemenet = json.load(open(args.valtozasok, encoding="utf-8"))
    valt = bemenet if isinstance(bemenet, list) else bemenet.get("valtozasok", [])
    ujak = [] if isinstance(bemenet, list) else bemenet.get("uj_bekezdesek", [])
    with zipfile.ZipFile(args.be) as z:
        reszek = {n: z.read(n) for n in z.namelist()}
    doc = etree.fromstring(reszek["word/document.xml"])
    bekezdesek = list(doc.iter(w("p")))
    datum = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    azon = 1 + max([int(e.get(w("id"))) for e in doc.iter(w("ins"), w("del")) if e.get(w("id"))] + [0])
    azon = max(azon, 10000)

    elvart = {}
    kimaradt, kesz = [], 0
    by_id = defaultdict(list)
    for v in valt:
        by_id[v["id"]].append(v)
    for pid, vk in sorted(by_id.items()):
        if pid >= len(bekezdesek):
            kimaradt.append((pid, vk[0]["regi"], "nincs ilyen bekezdes"))
            continue
        p = bekezdesek[pid]
        szoveg = "".join(futas_szoveg(r) for r, _ in bekezdes_futasok(p))
        cel = szoveg
        for v in vk:
            hiba = csere(p, v["regi"], v["uj"], args.szerzo, datum, azon)
            azon += 500
            if hiba:
                kimaradt.append((pid, v["regi"], hiba))
            else:
                cel = cel.replace(v["regi"], v["uj"], 1)
                kesz += 1
        elvart[pid] = cel

    # ellenorzes: az elfogadott nezet pontosan a cserek eredmenye
    rossz = []
    for pid, cel in elvart.items():
        most = "".join(futas_szoveg(r) for r, _ in bekezdes_futasok(bekezdesek[pid]))
        if most != cel:
            rossz.append(pid)
    # teljes torlesek (a cserek utan; ugyanaz a bekezdes nem lehet csere es torles is)
    torolt_b = [] if isinstance(bemenet, list) else bemenet.get("torolt_bekezdesek", [])
    torolt_t = [] if isinstance(bemenet, list) else bemenet.get("torolt_tablak", [])
    utkozes = sorted(set(torolt_b) & set(elvart))
    if utkozes:
        sys.exit(f"HIBA: csere es torles ugyanabban a bekezdesben: {utkozes}")
    torles_kesz, torles_hiba = 0, []
    for pid in torolt_b:
        try:
            azon += torol_bekezdes(bekezdesek[pid], args.szerzo, datum, azon) + 1
            torles_kesz += 1
        except (IndexError, ValueError) as e:
            torles_hiba.append((pid, str(e)))
    tabla_kesz = 0
    for pid in torolt_t:
        tbl = next((a for a in bekezdesek[pid].iterancestors() if a.tag == w("tbl")), None)
        if tbl is None:
            torles_hiba.append((pid, "nem tablazatban van"))
            continue
        try:
            azon += torol_tabla(tbl, args.szerzo, datum, azon) + 1
            tabla_kesz += 1
        except ValueError as e:
            torles_hiba.append((pid, str(e)))

    # uj bekezdesek (a cserek utan; az elemhivatkozasok a beszurastol nem csusznak el)
    body = doc.find(w("body"))
    beszurva, rossz_hely = 0, []
    csop = defaultdict(list)
    for u in ujak:
        csop[("utan", u["utan_id"]) if "utan_id" in u else ("elott", u["elott_id"])].append(u)
    for (irany, uid), us in csop.items():
        if uid >= len(bekezdesek) or bekezdesek[uid].getparent() is not body:
            rossz_hely.append(uid)
            continue
        horgony = bekezdesek[uid]
        for u in sorted(us, key=lambda x: x["sorrend"]):
            if u["stilus"] == "abra":
                p = uj_abra(doc, reszek, u, args.szerzo, datum, azon)
                azon += 2
            elif u["stilus"] == "tabla":
                p, db = uj_tabla(doc, u["sorok"], args.szerzo, datum, azon)
                azon += db
            else:
                p = uj_bekezdes(doc, u["stilus"], u.get("szoveg", ""), args.szerzo, datum, azon, u)
                azon += 2
            if irany == "utan":
                horgony.addnext(p)
                horgony = p
            else:
                horgony.addprevious(p)
            beszurva += 1
    reszek["word/document.xml"] = etree.tostring(doc, xml_declaration=True, encoding="UTF-8", standalone=True)
    with zipfile.ZipFile(args.ki, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", reszek.pop("[Content_Types].xml"))
        for n, a in reszek.items():
            z.writestr(n, a)

    print(f"Valtoztatas: {len(valt)}, beirva: {kesz}, kimaradt: {len(kimaradt)}; "
          f"erintett bekezdes: {len(elvart)}; elfogadott nezet egyezik: {len(elvart) - len(rossz)}/{len(elvart)}")
    print(f"Uj bekezdes: {len(ujak)}, beszurva: {beszurva}"
          + (f"; NEM torzs-szintu vagy hibas utan_id: {rossz_hely}" if rossz_hely else ""))
    for pid, regi, ok in kimaradt:
        print(f"  KIMARADT [{pid}] {ok}: {regi[:80]!r}")
    if torolt_b or torolt_t:
        print(f"Torolt bekezdes: {torles_kesz}/{len(torolt_b)}, torolt tablazat: {tabla_kesz}/{len(torolt_t)}")
        for pid, ok in torles_hiba:
            print(f"  TORLES KIMARADT [{pid}] {ok}")
    nezet, osszeolvad = elfogadott_nezet(doc)
    print(f"Elfogadott nezet: {len(nezet)} bekezdes (bemenet: {len(bekezdesek)} w:p)"
          + (f"; FIGYELEM: {osszeolvad} torolt jelu bekezdes tartalma megmaradna" if osszeolvad else ""))
    if rossz:
        print(f"  ELTERES az elfogadott nezetben: {rossz}")
        sys.exit(1)


if __name__ == "__main__":
    main()
