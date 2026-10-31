"""
Hormuz-elemzes: kiterjesztett minta (robusztussag, utolag hozzaadva).

A dolgozat/hormuz_merce_kiegeszites_2026-10-31_kiterjesztes.md szerint: a negy
ablak minden napja (258 nap). A fo eredmeny a 76 napos marad; ez a szkript az
outputs/hormuz/ fajljait csak olvassa.

A lanc ugyanaz, mint a fo valtozate, valtozatlan koddal:
  minta       a hianyzo 182 nap listaja -> kiterjesztett/mintanapok.csv
  feldolgoz   hormuz_napi.main(), a napi kimenetek kiterjesztett/-be iranyitva.
              A hormuz_napi.py a napi fajlokat modulszintu utvonalakra irja
              (HORMUZ, ALLAPOT), ezert itt ezeket csereljuk le. Idempotens,
              megszakadas utan ugyanezzel a paranccsal folytathato.
  elemez      a 76 + a kesz uj napok egyesitese kiterjesztett/teljes/-be, ott
              hormuz_elemzes.py es hormuz_mde.py --hormuz kapcsoloval; az
              eredmeny kiterjesztett/-be masolva, plusz osszevetes.csv.

Hasznalat:
    python hormuz_kiterjesztes.py minta
    python hormuz_kiterjesztes.py feldolgoz --kozvetlen-zip
    python hormuz_kiterjesztes.py feldolgoz --osszesito
    python hormuz_kiterjesztes.py elemez
    python hormuz_kiterjesztes.py elemez --csak-fo --teljes <mappa>   # ellenorzes: 76 nap
    python hormuz_kiterjesztes.py bontas     # leiro: kedd-csutortok kontra tobbi nap
"""

import argparse
import shutil
import subprocess
import sys
from datetime import timedelta
from pathlib import Path

import pandas as pd

from utak import KIMENET
from hormuz_kozos import ABLAKOK, HORMUZ, MINTA_HETNAPOK, ablak_atlagok, blokk, did

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)
except AttributeError:
    pass

KI = HORMUZ / "kiterjesztett"
SZURT = KIMENET / "tarolo_hormuz_kiterjesztett"
SZKRIPTEK = Path(__file__).resolve().parent

# A merce szerinti napszam (4 ablak, minden nap), ebbol a fo minta 76 nap
TELJES_NAPOK = 258
FO_NAPOK = 76

HETNAPOK = ["H", "K", "Sze", "Cs", "P", "Szo", "V"]

# Soronkent egyesitendo fajlok (a hormuz_elemzes.py bemenetei) es a napkulcsuk
TABLAK = {"feldolgozas.csv": "nap", "uticel.csv": "nap",
          **{f"atkelesek{s}.csv": "nap" for s in ("", "_drogden", "_nyers", "_sulyozatlan")},
          **{f"monitor{s}/merules_tortenet.csv": "nap" for s in ("", "_drogden", "_nyers", "_sulyozatlan")},
          **{f"monitor{s}/atkelesek_reszletes.csv": "datum" for s in ("", "_drogden", "_nyers", "_sulyozatlan")}}

# Ezek kerulnek a teljes/ munkamappabol a kiterjesztett/ mappaba
KIMENETEK = ("eredmeny.csv", "erzekenyseg.csv", "mde.csv", "mintanap_mutatok.csv",
             "uticel_ertelmezhetoseg.csv", "uticel_osszetetel.csv")


