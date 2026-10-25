"""
Kapu-kiterjesztes: a konfiguracio (scripts/kapuk.json) minden kapuja a
Parquet-tarolo minden napjan - az atviheto-sag (KK3) demonstracioja.

Uj kapuhoz nem kell kodot modositani: a kapuk.json-ba kerul egy uj bejegyzes
(nev, ket vegpont, iranynevek), es ez a szkript a tarolo napjain kiszamolja
az atkeleseit a kapuvonal.py logikajaval (import, nem masolat).

Csoportositas a tipus-szavazas miatt: a kapuvonal.py egy hivason belul a
hivas OSSZES kapujanak folyosojaban latott poziciokbol donti el a hajo tipusat.
  - a monitorozott kapuk (monitor: true) egy hivasban futnak, pontosan ugy,
    ahogy a monitor.py hivja - igy az eredmenyuk a monitortablaval
    (outputs/monitor/kapuvonal_napi.csv) soronkent osszevetheto;
  - minden kiserleti kapu kulon hivasban fut, hogy egy uj kapu felvetele a
    tobbi kapu szamait ne valtoztassa meg.

Idempotens es ujraindithato: naponkent egy koztes fajl
(<ki>/napok/<nap>.csv + <nap>.json). Egy napot ujraszamol, ha hianyzik, ha a
kapukonfiguracio azota valtozott (a .json-ban tarolt ujjlenyomat), vagy
--felulir eseten.

Kimenet (<ki> = outputs/kapuk_kiterjesztes):
  kapuvonal_napi.csv   datum, kapu, irany, csoport, atkeles  (a monitor formatuma)
  atkelesek.csv        atkelesenkent: datum, kapu, ts, MMSI, irany, csoport, merules_m
  futasido.csv         naponkent, kapucsoportonkent: mp, folyoso-pozicio, atkeles

Hasznalat:
    python kapu_kiterjesztes.py                         # a tarolo minden napja
    python kapu_kiterjesztes.py --napok 2026-07-15 2026-07-16
    python kapu_kiterjesztes.py --kapuk mas_kapuk.json --ki outputs/proba
"""

import argparse
import contextlib
import hashlib
import io
import json
import os
import sys
import time
from pathlib import Path

import pandas as pd

from utak import KIMENET
from kapuvonal import KAPU_KONFIG, betolt, feldolgoz_parquet, folyoso
from pipeline import TAROLO

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)
except AttributeError:
    pass

KI = KIMENET / "kapuk_kiterjesztes"
OSZLOPOK = ["datum", "kapu", "ts", "MMSI", "irany", "csoport", "merules_m"]


def ujjlenyomat(kapuk) -> str:
    """A kapuk geometriajanak es iranyneveinek kivonata: ha ez valtozik, a
    koztes napi eredmeny elavult."""
    s = json.dumps([[k.nev, k.a, k.b, k.iranyok, k.monitor] for k in kapuk],
                   ensure_ascii=False)
    return hashlib.sha1(s.encode("utf-8")).hexdigest()[:12]


def csoportok(kapuk):
    """[(csoportnev, {nev: Kapu})]: a monitor-kapuk egyutt, a tobbi kulon."""
    mon = {k.nev: k for k in kapuk if k.monitor}
    ki = [("monitor", mon)] if mon else []
    ki += [(k.nev, {k.nev: k}) for k in kapuk if not k.monitor]
    return ki


def tarolo_napok(tarolo: Path):
    return sorted((p.stem.replace("aisdk-", ""), p)
                  for p in tarolo.glob("ev=*/ho=*/aisdk-*.parquet"))


def egy_nap(nap, pq, csop, folyosok):
    """Egy nap minden kapucsoportja. Visszaad: atkelesek, futasido-sorok, nyers sorszam."""
    darabok, ido, nyers = [], [], None
    for cs_nev, kapuk in csop:
        t0 = time.perf_counter()
        with contextlib.redirect_stdout(io.StringIO()):
            atk, osszes = feldolgoz_parquet(pq, {n: folyosok[n] for n in kapuk}, kapuk)
        mp = time.perf_counter() - t0
        nyers = osszes
        poz = (atk.groupby("kapu")["folyoso_pozicio"].first().to_dict()
               if not atk.empty else {})
        ido.append({"datum": nap, "csoport": cs_nev, "kapuk": len(kapuk),
                    "mp": round(mp, 3), "folyoso_pozicio": int(sum(poz.values())),
                    "atkeles": len(atk)})
        if not atk.empty:
            darabok.append(atk)
    atk = pd.concat(darabok, ignore_index=True) if darabok else pd.DataFrame(
        columns=["MMSI", "ts", "irany", "kapu", "csoport", "merules_m"])
    atk.insert(0, "datum", nap)
    return atk[OSZLOPOK], ido, nyers


