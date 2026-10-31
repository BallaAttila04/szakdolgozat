"""
Szakirodalmi javaslatok ellenorzese az elsodleges forrassal.

A dolgozat szovegebe csak az a javaslat kerulhet, amelynek forrasat ez a szkript
tenylegesen letoltotte, es a forrasban megtalalta a kert szovegreszt, vagy a
Crossref a megadott bibliografiai adatot adja. Kimenet: egy CSV (azon, url,
statusz, bizonyitek), statusz: igazolt | nem_igazolt | nem_elerheto.

Hasznalat:
    python szakirodalom_ellenorzes.py [--ki munka/szakirodalom_forrascheck.csv]
                                      [--gyorsitotar munka/forrasok]
"""

import argparse
import csv
import hashlib
import io
import json
import re
import sys
import time
import unicodedata
from pathlib import Path
from urllib.parse import quote

import requests

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except AttributeError:
    pass

UA = {"User-Agent": "Mozilla/5.0 (szakdolgozat forrasellenorzes)"}
IDOKORLAT = 45  # mp; a lassu kiadoi oldalaknal ennyi mar eleg

# (azonosito, DOI, kert adatok: ev, kotet, fuzet, oldal, elso szerzo vezetekneve)
DOI = [
    ("Abadi2008", "10.1145/1376616.1376712", "2008", None, None, "967-980", "Abadi"),
    ("Arslanalp2021", "10.5089/9781513593531.001", "2021", None, None, None, "Arslanalp"),
    ("Arslanalp2019", "10.5089/9781513521121.001", "2019", None, None, None, "Arslanalp"),
    ("Birch2007", "10.1016/j.ecolmodel.2007.03.041", "2007", "206", "3-4", "347-359", "Birch"),
    ("Cao2006", "10.1007/s00778-005-0163-7", None, "15", "3", "211-228", "Cao"),
    ("Cohen1960", "10.1177/001316446002000104", "1960", "20", "1", "37-46", "Cohen"),
    ("Guttman1984", "10.1145/602259.602266", "1984", None, None, "47", "Guttman"),
    ("Kunsch1989", "10.1214/aos/1176347265", "1989", "17", "3", "1217-1241", "Kunsch"),
    ("Makris2021", "10.1109/ACCESS.2021.3092948", "2021", "9", None, "92516-92530", "Makris"),
    ("Melnik2010", "10.14778/1920841.1920886", "2010", "3", "1-2", "330-339", "Melnik"),
    ("Paolo2022", "10.52202/068431-2726", "2022", None, None, "37604", "Paolo"),
    ("Trajcevski2006", "10.1145/1140104.1140110", "2006", None, None, "19", "Trajcevski"),
    ("Tu2018", "10.1109/TITS.2017.2724551", "2018", "19", "5", "1559-1582", "Tu"),
    ("Wilkinson2016", "10.1038/sdata.2016.18", "2016", "3", None, None, "Wilkinson"),
    ("Zaharia2016", "10.1145/2934664", "2016", "59", "11", "56-65", "Zaharia"),
    ("Zimanyi2020", "10.1145/3406534", "2020", "45", "4", None, "Zim"),
    ("Otsu1979", "10.1109/TSMC.1979.4310076", "1979", "9", "1", "62-66", "Otsu"),
    ("Bloom1995", "10.1177/0193841X9501900504", "1995", "19", "5", "547-556", "Bloom"),
]