def minta():
    sorok = []
    for nev, (k, v) in ABLAKOK.items():
        d = k
        while d <= v:
            sorok.append({"nap": d.isoformat(), "ablak": nev, "hetnap": HETNAPOK[d.weekday()],
                          "het": blokk(d)})
            d += timedelta(days=1)
    m = pd.DataFrame(sorok)
    a = pd.read_csv(HORMUZ / "feldolgozas.csv", dtype={"nap": str})
    kesz = set(a.loc[a.statusz == "kesz", "nap"])
    if len(m) != TELJES_NAPOK or len(kesz) != FO_NAPOK or not kesz <= set(m.nap):
        sys.exit(f"Varatlan napszam: teljes {len(m)}, kesz {len(kesz)} - megallok.")
    h = m[~m.nap.isin(kesz)]
    KI.mkdir(parents=True, exist_ok=True)
    h.to_csv(KI / "mintanapok.csv", index=False, encoding="utf-8")
    for nev in ABLAKOK:
        print(f"  {nev}: {(m.ablak == nev).sum()} nap, ebbol hianyzik {(h.ablak == nev).sum()}")
    print(f"Feldolgozva: {len(m)} nap, kesz {len(kesz)}, maradt {len(h)} -> {KI / 'mintanapok.csv'}")
    return 0


def feldolgoz(tovabbi):
    import hormuz_napi as hn
    hn.HORMUZ = KI
    hn.MINTA = KI / "mintanapok.csv"
    hn.ALLAPOT = KI / "feldolgozas.csv"
    hn.PIPELINE_NAPLO = KI / "pipeline_napok.csv"
    hn.SZURT_TAROLO = SZURT
    sys.argv = ["hormuz_napi.py"] + tovabbi
    return hn.main()


def egyesit(cel: Path, csak_fo: bool) -> int:
    """A fo minta es a kesz uj napok; ket forras kozott nap nem ismetlodhet."""
    fo_m = pd.read_csv(HORMUZ / "mintanapok.csv", dtype={"nap": str})
    if csak_fo:
        uj_m = fo_m.iloc[0:0]
        uj_kesz = set()
    else:
        uj_a = pd.read_csv(KI / "feldolgozas.csv", dtype={"nap": str})
        uj_kesz = set(uj_a.loc[uj_a.statusz == "kesz", "nap"])
        uj_m = pd.read_csv(KI / "mintanapok.csv", dtype={"nap": str})
        uj_m = uj_m[uj_m.nap.isin(uj_kesz)]
    if set(fo_m.nap) & uj_kesz:
        sys.exit("A fo es az uj minta napjai atfednek - megallok.")
    (cel / "x").parent.mkdir(parents=True, exist_ok=True)
    pd.concat([fo_m, uj_m], ignore_index=True).to_csv(
        cel / "mintanapok.csv", index=False, encoding="utf-8")
    for fajl, kulcs in TABLAK.items():
        t = pd.read_csv(HORMUZ / fajl, dtype={kulcs: str})
        n_fo = len(t)
        if not csak_fo:
            u = pd.read_csv(KI / fajl, dtype={kulcs: str})
            u = u[u[kulcs].isin(uj_kesz)]
            t = pd.concat([t, u], ignore_index=True)
        (cel / fajl).parent.mkdir(parents=True, exist_ok=True)
        t.to_csv(cel / fajl, index=False, encoding="utf-8")
        print(f"  {fajl}: {n_fo:,} + {len(t) - n_fo:,} = {len(t):,} sor")
    return len(fo_m) + len(uj_m)


def elemez(cel: Path, csak_fo: bool):
    n = egyesit(cel, csak_fo)
    print(f"Egyesitve: {n} nap -> {cel}")
    for sz in ("hormuz_elemzes.py", "hormuz_mde.py"):
        print(f"\n$ {sz} --hormuz {cel}")
        r = subprocess.run([sys.executable, str(SZKRIPTEK / sz), "--hormuz", str(cel)])
        if r.returncode:
            sys.exit(f"{sz}: kilepes {r.returncode}")
    # az abra felirata "kedd-csutortoki mintanapok", itt nem igaz; a 258 naposrol nem kozoljuk
    (cel / "abra_ablakok.png").unlink(missing_ok=True)
    if csak_fo:
        return ellenoriz(cel)
    for f in KIMENETEK:
        shutil.copy2(cel / f, KI / f)
    osszevet(n)
    return 0


