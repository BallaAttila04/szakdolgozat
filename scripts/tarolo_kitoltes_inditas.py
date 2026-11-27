"""
A Parquet-tarolo kiegeszitese a 2026. oktober 7-22. kozotti 16 nappal (a monitor-idosor
144 napjanak utolso 16 napja, amely eddig csak a felhobeli futaton keszult).

VS Code-ban a Run gombbal futtathato. Minden napot kulon, frissen inditott
programpeldanyban dolgoz fel (pipeline.py <nap> --kozvetlen-zip --torol-zip), igy a
validalt nap ZIP-je torlodik, es megszakitas utan ujrainditva a mar kesz napokat
kihagyja. Minden kimenet a konzolra es az outputs/tarolo_kitoltes/naplo.txt fajlba is kerul.
"""
import subprocess
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

ITT = Path(__file__).resolve().parent
sys.path.insert(0, str(ITT))
from kitoltes_inditas import python_keres  # noqa: E402  (a csomagokat tartalmazo Pythont keresi)

NAPLO = ITT.parent / "outputs" / "tarolo_kitoltes" / "naplo.txt"
NAPLO.parent.mkdir(parents=True, exist_ok=True)
ELSO, UTOLSO = date(2026, 10, 7), date(2026, 10, 22)


def futtat(python, nap):
    parancs = [python, "-u", str(ITT / "pipeline.py"), nap, "--kozvetlen-zip", "--torol-zip"]
    with open(NAPLO, "a", encoding="utf-8") as n:
        n.write(f"\n### {datetime.now().isoformat(timespec='seconds')}  {nap}\n")
        p = subprocess.Popen(parancs, cwd=ITT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                             text=True, encoding="utf-8", errors="replace")
        for sor in p.stdout:
            print(sor, end="")
            n.write(sor)
            n.flush()
        return p.wait()


if __name__ == "__main__":
    py = python_keres()
    print(f"Feldolgozo Python: {py}\nNaplo: {NAPLO}\n")
    hibak = []
    d = ELSO
    while d <= UTOLSO:
        k = futtat(py, d.isoformat())
        if k != 0:
            hibak.append(d.isoformat())
        d += timedelta(days=1)
    print(f"\nKesz. Hibas napok: {hibak or 'nincs'}")
    sys.exit(1 if hibak else 0)
