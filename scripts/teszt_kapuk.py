"""
A konfiguralhato kapuvonal (kapuvonal.py) atkeles-felismeresenek tesztje
szintetikus nyomvonalakon. Onalloan futtathato, nem olvas AIS-adatot:

    python scripts/teszt_kapuk.py

Esetek: meroleges atkeles ferde szakaszon, parhuzamos haladas, a szakasz
vegen kivuli atkeles, oda-vissza, MAX_RES_MP-nel nagyobb res (es pont annyi),
szelessegi kor mint specialis eset (a regi szabaly: a vonalon fekvo pont az
eszaki oldalhoz tartozik), forditott vegpontsorrend, delibab-kapu,
egymas utani kulonbozo hajok, a konfiguracio betoltese es a bbox.
"""

import contextlib
import io
import json
import sys
import tempfile
from pathlib import Path

import h3
import numpy as np
import pandas as pd

with contextlib.redirect_stdout(io.StringIO()):
    import kapuvonal as kv
from kapuvonal import Kapu, MAX_RES_MP, atkelesek

T0 = pd.Timestamp("2026-07-15 12:00:00")
eredmeny = {"ok": 0, "hiba": 0}


def nyom(pontok, mmsi=1, lepes=60):
    """pontok: [(lat, lon)] vagy [(lat, lon, mp)] -> DataFrame."""
    sorok = []
    for i, p in enumerate(pontok):
        mp = p[2] if len(p) > 2 else i * lepes
        sorok.append({"MMSI": mmsi, "ts": T0 + pd.Timedelta(seconds=mp),
                      "Latitude": p[0], "Longitude": p[1]})
    return pd.DataFrame(sorok)


def ellenoriz(nev, kapott, vart):
    if kapott == vart:
        eredmeny["ok"] += 1
        print(f"  OK    {nev}")
    else:
        eredmeny["hiba"] += 1
        print(f"  HIBA  {nev}: kapott {kapott!r}, vart {vart!r}")


def iranyok(df, k):
    return list(atkelesek(df, k)["irany"])


# Ferde szakasz (DNY -> EK), kb. 0,2 x 0,2 fok; a -> b-tol balra = eszaknyugat
FERDE = Kapu("ferde", (55.0, 11.0), (55.2, 11.2), ("ÉNy", "DK"))
# Szelessegi kor (a ket monitorozott kapu alakja)
SZEL = Kapu("szel", (55.40, 10.60), (55.40, 11.35))
# Delibab-kapu (deltol eszak fele): balra = nyugat
DELI = Kapu("deli", (54.50, 11.15), (54.76, 11.15), ("nyugat", "kelet"))

print("Atkeles-felismeres, szintetikus nyomvonalak:")

# 1. meroleges atkeles a szakasz kozepen (kozeppont: 55.1, 11.1)
d = nyom([(55.12, 11.08), (55.11, 11.09), (55.09, 11.11), (55.08, 11.12)])
ellenoriz("meroleges atkeles DK fele", iranyok(d, FERDE), ["DK"])
ellenoriz("meroleges atkeles EK-rol visszafele (ENy)", iranyok(d.iloc[::-1].assign(
    ts=d["ts"].to_numpy()), FERDE), ["ÉNy"])
a = atkelesek(d, FERDE)
ellenoriz("az atkeles ideje a vonal utani elso pozicio", a["ts"].tolist(),
          [T0 + pd.Timedelta(seconds=120)])

# 2. parhuzamos haladas a vonal egyik oldalan
d = nyom([(55.02 + i * 0.02, 11.00 + i * 0.02) for i in range(9)])
ellenoriz("parhuzamos haladas a vonaltol nyugatra", iranyok(d, FERDE), [])

# 3. atkeles a szakasz vegpontjan tul (a b-n tul, majd az a elott)
d = nyom([(55.26, 11.24), (55.24, 11.26)])
ellenoriz("atkeles a b vegponton tul", iranyok(d, FERDE), [])
d = nyom([(54.96, 10.94), (54.94, 10.96)])
ellenoriz("atkeles az a vegpont elott", iranyok(d, FERDE), [])
d = nyom([(55.11, 11.09), (55.30, 11.10)])
ellenoriz("csak az egyik pozicio esik a szakasz hatarai koze", iranyok(d, FERDE), [])

# 4. oda-vissza (pl. komp): ket atkeles, ellentetes irannyal
d = nyom([(55.11, 11.09), (55.09, 11.11), (55.11, 11.09), (55.09, 11.11)])
ellenoriz("oda-vissza-oda: harom atkeles", iranyok(d, FERDE), ["DK", "ÉNy", "DK"])

# 5. idores
d = nyom([(55.11, 11.09, 0), (55.09, 11.11, MAX_RES_MP + 1)])
ellenoriz(f"res > MAX_RES_MP ({MAX_RES_MP} mp): nincs atkeles", iranyok(d, FERDE), [])
d = nyom([(55.11, 11.09, 0), (55.09, 11.11, MAX_RES_MP)])
ellenoriz("res == MAX_RES_MP: atkeles (a hatar zart)", iranyok(d, FERDE), ["DK"])

# 6. szelessegi kor: a regi szabaly (elotte < lat <= utana -> eszak)
d = nyom([(55.39, 11.0), (55.40, 11.0), (55.41, 11.0), (55.40, 11.0), (55.39, 11.0)])
ellenoriz("szelessegi kor: a vonalon fekvo pont az eszaki oldal",
          iranyok(d, SZEL), ["észak", "dél"])
