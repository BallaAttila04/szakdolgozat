"""
Animalt terkephez valo adat eloallitasa: hajopoziciok szabalyos idoracson.

FONTOS modszertani megjegyzes: az animaciohoz szabalyos idosor kell, ezert itt
hajonkent UJRAMINTAVETELEZUNK - ez interpolalt, tehat reszben kitalalt adat.
Ez kizarolag MEGJELENITESI reteg, nem forrasadat, es nem szabad belole szamot
szamolni (ld. naplo.md, a regularizalasrol szolo resz). Az elemzesi szamok
mindig a nyers, szabalytalan adatbol jonnek.

A kitoltes korlatozott: ha ket valodi pozicio kozott tobb mint MAX_HEZAG_PERC
telt el, a hajo abban az idoszakban NEM jelenik meg (nem talalunk ki poziciot
hosszu vetelkieseseken at).

Kimenet: egy tomor JSON, amit a terkep olvas.
  - meta: bounding box, idorács, hajoszam
  - hajok: hajonkent egy savval kodolt palya (Uint16-kent kvantalt koordinatak,
    base64-ben), plusz a jelenleti maszk

Hasznalat:
    python terkep_adat.py tomorites_out/aisdk-2026-07-15_teljes.parquet
    python terkep_adat.py <parquet> --perc 10 --ki terkep_adat.json
"""

import argparse
import base64
import json
from pathlib import Path

import numpy as np
import pandas as pd

LAT_MIN, LAT_MAX = 54.5, 56.5
LON_MIN, LON_MAX = 10.0, 13.0

# Ennel hosszabb hezagon at nem interpolalunk - ott a hajo egyszeruen eltunik.
MAX_HEZAG_PERC = 20

# Kvantalas: a bounding boxot 0..65534 tartomanyra kepezzuk (Uint16).
# Ez ~3 m felbontas szelessegben, ~5 m hosszusagban - boven eleg terkephez.
HIANYZO = 65535


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("parquet", help="Bemeneti Parquet (MMSI, ts, Latitude, Longitude, SOG)")
    ap.add_argument("--perc", type=int, default=10, help="Idorács lepeskoze percben")
    ap.add_argument("--ki", default="terkep_adat.json")
    args = ap.parse_args()

    print(f"Betoltes: {args.parquet}")
    df = pd.read_parquet(args.parquet, columns=["MMSI", "ts", "Latitude", "Longitude", "SOG"])
    df = df.sort_values(["MMSI", "ts"], kind="stable")
    print(f"  {len(df):,} pozicio, {df['MMSI'].nunique():,} hajo")

    nap_kezd = df["ts"].min().normalize()
    nap_veg = nap_kezd + pd.Timedelta(days=1)
    racs = pd.date_range(nap_kezd, nap_veg, freq=f"{args.perc}min", inclusive="left")
    racs_mp = racs.astype("int64").to_numpy() / 1e9
    n_frame = len(racs)
    max_hezag_mp = MAX_HEZAG_PERC * 60
    print(f"  idorács: {n_frame} lepes, {args.perc} percenkent")

    mmsi_arr = df["MMSI"].to_numpy()
    t_arr = df["ts"].astype("int64").to_numpy() / 1e9
    lat_arr = df["Latitude"].to_numpy()
    lon_arr = df["Longitude"].to_numpy()
    sog_arr = df["SOG"].to_numpy()

    hatarok = np.flatnonzero(np.r_[True, mmsi_arr[1:] != mmsi_arr[:-1], True])

    hajok = []
    palyak = []

    for gi in range(len(hatarok) - 1):
        a, b = hatarok[gi], hatarok[gi + 1]
        if b - a < 2:
            continue

        t = t_arr[a:b]
        # Csak azokra a racspontokra, amik a hajo elso es utolso uzenete koze esnek
        eleje = np.searchsorted(racs_mp, t[0], side="left")
        vege = np.searchsorted(racs_mp, t[-1], side="right")
        if vege <= eleje:
            continue

        r = racs_mp[eleje:vege]
        i_lat = np.interp(r, t, lat_arr[a:b])
        i_lon = np.interp(r, t, lon_arr[a:b])
        i_sog = np.interp(r, t, sog_arr[a:b])

        # Hosszú hezagok kimaszkolasa: minden racspontra a legkozelebbi valodi
        # uzenet tavolsaga
        idx = np.searchsorted(t, r)
        elozo = np.clip(idx - 1, 0, len(t) - 1)
        kovetkezo = np.clip(idx, 0, len(t) - 1)
        tav = np.minimum(np.abs(r - t[elozo]), np.abs(t[kovetkezo] - r))
        # a ket szomszedos valodi pont kozti hezag
        hezag = t[kovetkezo] - t[elozo]
        ervenyes = (hezag <= max_hezag_mp) | (tav <= max_hezag_mp / 2)

        if not ervenyes.any():
            continue

        x = np.full(len(r), HIANYZO, dtype=np.uint16)
        y = np.full(len(r), HIANYZO, dtype=np.uint16)
        qx = ((i_lon - LON_MIN) / (LON_MAX - LON_MIN) * 65534).round()
        qy = ((i_lat - LAT_MIN) / (LAT_MAX - LAT_MIN) * 65534).round()
        jo = ervenyes & np.isfinite(qx) & np.isfinite(qy) \
             & (qx >= 0) & (qx <= 65534) & (qy >= 0) & (qy <= 65534)
        x[jo] = qx[jo].astype(np.uint16)
        y[jo] = qy[jo].astype(np.uint16)

        # Sebesseg 0..255 csomo helyett 0..63 (negyed csomo felbontas, 0-63 kn)
        s = np.clip(np.nan_to_num(i_sog, nan=0.0), 0, 63).astype(np.uint8)

        hajok.append({"s": int(eleje), "n": int(len(r))})
        palyak.append((x, y, s))

    print(f"  megjelenitheto hajo: {len(hajok):,}")

    # Osszefuzes egyetlen bufferbe
    xs = np.concatenate([p[0] for p in palyak])
    ys = np.concatenate([p[1] for p in palyak])
    ss = np.concatenate([p[2] for p in palyak])

    ki = {
        "meta": {
            "nap": str(nap_kezd.date()),
            "lat_min": LAT_MIN, "lat_max": LAT_MAX,
            "lon_min": LON_MIN, "lon_max": LON_MAX,
            "perc": args.perc,
            "frame_db": n_frame,
            "hajo_db": len(hajok),
            "hianyzo": HIANYZO,
            "max_hezag_perc": MAX_HEZAG_PERC,
        },
        "hajok": hajok,
        "x": base64.b64encode(xs.tobytes()).decode("ascii"),
        "y": base64.b64encode(ys.tobytes()).decode("ascii"),
        "sog": base64.b64encode(ss.tobytes()).decode("ascii"),
    }

    Path(args.ki).write_text(json.dumps(ki, separators=(",", ":")), encoding="utf-8")
    meret = Path(args.ki).stat().st_size / 1_048_576
    print(f"-> {args.ki} kiirva ({meret:,.1f} MB, {len(xs):,} racspozicio)")


if __name__ == "__main__":
    main()
