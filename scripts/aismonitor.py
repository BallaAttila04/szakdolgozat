"""
A napi monitor egyseges parancssori belepesi pontja.

Vekony burok a meglevo szkriptek folott: minden alparancs a megfelelo
szkriptet hivja (sajat folyamatban, valtozatlan kapcsolokkal), logikat nem
duplikal. Az 'allapot' a dashboard_epit.py legutobbi() fuggvenyet hasznalja,
ugyanazt, amibol a docs/adat/legutobbi.json keszul.

Alparancsok:
  allapot     az utolso nap, a sorozatok es az aktiv jelzesek a terminalba
  dashboard   a dashboard es az adat-feed epitese      (dashboard_epit.py)
  oldal       a nyitolap epitese                       (oldal_epit.py)
  backtest    a jelzesi szabaly backtestje             (backtest.py)
  kapuk       a kiserleti kapuk szamolasa es elemzese  (kapu_kiterjesztes.py + kapu_elemzes.py)
  napi        a napi futas, valtozatlan parancs        (napi_futas.py)
  teszt       a dashboard-, terkep- es kapu-tesztek

A '--' utani kapcsolok valtozatlanul a hivott szkripthez kerulnek, pl.:
    python aismonitor.py allapot
    python aismonitor.py allapot --json
    python aismonitor.py dashboard -- --oldal docs
    python aismonitor.py napi -- --szaraz
    python aismonitor.py kapuk -- --napok 2026-07-15 2026-07-16
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

from utak import KIMENET

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)
except AttributeError:
    pass

SZKRIPTEK = Path(__file__).resolve().parent

# alparancs -> a hivott szkriptek sorrendben, es a sugo egy sora
PARANCSOK = {
    "dashboard": (["dashboard_epit.py"], "a dashboard es az adat-feed epitese (docs/)"),
    "oldal": (["oldal_epit.py"], "a nyitolap epitese (docs/index.html)"),
    "backtest": (["backtest.py"], "a jelzesi szabaly backtestje (outputs/backtest/)"),
    "kapuk": (["kapu_kiterjesztes.py", "kapu_elemzes.py"],
              "a kiserleti kapuk szamolasa es elemzese (outputs/kapuk_kiterjesztes/)"),
    "napi": (["napi_futas.py"], "a napi futas: letoltes -> monitor -> oldal -> dashboard"),
}


def futtat(szkript: str, extra: list) -> int:
    parancs = [sys.executable, str(SZKRIPTEK / szkript), *extra]
    print(f"$ {' '.join(parancs[1:])}", flush=True)
    # UTF-8 kimenet a gyerekfolyamatban is: atiranyitott kimenetnel a Windows
    # alap kodlapja (cp1250) az "Ø" betunel elszallna (pl. teszt_kapuk.py).
    env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
    return subprocess.run(parancs, env=env).returncode


def allapot(monitor: Path, json_ki: bool) -> int:
    from dashboard_epit import legutobbi
    if not (monitor / "allapot.json").exists():
        print(f"Nincs monitor-allapot: {monitor / 'allapot.json'}")
        return 1
    lu = legutobbi(monitor)
    if json_ki:
        print(json.dumps(lu, ensure_ascii=False, indent=1))
        return 0
    f = lu.get("utolso_futas") or {}
    print(f"Utolso nap:     {lu['utolso_nap']}  (idosor: {lu['elso_nap']} - {lu['utolso_nap']}, {lu['napok_szama']} nap)")
    print(f"Frissitve:      {lu['frissitve_utc']}")
    print(f"Utolso futas:   {f.get('ido_utc', '-')}  {f.get('statusz', '-')}  {f.get('uzenet', '')}")
    print(f"\n{'sorozat':<34} {'ertek':>8} {'alapszint':>10} {'elteres':>9} {'kuszob':>8}  jelzes")
    for s in lu["sorozatok"]:
        alap = f"{s['alapszint']:.1f}" if s["alapszint"] is not None else "-"
        elt = f"{s['elteres']:+.1%}" if s["elteres"] is not None else "-"
        kusz = f"±{s['kuszob']:.1%}" if s["kuszob"] is not None else "-"
        print(f"{s['sorozat']:<34} {s['ertek']:>8} {alap:>10} {elt:>9} {kusz:>8}  {s['jelzes']}")
    akt = lu["aktiv_jelzesek"]
    print(f"\nAktiv jelzes az utolso napon: {len(akt)}"
          + "".join(f"\n  {s['sorozat']}: {s['jelzes']} ({s['elteres']:+.1%})" for s in akt))
    print(f"Jelzes az utolso napokban: {len(lu['jelzesek_utolso_napok'])} nap-sorozat par")
    return 0


def teszt() -> int:
    hibak = 0
    node = shutil.which("node")
    for t in ["teszt_dashboard.mjs", "teszt_terkep.mjs"]:
        if node:
            print(f"$ node {t}", flush=True)
            hibak += subprocess.run([node, str(SZKRIPTEK / t)]).returncode != 0
        else:
            print(f"KIHAGYVA (nincs node): {t}")
    hibak += futtat("teszt_kapuk.py", []) != 0
    print(f"\nTesztcsomagok: {'mind rendben' if not hibak else f'{hibak} bukott'}")
    return 1 if hibak else 0


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    al = ap.add_subparsers(dest="parancs", required=True, metavar="alparancs")
    a = al.add_parser("allapot", help="az utolso nap es a jelzesek a terminalba")
    a.add_argument("--monitor", type=Path, default=KIMENET / "monitor")
    a.add_argument("--json", action="store_true", help="a legutobbi.json tartalma")
    for nev, (_, sugo) in PARANCSOK.items():
        p = al.add_parser(nev, help=sugo,
                          description=f"{sugo}. A '--' utani kapcsolok a hivott szkripte.")
        p.add_argument("extra", nargs=argparse.REMAINDER,
                       help="a hivott szkript kapcsoloi ('--' utan)")
    al.add_parser("teszt", help="a dashboard-, terkep- es kapu-tesztek")
    args = ap.parse_args()

    if args.parancs == "allapot":
        return allapot(args.monitor, args.json)
    if args.parancs == "teszt":
        return teszt()
    extra = args.extra[1:] if args.extra[:1] == ["--"] else args.extra
    szkriptek = PARANCSOK[args.parancs][0]
    if any(x in ("-h", "--help") for x in extra):
        szkriptek = szkriptek[:1]          # sugonal a tobbi lepes ne fusson le
    kovetkezo = []
    if args.parancs == "kapuk" and "--ki" in extra:
        # az elemzes ugyanabbol a mappabol olvasson, ahova a szamolas irt
        kovetkezo = ["--be", extra[extra.index("--ki") + 1]]
    for i, sz in enumerate(szkriptek):
        # tobb lepesnel (kapuk) a kapcsolok az elso szkripte; a tobbi csak a mappat kapja
        kod = futtat(sz, extra if i == 0 else kovetkezo)
        if kod != 0:
            return kod
    return 0


if __name__ == "__main__":
    sys.exit(main())