# (azonosito, url, [kotelezo szovegreszek])
OLDAL = [
    ("Apache-fileformat", "https://parquet.apache.org/docs/file-format/", ["column chunk start locations"]),
    ("Apache-pageindex", "https://parquet.apache.org/docs/file-format/pageindex/", ["statistics are stored for columnchunks"]),
    ("GitHub-limits", "https://docs.github.com/en/actions/reference/limits", ["6 hours of execution time"]),
    ("GitHub-events", "https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows",
     ["can be delayed during periods of high loads", "may be dropped"]),
    ("NIST-cusum", "https://www.itl.nist.gov/div898/handbook/pmc/section3/pmc323.htm", ["rule of thumb", "montgomery"]),
    ("Prat2014", "https://aisel.aisnet.org/pacis2014/23/", ["artifact evaluation in information systems design-science research"]),
    ("OPSIS", "https://opsis.eci.ox.ac.uk/post/2023-11-15-portwatch/", ["portwatch", "verschuur"]),
    ("RFC8878", "https://www.rfc-editor.org/rfc/rfc8878.txt", ["y. collet", "m. kucherawy, ed."]),
    ("Spark420", "https://spark.apache.org/docs/4.2.0/", ["spark 4.2.0"]),
    ("DuckDB15", "https://duckdb.org/docs/1.5/data/parquet/overview", ["parquet"]),
    ("ITU-M585", "https://www.itu.int/rec/R-REC-M.585/en", ["m.585-10", "m.585-6"]),
    ("Few2006-pitfalls", "https://www.perceptualedge.com/articles/Whitepapers/Common_Pitfalls.pdf",
     ["common pitfalls in dashboard design", "exceeding the boundaries of a single screen"]),
    ("HaratiMokhtari-phd", "https://researchonline.ljmu.ac.uk/id/eprint/5837/1/438839.pdf", ["automatic identification system"]),
    ("Kiersztyn2025", "https://arxiv.org/pdf/2501.03358", ["102 knots", "moored"]),
    ("McSherry2015", "https://www.usenix.org/system/files/conference/hotos15/hotos15-paper-mcsherry.pdf",
     ["configuration that outperforms a single thread"]),
    ("Armbrust2021", "https://www.cidrdb.org/cidr2021/papers/cidr2021_paper17.pdf", ["we define a lakehouse"]),
    ("Wilkinson-fulltext", "https://www.ebi.ac.uk/europepmc/webservices/rest/PMC4792175/fullTextXML",
     ["detailed provenance", "algorithms, tools, and workflows"]),
    ("Arslanalp2019-abs", "https://api.semanticscholar.org/graph/v1/paper/DOI:10.5089/9781513521121.001?fields=title,abstract",
     ["appropriate filtering"]),
    ("Meyers2022-abs", "https://api.semanticscholar.org/graph/v1/paper/DOI:10.1016/j.oceaneng.2022.112367?fields=title,abstract",
     ["ship draft, beam, and class"]),
    ("Tu2018-abs", "https://api.semanticscholar.org/graph/v1/paper/DOI:10.1109/TITS.2017.2724551?fields=title,abstract",
     ["traffic anomaly detection, route estimation, collision prediction, and path planning"]),
    ("Wieringa-foliak", "https://pros.webs.upv.es/site/2018/11/08/roel-wieringa-seminar-desing-science-applied-to-phd-research-22-november-2018/design-science-methodology",
     ["treatment = interaction between artifact and context", "lab experiment", "field experiment", "implementation evaluation (in the field)"]),
    ("Peffers2007", "https://wise.vub.ac.be/sites/default/files/thesis_info/Design_Science_Research_Methodology_2008.pdf",
     ["client/context-centered initiation"]),
    ("Prat2014-dim", "https://aisel.aisnet.org/pacis2014/23/", ["goal, environment, structure, activity, and evolution"]),
    ("PortWatch-meta", "https://www.arcgis.com/sharing/rest/content/items/3da2b9ca97684916b75c4013f95d18ab?f=json",
     ["tracking trade from space"]),
    ("Few2006-konyv", "https://www.perceptualedge.com/articles/Whitepapers/Common_Pitfalls.pdf",
     ["based on a chapter in the new book", "13 most common pitfalls"]),
    ("HaratiMokhtari-szamok", "https://researchonline.ljmu.ac.uk/id/eprint/5837/1/438839.pdf",
     ["out of 94 ships", "sample of 30946 ais transmissions, 49%", "vessel type with 74%", "30% inconsistencies"]),
    ("McSherry-scal", "https://www.usenix.org/system/files/conference/hotos15/hotos15-paper-mcsherry.pdf",
     ["efficient use of resources"]),
    ("Reis-undercurrents", "https://joereis.substack.com/p/the-data-engineering-lifecycle-and",
     ["undercurrents", "security", "data management", "dataops", "orchestration"]),
    ("FPP3", "https://otexts.com/fpp3/", ["forecasting: principles and practice"]),
    ("Soldi2021-50nm", "https://arxiv.org/pdf/2011.11304", ["50 nautical miles"]),
    ("Birch-abs", "https://ideas.repec.org/a/eee/ecomod/v206y2007i3p347-359.html", ["nearest neighbo"]),
    ("Meyers2022", "https://repository.library.noaa.gov/view/noaa/49215", ["ais"]),
    ("Zaharia-cacm", "https://people.eecs.berkeley.edu/~matei/papers/2016/cacm_apache_spark.pdf", ["most active open source"]),
    ("S2", "https://s2geometry.io/devguide/s2cell_hierarchy", ["0 to 30"]),
    ("GregorHevner2013", "https://ailab-ua.github.io/courses/MIS611D/gregor-2013-positioning-presenting-design-science-research.pdf",
     ["improvement: new solutions for known problems", "situated implementation (level 1) as a knowledge contribution",
      "design theories (mid-range and grand theories)"]),
    ("JMIC-001", "https://mscio.eu/media/documents/001_JMIC_Advisory_Note_28_FEB_2026.pdf",
     ["no official closure of the strait of hormuz has been formally"]),
    ("gCaptain-JMIC", "https://gcaptain.com/strait-of-hormuz-traffic-grinds-to-near-halt-as-security-threat-remains-critical-advisory-warns/",
     ["no formal legal closure"]),
    ("EU-20", "https://finance.ec.europa.eu/news/eu-adopts-20th-package-sanctions-against-russia-2026-04-23_en", ["632"]),
    ("DMA-vessels", "https://www.dma.dk/growth-and-framework-conditions/maritime-sanctions/general-information/eu-vessel-designations",
     ["date of application"]),
    ("InsJournal-2025", "https://www.insurancejournal.com/news/international/2025/02/06/810919.htm", ["skagen"]),
    ("UNECE-LOCODE", "https://unece.org/trade/cefact/unlocode-code-list-country-and-territory", ["un/locode"]),
]