def atomi(df: pd.DataFrame, ut: Path):
    tmp = ut.with_suffix(ut.suffix + ".tmp")
    df.to_csv(tmp, index=False, encoding="utf-8")
    os.replace(tmp, ut)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--kapuk", type=Path, default=KAPU_KONFIG)
    ap.add_argument("--tarolo", type=Path, default=TAROLO)
    ap.add_argument("--ki", type=Path, default=KI)
    ap.add_argument("--napok", nargs="*", help="Csak ezek a napok (YYYY-MM-DD)")
    ap.add_argument("--felulir", action="store_true", help="A kesz napokat is ujraszamolja")
    args = ap.parse_args()

    kapuk = betolt(args.kapuk)
    lenyomat = ujjlenyomat(kapuk)
    csop = csoportok(kapuk)
    folyosok = {k.nev: folyoso(k) for k in kapuk}
    print(f"Konfiguracio: {args.kapuk} ({len(kapuk)} kapu, ujjlenyomat {lenyomat})")
    for k in kapuk:
        print(f"  {k.nev:<18} {'monitor ' if k.monitor else 'kiserleti'} "
              f"{k.a} -> {k.b}, iranyok {k.iranyok}, H3-folyoso {len(folyosok[k.nev])} cella")

    napok = tarolo_napok(args.tarolo)
    if args.napok:
        napok = [(n, p) for n, p in napok if n in set(args.napok)]
    koztes = args.ki / "napok"
    koztes.mkdir(parents=True, exist_ok=True)
    print(f"Tarolo: {args.tarolo}, {len(napok)} nap")

    uj = kesz = 0
    t_ossz = time.perf_counter()
    for nap, pq in napok:
        csv_ut, meta_ut = koztes / f"{nap}.csv", koztes / f"{nap}.json"
        if not args.felulir and csv_ut.exists() and meta_ut.exists():
            meta = json.loads(meta_ut.read_text(encoding="utf-8"))
            if meta.get("ujjlenyomat") == lenyomat:
                kesz += 1
                continue
        atk, ido, nyers = egy_nap(nap, pq, csop, folyosok)
        atomi(atk, csv_ut)
        meta = {"datum": nap, "ujjlenyomat": lenyomat, "nyers_sor": int(nyers or 0),
                "futasido": ido}
        tmp = meta_ut.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
        os.replace(tmp, meta_ut)
        uj += 1
        print(f"  {nap}: {nyers:>12,} nyers sor, {len(atk):>5} atkeles, "
              f"{sum(r['mp'] for r in ido):5.1f} mp  ("
              + ", ".join(f"{r['csoport']} {r['mp']:.2f}" for r in ido) + ")")
    print(f"Ujraszamolt nap: {uj}, mar kesz (kihagyva): {kesz}, "
          f"ido: {time.perf_counter() - t_ossz:.0f} mp")

    # Osszesites a koztes fajlokbol (csak a jelenlegi konfiguracioval keszultek)
    atk_l, ido_l, nyers_ossz = [], [], 0
    for nap, _ in napok:
        meta = json.loads((koztes / f"{nap}.json").read_text(encoding="utf-8"))
        if meta.get("ujjlenyomat") != lenyomat:
            sys.exit(f"{nap}: elavult koztes eredmeny")
        atk_l.append(pd.read_csv(koztes / f"{nap}.csv", dtype={"datum": str}))
        ido_l += meta["futasido"]
        nyers_ossz += meta["nyers_sor"]
    atk = pd.concat(atk_l, ignore_index=True)
    atk = atk.sort_values(["datum", "kapu", "ts", "MMSI"], kind="stable").reset_index(drop=True)
    atomi(atk, args.ki / "atkelesek.csv")
    napi = (atk.groupby(["datum", "kapu", "irany", "csoport"]).size()
            .reset_index(name="atkeles"))
    atomi(napi, args.ki / "kapuvonal_napi.csv")
    ido = pd.DataFrame(ido_l)
    atomi(ido, args.ki / "futasido.csv")

    print(f"\nFeldolgozott nyers sor: {nyers_ossz:,} ({len(napok)} nap); "
          f"atkeles osszesen: {len(atk):,}")
    ker = atk[atk["csoport"].isin(["Teherhajó", "Tanker"])]
    for k in kapuk:
        a = atk[atk["kapu"] == k.nev]
        kk = ker[ker["kapu"] == k.nev]
        print(f"  {k.nev:<18} {len(a):>7,} atkeles, ebbol kereskedelmi {len(kk):>6,} "
              f"(napi atlag {len(kk) / max(len(napok), 1):6.1f})")
    print("Futasido (mp/nap/kapucsoport, median | atlag | max):")
    for cs, g in ido.groupby("csoport", sort=False):
        print(f"  {cs:<18} {g['mp'].median():.2f} | {g['mp'].mean():.2f} | {g['mp'].max():.2f}"
              f"  ({int(g['kapuk'].iloc[0])} kapu)")
    print(f"-> {args.ki / 'kapuvonal_napi.csv'} ({len(napi):,} sor)")
    print(f"-> {args.ki / 'atkelesek.csv'} ({len(atk):,} sor, "
          f"{(args.ki / 'atkelesek.csv').stat().st_size / 1e6:.1f} MB)")
    print(f"-> {args.ki / 'futasido.csv'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
