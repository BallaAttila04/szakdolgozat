"""
A kesz docx ellenorzese: zip-epseg, egyedi valtozas-azonositok, kepek es kapcsolatok,
es az elfogadott nezeten a cimsorok, a belso hivatkozasok, a feliratok, a jelolesek,
a tiltott szavak es a hivatkozasi lista.

Hasznalat:
    python v4_ellenorzes.py fajl.docx ["tovabbi|tiltott|szavak"]
"""

import copy
import re
import sys
import zipfile
from collections import Counter
from pathlib import Path

from lxml import etree

sys.path.insert(0, str(Path(__file__).resolve().parent))
import javitas_beiras as jb  # noqa: E402

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except AttributeError:
    pass

w = jb.w
TILTOTT = ["Kiel", "Rendsburg", "placebo", "Rader", "Implenia", "Nord-Ostsee"]
# csak a nyilatkozatban lehet; a termekneveket a harmadik parancssori argumentum adja hozza
MI_ALAP = r"nyelvi modell|mesterséges intelligencia|generatív|MI-"
MI_SZAVAK = re.compile(r"\b(" + MI_ALAP + (("|" + sys.argv[2]) if len(sys.argv) > 2 else "") + ")", re.I)
JELOLES = re.compile(r"\[(NEM ELLENŐRIZVE|NEM VIZSGÁLT|NEM ELVÉGZETT|JAVASOLT|FOLYAMATBAN|FORRÁS PÓTLANDÓ|DÖNTÉS)")


def nezet_stilussal(doc):
    d = copy.deepcopy(doc)
    for e in list(d.iter(w("del"))):
        sz = e.getparent()
        if (sz.tag == w("rPr") and sz.getparent().tag == w("pPr")) or sz.tag == w("trPr"):
            continue
        sz.remove(e)
    for tr in list(d.iter(w("tr"))):
        if tr.find(f"{w('trPr')}/{w('del')}") is not None:
            tr.getparent().remove(tr)
    for p in list(d.iter(w("p"))):
        if p.find(f"{w('pPr')}/{w('rPr')}/{w('del')}") is not None:
            p.getparent().remove(p)
    ki = []
    for p in d.iter(w("p")):
        s = p.find(f"{w('pPr')}/{w('pStyle')}")
        ki.append((s.get(w("val")) if s is not None else "", "".join(t.text or "" for t in p.iter(w("t")))))
    return ki


