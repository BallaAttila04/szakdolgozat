"""
Ertesites a monitor jelzeseirol GitHub Issue-val (7d).

A napi futas utan fut. A legutolso feldolgozott nap "szokatlanul magas /
alacsony" jelzeseire issue-t nyit; a GitHub errol e-mailt kuld a repo
gazdajanak, titkos kulcs nem kell (a workflow sajat GITHUB_TOKEN-je eleg).

Duplikacio elleni szabaly: egy sorozat + irany (magas/alacsony) parhoz
egyszerre legfeljebb egy nyitott issue tartozik. Ha a jelzes masnap is
fennall, az issue egy megjegyzest kap (naponta legfeljebb egyet), uj issue
nem nyilik. Ha a sorozat visszaall normalra, az issue megjegyzessel lezarul.

Hasznalat:
    python ertesites.py                 # a workflowban, GH_TOKEN-nel
    python ertesites.py --szaraz        # csak kiirja, mit tenne
    python ertesites.py --teszt         # mesterseges teszt-jelzes (7d teszt)

Fuggoseg: a `gh` parancssori eszkoz (a GitHub-futtaton elore telepitve).
"""

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from utak import KIMENET

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except AttributeError:
    pass

MONITOR = KIMENET / "monitor"
CIMKE = "monitor-jelzes"
FAJLOK = ["jelzesek.csv", "jelzesek_megrakottsag.csv"]
OLDAL = "https://ballaattila04.github.io/szakdolgozat/#monitor"


def gh(*arg, szaraz=False, kimenet=False):
    if szaraz and not kimenet:
        print("  [szaraz] gh " + " ".join(arg))
        return ""
    r = subprocess.run(["gh", *arg], capture_output=True, text=True, encoding="utf-8")
    if r.returncode != 0:
        raise RuntimeError(f"gh {' '.join(arg[:2])}: {r.stderr.strip()}")
    return r.stdout


def cim(sorozat, jelzes, teszt=False):
    return f"[{'Monitor-teszt' if teszt else 'Monitor'}] {sorozat}: {jelzes}"


def aktiv_jelzesek(mappa: Path):
    allapot = json.loads((mappa / "allapot.json").read_text(encoding="utf-8"))
    nap = allapot["utolso_nap"]
    sorok, mind = [], set()
    for f in FAJLOK:
        if not (mappa / f).exists():
            continue
        j = pd.read_csv(mappa / f, dtype={"datum": str})
        mind |= set(j["sorozat"])
        u = j[(j.datum == nap) & j.jelzes.str.startswith("szokatlanul")]
        sorok += u.to_dict("records")
    return nap, sorok, mind


def torzs(r, nap):
    return (f"A napi monitor jelzést adott a(z) **{nap}** napra.\n\n"
            f"| sorozat | érték | alapszint (4 hét azonos napja) | eltérés | küszöb |\n"
            f"|---|---|---|---|---|\n"
            f"| {r['sorozat']} | {r['ertek']} | {r['alapszint']:.1f} | {r['elteres']:+.1%} | "
            f"±{r['kuszob']:.1%} |\n\n"
            f"Minősítés: **{r['jelzes']}**. Részletek: {OLDAL}\n\n"
            f"_Automatikus értesítés (napi_monitor.yml). Amíg a jelzés fennáll, ez az "
            f"issue naponta egy megjegyzést kap; ha a sorozat visszaáll normálra, lezárul._")


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--mappa", type=Path, default=MONITOR)
    ap.add_argument("--szaraz", action="store_true", help="Semmit nem modosit a GitHubon")
    ap.add_argument("--teszt", action="store_true", help="Mesterseges teszt-jelzes")
    args = ap.parse_args()

    if args.teszt:
        nap = datetime.now(timezone.utc).date().isoformat()
        aktiv = [{"sorozat": "Megrakott tanker (7 nap)", "ertek": 30, "alapszint": 50.0,
                  "elteres": -0.4, "kuszob": 0.25, "jelzes": "szokatlanul alacsony"}]
        mind = {"Megrakott tanker (7 nap)"}
    else:
        nap, aktiv, mind = aktiv_jelzesek(args.mappa)
    print(f"Utolso nap: {nap}; aktiv jelzes: {len(aktiv)}")

    gh("label", "create", CIMKE, "--color", "D93F0B", "--force",
       "--description", "A napi forgalmi monitor automatikus jelzese", szaraz=args.szaraz)
    nyitott = json.loads(gh("issue", "list", "--label", CIMKE, "--state", "open",
                            "--json", "number,title", "--limit", "200",
                            szaraz=args.szaraz, kimenet=True) or "[]") if not args.szaraz \
        else []
    nyitott = {i["title"]: i["number"] for i in nyitott}

    aktiv_cimek = set()
    for r in aktiv:
        c = cim(r["sorozat"], r["jelzes"], args.teszt)
        aktiv_cimek.add(c)
        if c in nyitott:
            szam = nyitott[c]
            megj = json.loads(gh("issue", "view", str(szam), "--json", "comments",
                                 szaraz=args.szaraz, kimenet=True) or '{"comments": []}')
            if any(nap in m.get("body", "") for m in megj.get("comments", [])):
                print(f"  #{szam} mar tartalmazza a(z) {nap} napot - nincs teendo")
                continue
            gh("issue", "comment", str(szam), "--body",
               f"Továbbra is fennáll: **{nap}** – érték {r['ertek']}, alapszint "
               f"{r['alapszint']:.1f}, eltérés {r['elteres']:+.1%}.", szaraz=args.szaraz)
            print(f"  #{szam}: megjegyzes ({nap})")
        else:
            gh("issue", "create", "--title", c, "--label", CIMKE, "--body", torzs(r, nap),
               szaraz=args.szaraz)
            print(f"  uj issue: {c}")

    # a mar nem aktiv jelzesek issue-inak lezarasa (a teszt-issue-kat a teszt nem zarja)
    for c, szam in nyitott.items():
        if c in aktiv_cimek or c.startswith("[Monitor-teszt]") != args.teszt:
            continue
        sorozat = c.split("] ", 1)[1].rsplit(": ", 1)[0]
        if sorozat in mind:
            gh("issue", "close", str(szam), "--comment",
               f"A(z) {nap} napon a sorozat már nem jelez – lezárva.", szaraz=args.szaraz)
            print(f"  #{szam} lezarva: {c}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