def ellenoriz(cel: Path):
    """A 76 napos egyesites az eredeti utvonalon szamjegyre visszaadja a fo eredmenyt?"""
    hiba = 0
    for f in ("eredmeny.csv", "erzekenyseg.csv", "mde.csv", "mintanap_mutatok.csv"):
        a, b = pd.read_csv(HORMUZ / f), pd.read_csv(cel / f)
        azonos = a.equals(b)
        print(f"  {f}: {'AZONOS' if azonos else 'ELTER'} ({len(a)} sor)")
        hiba += not azonos
    return 1 if hiba else 0


def osszevet(n: int):
    """A merce 'Kozlendo' pontja: a ket minta egymas mellett."""
    sorok = []
    for cim, h in (("fő (76 nap)", HORMUZ), (f"kiterjesztett ({n} nap)", KI)):
        e = pd.read_csv(h / "eredmeny.csv").set_index("mutato")
        d = pd.read_csv(h / "mde.csv").set_index("mutato")
        fo = "kimutatható" if e.loc[["H1", "H2"], "holm_elvet"].any() else "nem mutatható ki"
        for m in e.index:
            sorok.append({"minta": cim, "mutato": m, "did": e.loc[m, "did"],
                          "ci95_also": e.loc[m, "ci95_also"], "ci95_felso": e.loc[m, "ci95_felso"],
                          "holm_ci_also": e.loc[m, "holm_ci_also"], "holm_ci_felso": e.loc[m, "holm_ci_felso"],
                          "p_holm": e.loc[m, "p_holm"], "holm_elvet": e.loc[m, "holm_elvet"],
                          "se_bootstrap": d.loc[m, "se_bootstrap"], "szint_A26": d.loc[m, "szint_A26"],
                          "mde": d.loc[m, "mde"], "mde_szint_arany": d.loc[m, "mde_szint_arany"],
                          "mde_holm1": d.loc[m, "mde_holm1"], "kovetkeztetes": fo})
    t = pd.DataFrame(sorok)
    t.to_csv(KI / "osszevetes.csv", index=False, encoding="utf-8")
    pd.set_option("display.width", 250)
    print("\nOsszevetes:")
    print(t.round(4).to_string(index=False))
    print(f"-> {KI / 'osszevetes.csv'}")


def bontas():
    """Leiro, nem a merce resze: honnan jon a ket minta kulonbsege? A 258 napos
    futas napi mutatoi a fo minta hetnapjaira es a tobbi napra bontva, pontbecslessel."""
    d = pd.read_csv(KI / "mintanap_mutatok.csv", dtype={"nap": str})
    d["egy"] = 1
    kt = pd.to_datetime(d.nap).dt.weekday.isin(MINTA_HETNAPOK)
    sorok = []
    for m, (sz, nv) in {"H1": ("h1", "egy"), "H2": ("h2_szamlalo", "h2_nevezo"), "H3": ("h3", "egy")}.items():
        for cim, g in (("kedd-csütörtök (258 napos P95)", d[kt]), ("a többi nap", d[~kt]), ("mind", d)):
            a = ablak_atlagok(g, sz, nv)
            sorok.append({"mutato": m, "reszminta": cim, "napok": len(g), **a, "did": did(a)})
    t = pd.DataFrame(sorok)
    t.to_csv(KI / "hetnap_bontas.csv", index=False, encoding="utf-8")
    pd.set_option("display.width", 250)
    print(t.round(4).to_string(index=False))
    print(f"Feldolgozva: {len(d)} nap, {len(t)} sor -> {KI / 'hetnap_bontas.csv'}")
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("lepes", choices=("minta", "feldolgoz", "elemez", "bontas"))
    ap.add_argument("--teljes", type=Path, default=KI / "teljes", help="elemez: az egyesitett munkamappa")
    ap.add_argument("--csak-fo", action="store_true",
                    help="elemez: csak a 76 nap; a kimenetnek egyeznie kell a fo eredmennyel")
    args, tovabbi = ap.parse_known_args()
    if args.lepes == "minta":
        return minta()
    if args.lepes == "feldolgoz":
        return feldolgoz(tovabbi)
    if args.lepes == "bontas":
        return bontas()
    return elemez(args.teljes, args.csak_fo)


if __name__ == "__main__":
    sys.exit(main())