def norm(s):
    s = unicodedata.normalize("NFKC", s).replace("­", "").replace("’", "'")
    return re.sub(r"\s+", " ", s).lower()


def letolt(url, tar):
    f = tar / (hashlib.sha1(url.encode()).hexdigest()[:16] + ".txt")
    if f.exists():
        return f.read_text(encoding="utf-8"), "gyorsitotar"
    r = requests.get(url, headers=UA, timeout=IDOKORLAT, allow_redirects=True)
    if r.status_code != 200:
        return None, f"HTTP {r.status_code}"
    if r.content[:4] == b"%PDF":
        import fitz
        with fitz.open(stream=io.BytesIO(r.content), filetype="pdf") as d:
            szoveg = "\n".join(o.get_text() for o in d)
    else:
        szoveg = re.sub(r"<(script|style).*?</\1>", " ", r.text, flags=re.S)
        szoveg = re.sub(r"<[^>]+>", " ", szoveg)
    f.write_text(szoveg, encoding="utf-8")
    return szoveg, "HTTP 200"


def doi_check(azon, doi, ev, kotet, fuzet, oldal, szerzo):
    r = requests.get(f"https://api.crossref.org/works/{quote(doi)}", headers=UA, timeout=IDOKORLAT)
    if r.status_code != 200:
        return "nem_elerheto", f"Crossref HTTP {r.status_code}"
    m = r.json()["message"]
    kapott = {"ev": str((m.get("issued", {}).get("date-parts") or [[None]])[0][0]), "kotet": m.get("volume"),
              "fuzet": m.get("issue"), "oldal": m.get("page"),
              "szerzo": "; ".join(a.get("family", a.get("name", "")) for a in m.get("author", []))[:120],
              "cim": (m.get("title") or [""])[0][:90], "n_szerzo": len(m.get("author", []))}
    hibak = []
    if ev and kapott["ev"] != ev:
        hibak.append(f"ev {kapott['ev']}")
    if kotet and kapott["kotet"] != kotet:
        hibak.append(f"kotet {kapott['kotet']}")
    if fuzet and (kapott["fuzet"] or "").replace("–", "-") != fuzet:
        hibak.append(f"fuzet {kapott['fuzet']}")
    if oldal and oldal not in (kapott["oldal"] or ""):
        hibak.append(f"oldal {kapott['oldal']}")
    ascii_szerzo = unicodedata.normalize("NFKD", kapott["szerzo"]).encode("ascii", "ignore").decode().lower()
    if szerzo and szerzo.lower() not in ascii_szerzo:
        hibak.append(f"szerzo {kapott['szerzo']}")
    return ("nem_igazolt" if hibak else "igazolt"), json.dumps(kapott, ensure_ascii=False) + (" ELTERES: " + ", ".join(hibak) if hibak else "")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    itt = Path(__file__).resolve().parent
    ap.add_argument("--ki", type=Path, default=itt / "munka" / "szakirodalom_forrascheck.csv")
    ap.add_argument("--gyorsitotar", type=Path, default=itt / "munka" / "forrasok")
    args = ap.parse_args()
    args.gyorsitotar.mkdir(parents=True, exist_ok=True)
    sorok = []
    for t in DOI:
        try:
            st, biz = doi_check(*t)
        except requests.RequestException as e:
            st, biz = "nem_elerheto", type(e).__name__
        sorok.append({"azon": t[0], "url": "https://doi.org/" + t[1], "statusz": st, "bizonyitek": biz})
        time.sleep(0.2)
    for azon, url, kell in OLDAL:
        try:
            szoveg, inf = letolt(url, args.gyorsitotar)
        except Exception as e:
            szoveg, inf = None, type(e).__name__
        if szoveg is None:
            sorok.append({"azon": azon, "url": url, "statusz": "nem_elerheto", "bizonyitek": inf})
            continue
        n = norm(szoveg)
        hiany = [k for k in kell if norm(k) not in n]
        sorok.append({"azon": azon, "url": url, "statusz": "nem_igazolt" if hiany else "igazolt",
                      "bizonyitek": f"{inf}; {len(n)} kar.; " + ("hianyzik: " + " | ".join(hiany) if hiany else "megvan: " + " | ".join(kell))})
    with open(args.ki, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["azon", "url", "statusz", "bizonyitek"])
        w.writeheader()
        w.writerows(sorok)
    for s in sorok:
        print(f"{s['statusz']:12} {s['azon']:20} {s['bizonyitek'][:170]}")
    db = {k: sum(s["statusz"] == k for s in sorok) for k in ("igazolt", "nem_igazolt", "nem_elerheto")}
    print(f"Ellenorizve: {len(sorok)} forras; {db}")


if __name__ == "__main__":
    main()
