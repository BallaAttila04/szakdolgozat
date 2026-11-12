"""
Inditofajl a dan idosor kitoltesehez (hormuz_kitoltes.py): VS Code-ban a Run gombbal
futtathato. Elobb elkesziti a hianyzo napok listajat, aztan feldolgozza oket; minden
kimenet a konzolra es az outputs/hormuz/kitoltes/naplo.txt fajlba is kerul.
Megszakitas utan ugyanigy ujrainditva onnan folytatja, ahol abbahagyta.
"""
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ITT = Path(__file__).resolve().parent
NAPLO = ITT.parent / "outputs" / "hormuz" / "kitoltes" / "naplo.txt"
NAPLO.parent.mkdir(parents=True, exist_ok=True)

# A VS Code nem mindig azt a Pythont valasztja, amelyikben a csomagok telepitve vannak
# (pl. a Microsoft Store-os python.exe). Ezert a jelolteket sorban kiprobaljuk, es az
# elsot hasznaljuk, amelyikben a pipeline osszes fuggosege importalhato.
SZUKSEGES = "import pandas, duckdb, h3, psutil, numpy"
_LOCAL = Path(os.environ.get("LOCALAPPDATA", ""))
JELOLTEK = [
    [sys.executable],
    [str(_LOCAL / "Programs" / "Python" / "Python313" / "python.exe")],
    ["py", "-3.13"],
    ["py", "-3"],
    ["python"],
    [str(_LOCAL / "Programs" / "Python" / "Python39" / "python.exe")],
]


def python_keres():
    for jelolt in JELOLTEK:
        try:
            r = subprocess.run(jelolt + ["-c", SZUKSEGES + "; import sys; print(sys.executable)"],
                               capture_output=True, text=True, timeout=120)
        except (OSError, subprocess.TimeoutExpired):
            continue
        if r.returncode == 0 and r.stdout.strip():
            return r.stdout.strip().splitlines()[-1]
    sys.exit("Nem talaltam olyan Pythont, amelyben a pandas, duckdb, h3, psutil es numpy "
             "is telepitve van. Probald: pip install -r requirements-monitor.txt")


PYTHON = None


def futtat(*argumentumok):
    parancs = [PYTHON, "-u", str(ITT / "hormuz_kitoltes.py"), *argumentumok]
    with open(NAPLO, "a", encoding="utf-8") as n:
        n.write(f"\n### {datetime.now().isoformat(timespec='seconds')}  {' '.join(argumentumok)}\n")
        p = subprocess.Popen(parancs, cwd=ITT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                             text=True, encoding="utf-8", errors="replace")
        for sor in p.stdout:
            print(sor, end="")
            n.write(sor)
            n.flush()
        return p.wait()


if __name__ == "__main__":
    PYTHON = python_keres()
    print(f"VS Code Python: {sys.executable}\nFeldolgozo Python: {PYTHON}\nNaplo: {NAPLO}\n")
    k = futtat("minta")
    if k == 0:
        k = futtat("feldolgoz", "--kozvetlen-zip")
    print(f"\nKesz, kilepesi kod: {k}")
    sys.exit(k)