ellenoriz("szelessegi kor = a regi, szelesseg-alapu hivas (atkelesek(df, 55.40))",
          atkelesek(d, 55.40).to_csv(index=False), atkelesek(d, SZEL).to_csv(index=False))
d = nyom([(55.39, 10.59), (55.41, 10.59)])
ellenoriz("szelessegi kor: a nyugati vegen kivul", iranyok(d, SZEL), [])
d = nyom([(55.39, 10.60), (55.41, 10.60), (55.39, 11.35), (55.41, 11.35)], lepes=10)
ellenoriz("szelessegi kor: pontosan a vegpontok hosszusagan (zart hatar)",
          iranyok(d, SZEL), ["észak", "dél", "észak"])
ellenoriz("KAPUK alak: szelessegi kornel (lat, lon0, lon1)", SZEL.ertek, (55.40, 10.60, 11.35))

# 7. forditott vegpontsorrend + felcserelt iranynevek = ugyanaz, a vonalon fekvo
#    pontokkal egyutt (a besorolas a kanonikus iranyhoz kotott)
FORD = Kapu("szel", (55.40, 11.35), (55.40, 10.60), ("dél", "észak"))
d = nyom([(55.39, 11.0), (55.40, 11.0), (55.41, 11.0), (55.40, 11.0), (55.39, 11.0),
          (55.40, 11.0), (55.40, 11.01)])
ellenoriz("forditott vegpontok: azonos atkelesek",
          atkelesek(d, FORD).to_csv(index=False), atkelesek(d, SZEL).to_csv(index=False))
FERDE_F = Kapu("ferde", (55.2, 11.2), (55.0, 11.0), ("DK", "ÉNy"))
d = nyom([(55.12, 11.08), (55.10, 11.10), (55.08, 11.12), (55.10, 11.10), (55.12, 11.08)])
ellenoriz("forditott ferde szakasz, vonalon fekvo ponttal",
          atkelesek(d, FERDE_F).to_csv(index=False), atkelesek(d, FERDE).to_csv(index=False))

# 8. delibab-kapu: nyugat fele haladva az elso iranynev
d = nyom([(54.60, 11.17), (54.60, 11.13), (54.60, 11.17)])
ellenoriz("delibab-kapu: nyugat, majd kelet", iranyok(d, DELI), ["nyugat", "kelet"])
d = nyom([(54.40, 11.17), (54.40, 11.13)])
ellenoriz("delibab-kapu: a deli vegponton kivul", iranyok(d, DELI), [])

# 9. ket kulonbozo hajo egymas utani sorai nem alkotnak part
d = pd.concat([nyom([(55.12, 11.08)], mmsi=1), nyom([(55.08, 11.12)], mmsi=2)])
ellenoriz("kulonbozo MMSI-k pozicioi kozott nincs atkeles", iranyok(d, FERDE), [])
d = pd.concat([nyom([(55.12, 11.08), (55.08, 11.12)], mmsi=7),
               nyom([(55.08, 11.12), (55.12, 11.08)], mmsi=3)])
a = atkelesek(d, FERDE)
ellenoriz("ket hajo: MMSI szerint rendezve, mindketto egyszer",
          list(zip(a["MMSI"], a["irany"])), [(3, "ÉNy"), (7, "DK")])

print("\nKonfiguracio:")
ellenoriz("KAPUK: a korabbi, kodba irt szotarral azonos (ertek es sorrend)",
          list(kv.KAPUK.items()),
          [("Nagy-Balti-öv", (55.40, 10.60, 11.35)), ("Øresund", (56.07, 12.40, 12.85))])
kapuk = kv.betolt()
ellenoriz("kapuk.json: minden kapunak van kifele-iranya az iranyai kozul",
          all(k.kifele in k.iranyok for k in kapuk), True)
with tempfile.TemporaryDirectory() as tmp:
    rossz = Path(tmp) / "rossz.json"
    for leiras, kapu_lista in (
            ("ismetlodo nev", [{"nev": "x", "a": [1, 1], "b": [2, 2]}] * 2),
            ("kifele nem irany", [{"nev": "x", "a": [1, 1], "b": [2, 2], "kifele": "fel"}]),
            ("egybeeso vegpontok", [{"nev": "x", "a": [1, 1], "b": [1, 1]}]),
            ("forditott hosszusag", [{"nev": "x", "szelesseg": 55, "hosszusag": [11, 10]}])):
        rossz.write_text(json.dumps({"kapuk": kapu_lista}), encoding="utf-8")
        try:
            kv.betolt(rossz)
            ellenoriz(f"hibas konfig elutasitva: {leiras}", "elfogadva", "ValueError")
        except ValueError:
            ellenoriz(f"hibas konfig elutasitva: {leiras}", "ValueError", "ValueError")

# A bbox-eloszures nem vagja le a folyoso szakaszon beluli reszet: minden
# folyosocella kozeppontja, amelynek vetulete a szakaszra esik, a bboxban van.
for k in kapuk:
    la0, la1, lo0, lo1 = k.bbox()
    kozep = np.array([h3.cell_to_latlng(h3.int_to_str(c)) for c in kv.folyoso(k)])
    _, bent = k.oldal_es_bent(kozep[:, 0], kozep[:, 1])
    kint = ~((kozep[:, 0] >= la0) & (kozep[:, 0] <= la1)
             & (kozep[:, 1] >= lo0) & (kozep[:, 1] <= lo1))
    ellenoriz(f"bbox lefedi a folyoso szakaszon beluli reszet: {k.nev}",
              int((bent & kint).sum()), 0)

print(f"\n{eredmeny['ok']} OK, {eredmeny['hiba']} HIBA")
sys.exit(1 if eredmeny["hiba"] else 0)
