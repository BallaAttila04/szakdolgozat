"""
A javitas_beiras.py tesztje szintetikus docx-en: csere, teljes bekezdes- es
tablazattorles, uj Heading1 + torzs + oldaltores beszurasa, es az elfogadott
nezet osszevetese a vart szoveggel. A kimenet ideiglenes mappaba kerul.

Hasznalat:
    python teszt_javitas_beiras.py
"""

import json
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

from lxml import etree

sys.path.insert(0, str(Path(__file__).resolve().parent))
import javitas_beiras as jb  # noqa: E402

W_NS = jb.W_NS
TIPUSOK = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
           '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
           '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
           '<Default Extension="xml" ContentType="application/xml"/>'
           '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-'
           'officedocument.wordprocessingml.document.main+xml"/></Types>')
RELS = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/'
        'relationships/officeDocument" Target="word/document.xml"/></Relationships>')


def p(szoveg, stilus=None):
    ppr = f'<w:pPr><w:pStyle w:val="{stilus}"/></w:pPr>' if stilus else ""
    return f'<w:p>{ppr}<w:r><w:t xml:space="preserve">{szoveg}</w:t></w:r></w:p>'


DOKUMENTUM = (f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:document xmlns:w="{W_NS}"><w:body>'
              + p("1. Fejezet", "Heading1")                      # 0
              + p("Alfa beta gamma.")                            # 1
              + '<w:p><w:r><w:br w:type="page"/></w:r></w:p>'    # 2
              + p("2. Fejezet", "Heading1")                      # 3
              + p("2.1 Torlendo", "Heading2")                    # 4
              + '<w:p><w:r><w:t>Torlendo </w:t></w:r><w:r><w:rPr><w:b/></w:rPr><w:t>kovér</w:t></w:r></w:p>'  # 5
              + '<w:tbl><w:tblPr/><w:tr><w:tc>' + p("a1") + '</w:tc><w:tc>' + p("b1") + '</w:tc></w:tr>'
              + '<w:tr><w:tc>' + p("a2") + '</w:tc><w:tc>' + p("b2") + '</w:tc></w:tr></w:tbl>'  # 6-9
              + p("Utolso.")                                     # 10
              + '<w:sectPr/></w:body></w:document>')

VALTOZASOK = {
    "valtozasok": [{"id": 1, "regi": "beta", "uj": "BETA"}],
    "torolt_bekezdesek": [4, 5],
    "torolt_tablak": [8],
    "uj_bekezdesek": [
        {"utan_id": 2, "sorrend": 1, "stilus": "Heading1", "szoveg": "2. Uj fejezet"},
        {"utan_id": 2, "sorrend": 2, "stilus": "torzs", "szoveg": "[FOLYAMATBAN] Helyfoglalo."},
        {"utan_id": 2, "sorrend": 3, "stilus": "oldaltores", "szoveg": ""},
    ],
}

VART = ["1. Fejezet", "Alfa BETA gamma.", "", "2. Uj fejezet", "[FOLYAMATBAN] Helyfoglalo.", "",
        "2. Fejezet", "Utolso."]


def main():
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        be, ki, js = tmp / "be.docx", tmp / "ki.docx", tmp / "v.json"
        with zipfile.ZipFile(be, "w") as z:
            z.writestr("[Content_Types].xml", TIPUSOK)
            z.writestr("_rels/.rels", RELS)
            z.writestr("word/document.xml", DOKUMENTUM)
        js.write_text(json.dumps(VALTOZASOK), encoding="utf-8")
        f = subprocess.run([sys.executable, str(Path(jb.__file__)), str(js), str(be), str(ki)],
                           capture_output=True, text=True, encoding="utf-8")
        print(f.stdout.rstrip())
        if f.returncode:
            print(f.stderr)
            sys.exit("BUKOTT: a szkript hibaval allt le")
        doc = etree.fromstring(zipfile.ZipFile(ki).read("word/document.xml"))
        nezet, osszeolvad = jb.elfogadott_nezet(doc)
        ok = []
        ok.append(("elfogadott nezet = vart", nezet == VART))
        ok.append(("nincs osszeolvado torolt bekezdes", osszeolvad == 0))
        ok.append(("torolt bekezdesjel: 2 bekezdes",
                   sum(1 for q in doc.iter(jb.w("p")) if q.find(f"{jb.w('pPr')}/{jb.w('rPr')}/{jb.w('del')}") is not None) == 2))
        ok.append(("torolt sor: 2", len(doc.findall(f".//{jb.w('trPr')}/{jb.w('del')}")) == 2))
        ok.append(("delText: Torlendo, kovér, a1..b2, beta",
                   sorted(t.text for t in doc.iter(jb.w("delText"))) ==
                   sorted(["2.1 Torlendo", "Torlendo ", "kovér", "a1", "b1", "a2", "b2", "beta"])))
        ok.append(("a felkover formazas a torolt futason megmaradt",
                   any(r.find(f"{jb.w('rPr')}/{jb.w('b')}") is not None for r in doc.iter(jb.w("r"))
                       if r.find(jb.w("delText")) is not None and r.find(jb.w("delText")).text == "kovér")))
        ok.append(("az uj oldaltores kovetett beszuras",
                   any(br.get(jb.w("type")) == "page" and any(a.tag == jb.w("ins") for a in br.iterancestors())
                       for br in doc.iter(jb.w("br")))))
        ids = [e.get(jb.w("id")) for e in doc.iter(jb.w("ins"), jb.w("del"))]
        ok.append(("egyedi valtozas-azonositok", len(ids) == len(set(ids))))
        for nev, v in ok:
            print(f"  {'OK ' if v else 'HIBA'} {nev}")
        if not nezet == VART:
            print("  kapott:", nezet)
        print(f"Teszt: {sum(v for _, v in ok)}/{len(ok)} rendben")
        sys.exit(0 if all(v for _, v in ok) else 1)


if __name__ == "__main__":
    main()