def main():
    fajl = sys.argv[1]
    z = zipfile.ZipFile(fajl)
    print("zip teszt:", z.testzip())
    doc = etree.fromstring(z.read("word/document.xml"))
    for n in z.namelist():
        if n.endswith((".xml", ".rels")):
            etree.fromstring(z.read(n))
    hibak = []

    ids = [e.get(w("id")) for e in doc.iter(w("ins"), w("del"))]
    d = Counter(ids)
    print(f"valtozas-azonosito: {len(ids)}, egyedi: {len(d)}")
    if len(ids) != len(d):
        hibak.append(f"duplikalt azonosito: {[k for k, v in d.items() if v > 1][:5]}")
    print("szerzo:", sorted({e.get(w("author")) for e in doc.iter(w("ins"), w("del"))}))
    t_del = [t for t in doc.iter(w("t")) if any(a.tag == w("del") for a in t.iterancestors())]
    dt_ki = [t for t in doc.iter(w("delText")) if not any(a.tag == w("del") for a in t.iterancestors())]
    print(f"w:t torlesben: {len(t_del)}; delText torlesen kivul: {len(dt_ki)}")
    if t_del or dt_ki:
        hibak.append("hibas torles")
    print("szakaszok (sectPr):", len(list(doc.iter(w("sectPr")))), "; mezok:",
          Counter(re.split(r"\s+", (i.text or "").strip())[0] for i in doc.iter(w("instrText"))))

    rels = etree.fromstring(z.read("word/_rels/document.xml.rels"))
    rel = {r.get("Id"): r.get("Target") for r in rels}
    R = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}embed"
    blip = [e.get(R) for e in doc.iter("{http://schemas.openxmlformats.org/drawingml/2006/main}blip")]
    hianyzik = [b for b in blip if b not in rel or "word/" + rel[b] not in z.namelist()]
    print(f"abrak: {len(blip)}, hibas kapcsolat: {len(hianyzik)}")
    if hianyzik:
        hibak.append(f"kep: {hianyzik}")
    docpr = [e.get("id") for e in doc.iter("{http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing}docPr")]
    if len(docpr) != len(set(docpr)):
        hibak.append(f"duplikalt docPr: {docpr}")

    nezet = nezet_stilussal(doc)
    print(f"elfogadott nezet: {len(nezet)} bekezdes")
    cimek = [(s, t) for s, t in nezet if s.startswith("Heading")]
    alfej = set()
    print("cimsorok szama:", Counter(s for s, _ in cimek))
    for s, t in cimek:
        m = re.match(r"(\d+(?:\.\d+)*)\.? ", t)
        if m:
            alfej.add(m.group(1))
    # a szamozas folytonossaga szintenkent
    elozo = {}
    for s, t in cimek:
        m = re.match(r"(\d+(?:\.\d+)*)\.? ", t)
        if not m:
            continue
        r = tuple(int(x) for x in m.group(1).split("."))
        kulcs = r[:-1]
        if elozo.get(kulcs, 0) + 1 != r[-1]:
            hibak.append(f"cimszam-hezag: {t[:40]}")
        elozo[kulcs] = r[-1]

    h_kezd = next(i for i, (s, t) in enumerate(nezet) if t == "Hivatkozások")
    m_kezd = next(i for i, (s, t) in enumerate(nezet) if t == "Melléklet")
    ny_kezd = next(i for i, (s, t) in enumerate(nezet) if t.startswith("Nyilatkozat a generatív"))
    ny_veg = next(i for i, (s, t) in enumerate(nezet) if t == "Bevezetés")

    rossz = []
    for i, (s, t) in enumerate(nezet):
        if s.startswith("Heading") or h_kezd <= i or i < ny_veg:
            continue
        for m in re.finditer(r"(?<![\d.,])(\d\.\d(?:\.\d)?)(?![\d,])", t):
            if m.group(1) not in alfej:
                rossz.append((m.group(1), t[max(0, m.start() - 30):m.end() + 15]))
        for m in re.finditer(r"(?<![\d.])(\d)\. fejezet", t):
            if m.group(1) not in alfej:
                rossz.append((m.group(0), ""))
    print(f"belso hivatkozas nem letezo alfejezetre: {len(rossz)}")
    for a, b in rossz:
        print(f"   {a}: …{b}…")

    tab = [int(m.group(1)) for s, t in nezet if (m := re.match(r"(\d+)\. táblázat:", t))]
    abr = [int(m.group(1)) for s, t in nezet if (m := re.match(r"(\d+)\. ábra:", t))]
    print(f"tablazatfeliratok: {tab}\nabrafeliratok: {abr}")
    if tab != list(range(1, len(tab) + 1)) or abr != list(range(1, len(abr) + 1)):
        hibak.append("felirat-hezag")
    for i, (s, t) in enumerate(nezet):
        if re.match(r"\d+\. (táblázat|ábra):", t) or i >= h_kezd:
            continue
        for m in re.finditer(r"(\d+)\. (táblázat|ábr)", t):
            n = int(m.group(1))
            if (m.group(2) == "ábr" and n not in abr) or (m.group(2) == "táblázat" and n not in tab):
                hibak.append(f"nincs ilyen felirat: {t[max(0, m.start() - 30):m.end() + 10]}")
    nev = re.findall(r"\b[Aa] (?:[15]\d?\.|5\d\.\d?)(?= )|\b[Aa]z (?:[2-4]|[6-9]|[1-4]\d)\. ", " ".join(t for _, t in nezet[ny_veg:h_kezd]))
    print("nevelo-gyanu:", Counter(nev).most_common(12))

    for kw in TILTOTT:
        hol = [i for i, (_, t) in enumerate(nezet) if kw in t]
        print(f"{kw}: {len(hol)}")
        if hol:
            hibak.append(f"tiltott szo: {kw} {[nezet[i][1][:60] for i in hol[:3]]}")
    mi = [(i, m.group(0)) for i, (_, t) in enumerate(nezet) for m in MI_SZAVAK.finditer(t)
          if not (ny_kezd <= i < ny_veg)]
    print("MI-utalas a nyilatkozaton kivul:", [(i, x, nezet[i][1][:80]) for i, x in mi])
    if mi:
        hibak.append("MI-utalas a nyilatkozaton kivul")

    jel = Counter()
    for _, t in nezet:
        for m in JELOLES.finditer(t):
            jel[m.group(1)] += 1
    print("jelolesek az elfogadott nezetben:", dict(jel))
    for s, t in nezet:
        for m in re.finditer(r"\[(NEM ELLENŐRIZVE|FOLYAMATBAN)[^\]]*\]", t):
            print("  nyitva:", m.group(0)[:110])

    lista = [t for s, t in nezet[h_kezd + 1:m_kezd] if t.strip()]
    print(f"hivatkozasi tetelek: {len(lista)}")
    kulcs = [re.sub(r"[^a-z]", "", (x.split(".")[0].split(",")[0]).lower().translate(str.maketrans("áéíóöőúüűø", "aeiooouuuo")))[:12] for x in lista]
    rend = [(a, b) for a, b in zip(kulcs, kulcs[1:]) if a > b]
    print("betureud-gyanu:", rend[:12])
    szoveg = " ".join(t for _, t in nezet[ny_veg:h_kezd])
    for minta, tetel in ((r"Few \(2006a\)", "Few, S. (2006a"), (r"Few, 2006b", "Few, S. (2006b"), (r"Wieringa \(2018\)|Wieringa, 2018", "Wieringa, R. J. (2018"),
                         (r"JMIC, 2026|\[JMIC\], 2026", "Joint Maritime Information Center. (2026"), (r"IMF PortWatch, 2026", "IMF PortWatch. (2026"),
                         (r"Holm, 1979", "Holm, S. (1979"), (r"Bloom, 1995", "Bloom, H. S. (1995"), (r"Künsch, 1989", "Künsch, H. R. (1989"),
                         (r"Schuler, 2026", "Schuler, M. (2026"), (r"Wass & Longley, 2025", "Wass, S."), (r"European Commission, 2026", "European Commission. (2026"),
                         (r"Danish Maritime Authority, 2026", "Danish Maritime Authority. (2026"), (r"datasets, é", "datasets. (é. n.)"),
                         (r"Harati-Mokhtari, 2007", "Harati-Mokhtari, A. (2007"), (r"Cohen, 1960", "Cohen, J. (1960"),
                         (r"NIST/SEMATECH, é", "NIST/SEMATECH. (é. n.)"), (r"Oxford Programme", "Oxford Programme"), (r"Prat et al\., 2014|Prat et al\. \(2014\)", "Prat, N., Comyn-Wattiau, I., & Akoka, J. (2014"),
                         (r"Meta Platforms, é", "Meta Platforms. (é. n.)")):
        van_sz, van_l = bool(re.search(minta, szoveg)), any(x.startswith(tetel) for x in lista)
        if not (van_sz and van_l):
            hibak.append(f"hivatkozas-par: {minta}: szoveg {van_sz}, lista {van_l}")
    for m in ("é. n.-a", "é. n.-b", "é. n.-c", "é. n.-d"):
        print(f"GitHub {m}:", szoveg.count(f"GitHub, {m}") + szoveg.count(f"; {m}"))
    print("\nHIBAK:", hibak if hibak else "nincs")
    sys.exit(1 if hibak else 0)


if __name__ == "__main__":
    main()
