"""
A javitas-csomag (dolgozat/munka/javitasok_ellenorzott.json) olvashato
attekintoje a hallgato tetelenkenti jovahagyasahoz.

Kimenet:
  dolgozat/munka/javitasok_attekintes.md   csoportonkent egy tablazat (regi -> uj,
                                           a kulonbseg kiemelve), az uj bekezdesek
                                           teljes szovege, a kimaradt / elutasitott
                                           tetelek, a Kiel-bekezdesek listaja
  dolgozat/munka/kiel_bekezdesek.csv       a Kiel-esetet emlito bekezdesek
                                           (bekezdesek_v2.txt szamozasa)

Ellenorzesek:
  1. Minden "regi" pontosan egyszer szerepel-e a bekezdesek_v2.txt megfelelo
     bekezdeseben - eredeti szovegen, es a javitas_beiras.py sorrendjeben
     (azonos bekezdesen belul a korabbi cserek utan) is.
  2. Az uj bekezdesek szamai: szamok.md, a forras-mezoben megnevezett fajlok,
     es az adatbol ujraszamolt ertekek (pipeline_napok.csv + napi_sorok.csv,
     szerver_napok_jun_aug.csv, futasok.csv, a 07-15-i Parquet DuckDB-vel,
     a megrakottsag.py fuggvenyei a fagyasztott monitorallapoton).
  3. (--docx) Csak olvasva: benne van-e mar a cserek uj szovege es az uj
     bekezdesek a megadott docx elfogadott nezeteben.

Csak olvas; a docx-et es a fagyasztott mappat nem modositja.

Hasznalat:
    python javitasok_attekintes.py
    python javitasok_attekintes.py --docx dolgozat/szakdolgozat_teljes_piszkozat.docx
"""

import argparse
import csv
import difflib
import html
import inspect
import json
import re
import statistics
import sys
import zipfile
from collections import OrderedDict, defaultdict
from datetime import datetime
from pathlib import Path

import duckdb
import pandas as pd

from utak import GYOKER, KIMENET, ADAT

MUNKA = GYOKER / "dolgozat" / "munka"
FAGY = KIMENET / "fagyasztas_2026-10-22" / "monitor"

# A Kiel-eset kikerul (a hallgato dontese, 2026-10-28). A 3.5 es a 4.4 teljes
# egeszeben a Kiel-esetrol szol; a feladat a J-2, J-3, J-8 tetelt nevesiti.
KIEL_SZAKASZOK = ("3.5 ", "4.4 ")
KIEL_TETEL_RE = re.compile(r"\bJ-(2|3|8)\b")
# kozvetlen utalas a Kiel-esetre (a lezaras forrasai is: Implenia, WSA NOK, Rader Hochbrucke)
KIEL_KOZVETLEN = re.compile(r"Kiel|Rendsburg|Nord-Ostsee|\bNOK\b|Rader|Implenia", re.I)
# csak kozvetett jel: mas lezarasra (pl. issue) vagy mas placebo-tesztre is vonatkozhat
KIEL_KOZVETETT = re.compile(r"lezár|placebo", re.I)
# a backtest szintetikus esemenyenek neve; a szam marad, csak az elnevezes kotodik Kielhez
KIEL_NEV = re.compile(r"Kiel-(?:méretű|eset \()", re.I)

# Az "egyenlo" szakaszok roviditese a diffben: ennel hosszabb valtozatlan
# szovegbol az eleje es a vege marad (KIVAG_MARAD karakter), hogy a valtozas latsszon.
KIVAG_HATAR = 160
KIVAG_MARAD = 60
# Ket valtozas kozti ennyi (vagy kevesebb) karakteres egyezo szo osszevonodik a valtozassal.
OSSZEVON = 3
# Ennel kisebb egesz szamot nem vetunk ossze az ujraszamolt ertekekkel, mert
# veletlenul is egyezhet (pl. 2, 5, 20); ezeket fajlban / forras-mezoben keressuk.
KIS_EGESZ = 30
# A [478] szovege: legfeljebb ennyi napi ertek eseten a P95 (linearis interpolacio)
# a ket legnagyobb ertek koze esik.
P95_NAPOK = 20

HONAP = ("január|február|március|április|május|június|július|augusztus|"
         "szeptember|október|november|december")
SZAKASZ_RE = re.compile(r"\b\d+(?:\.\d+)+\.?")              # 2.4.5, 4.6
DATUM_RE = re.compile(rf"\b(?:19|20)\d{{2}}(?!\d)\.?(?: (?:{HONAP})\w* \d{{1,2}}\.?)?|(?:{HONAP})\w* \d{{1,2}}\b")
SZAM_RE = re.compile(r"(?<![^\W\d_])\d+(?:[   ]\d{3})*(?:,\d+)?")
UT_RE = re.compile(r"[\w./=-]+\.(?:csv|json|py|md|txt|log)\b")


# ---------------------------------------------------------------- beolvasas

def bekezdesek(ut: Path) -> dict:
    pat = re.compile(r"^\[(\d+)\] \(([^)]*)\) ?(.*)$")
    ki = {}
    with open(ut, encoding="utf-8") as f:
        for sor in f:
            m = pat.match(sor.rstrip("\n"))
            if m:
                ki[int(m.group(1))] = (m.group(2), m.group(3))
    return ki


def szakasz(b, pid) -> str:
    return b[pid][0].split(" | ")[0] if pid in b else "?"


# ---------------------------------------------------------------- Kiel

def kiel_jel(szoveg: str) -> str:
    """'kozvetlen' | 'nev' | 'kozvetett' | ''"""
    if KIEL_KOZVETLEN.search(KIEL_NEV.sub("", szoveg)):
        return "kozvetlen"
    if KIEL_NEV.search(szoveg):
        return "nev"
    if KIEL_KOZVETETT.search(szoveg):
        return "kozvetett"
    return ""


def kiel_csere(v, b) -> str:
    sz = szakasz(b, v["id"])
    sajat = kiel_jel(v["regi"] + " " + v["uj"])
    if KIEL_TETEL_RE.search(v["tetel"]) or sz.startswith(KIEL_SZAKASZOK) or sajat == "kozvetlen":
        return "KIEL – kikerül"
    if sajat == "nev":
        return "KIEL-név (a backtest „Kiel-méretű” eseménye – átnevezendő, a szám marad)"
    bek = kiel_jel(b[v["id"]][1]) if v["id"] in b else ""
    if sajat == "kozvetett" or bek == "kozvetlen":
        return "KIEL? – Kiel-bekezdésben / lezárás-utalás, ellenőrizendő"
    return ""


def kiel_uj(u, b) -> str:
    sz = szakasz(b, u["utan_id"])
    j = kiel_jel(u["szoveg"])
    if KIEL_TETEL_RE.search(u["tetel"]) or sz.startswith(KIEL_SZAKASZOK) or j == "kozvetlen":
        return "KIEL – kikerül"
    if j:
        return "KIEL? – ellenőrizendő"
    return ""


def kiel_lista(b):
    sorok = []
    for pid, (sz, t) in b.items():
        fo = sz.split(" | ")[0]
        kulcs = sorted({m.group(0) for m in KIEL_KOZVETLEN.finditer(t)} |
                       {m.group(0) for m in KIEL_KOZVETETT.finditer(t)})
        if fo.startswith(KIEL_SZAKASZOK):
            kat = "3.5 / 4.4 alfejezet (teljes egészében Kiel)"
        elif kiel_jel(t) == "kozvetlen":
            kat = "közvetlen említés"
        elif kiel_jel(t) == "nev":
            kat = "csak a „Kiel-méretű” backtest-elnevezés"
        elif kiel_jel(t) == "kozvetett":
            kat = "csak lezár*/placebo (ellenőrizendő)"
        else:
            continue
        sorok.append({"id": pid, "szakasz": sz, "kategoria": kat, "kulcsszavak": " ".join(kulcs),
                      "szoveg_eleje": t[:140]})
    return sorok


# ---------------------------------------------------------------- egyezes

def egyezes(valt, b):
    """(eredeti elofordulas, sorrendi elofordulas) cserenkent, a javitas_beiras.py logikajaval."""
    ki = {}
    jelen = {}
    for i, v in sorted(enumerate(valt), key=lambda x: x[1]["id"]):  # stabil: azonos id-n belul a JSON-sorrend
        pid = v["id"]
        if pid not in b:
            ki[i] = (None, None)
            continue
        jelen.setdefault(pid, b[pid][1])
        db0 = b[pid][1].count(v["regi"])
        db = jelen[pid].count(v["regi"])
        if db == 1:
            jelen[pid] = jelen[pid].replace(v["regi"], v["uj"], 1)
        ki[i] = (db0, db)
    return ki


# ---------------------------------------------------------------- docx (csak olvasas)

def docx_bekezdesek(ut: Path):
    x = zipfile.ZipFile(ut).read("word/document.xml").decode("utf-8")
    x = re.sub(r"<w:del\b.*?</w:del>", "", x, flags=re.S)
    n = lambda s: re.sub(r"\s+", " ", s).strip()
    p = [n(html.unescape("".join(re.findall(r"<w:t(?: [^>]*)?>([^<]*)</w:t>", q))))
         for q in re.findall(r"<w:p[ >].*?</w:p>", x, flags=re.S)]
    rev = len(re.findall(r"<w:ins ", x))
    return p, rev


def md_nelkul(s):
    return re.sub(r"\s+", " ", re.sub(r"\*\*?([^*]+)\*\*?", r"\1", s)).strip()


# ---------------------------------------------------------------- szamok

def ertek(tok: str) -> float:
    return float(re.sub(r"[   ]", "", tok).replace(",", "."))


def tizedes(tok: str) -> int:
    return len(tok.split(",")[1]) if "," in tok else 0


def szamok_kinyer(s: str):
    s = SZAKASZ_RE.sub(" ", DATUM_RE.sub(" ", s))
    return [m.group(0) for m in SZAM_RE.finditer(s)]


def valtozatok(tok: str):
    puszta = re.sub(r"[   ]", "", tok)
    v = {tok, puszta, puszta.replace(",", ".")}
    egesz, _, tiz = puszta.partition(",")
    if len(egesz) > 3:
        ezres = f"{int(egesz):,}"
        v |= {ezres + ("." + tiz if tiz else ""), ezres.replace(",", " ") + ("," + tiz if tiz else "")}
    return v


def keres(tok: str, szoveg: str) -> bool:
    for v in valtozatok(tok):
        if re.search(rf"(?<![\d.,]){re.escape(v)}(?!\d)", szoveg):
            return True
    return False


def szamok_md(ut: Path):
    """(sorszam, szoveg, athuzott-resz) a szamok.md soraira."""
    ki = []
    with open(ut, encoding="utf-8") as f:
        for i, s in enumerate(f, 1):
            ath = " ".join(re.findall(r"~~(.*?)~~", s))
            ki.append((i, re.sub(r"~~.*?~~", " ", s), ath))
    return ki


def forras_fajlok(forras: str):
    jeloltek = []
    for m in UT_RE.findall(forras):
        nev = Path(m).name
        if nev == "szamok.md":  # kulon oszlopkent mar szerepel
            continue
        for alap in (GYOKER / m, GYOKER / "scripts" / nev, KIMENET / nev, KIMENET / "eles_uzem" / nev,
                     MUNKA / nev, FAGY / nev, GYOKER / "dolgozat" / nev):
            if alap.exists() and alap.is_file() and alap.stat().st_size < 20 * 2**20:
                jeloltek.append(alap)
                break
    return list(OrderedDict.fromkeys(jeloltek))


def adatbol() -> list:
    """Az uj bekezdesek szamai az adatbol ujraszamolva: (cimke, ertek)."""
    e = []
    pn = pd.read_csv(KIMENET / "pipeline_napok.csv", dtype={"nap": str})
    pn = pn[(pn.statusz == "validalt") & (pn.nap <= "2026-10-06")].drop_duplicates("nap", keep="last")
    ns = pd.read_csv(KIMENET / "eles_uzem" / "napi_sorok.csv", dtype={"nap": str})
    ns = ns[ns.nap >= "2026-10-07"].drop_duplicates("nap", keep="last")
    nyers = pd.concat([pn[["nap", "nyers_sor"]], ns[["nap", "nyers_sor"]]])
    zip_mib = pn.zip_mib.sum() + ns.zip_mib.sum()
    dedup144 = pn.dedup_sor.sum() + ns.dedup_sor.sum()
    mx = nyers.loc[nyers.nyers_sor.idxmax()]
    e += [("napok, 128 + 16", len(pn) + len(ns)), ("napok, helyi tároló", len(pn)),
          ("nyers sor, 144 nap", nyers.nyers_sor.sum()),
          ("ZIP, 144 nap, GiB", zip_mib / 1024),
          ("ismétlés %, 144 nap", (1 - dedup144 / nyers.nyers_sor.sum()) * 100),
          ("medián nyers sor / nap, millió, 144 nap", statistics.median(nyers.nyers_sor) / 1e6),
          (f"max. nyers sor / nap, millió ({mx.nap})", mx.nyers_sor / 1e6),
          ("Parquet, 128 nap, GiB", pn.parquet_mib.sum() / 1024),
          ("Parquet / ZIP %, 128 nap", pn.parquet_mib.sum() / pn.zip_mib.sum() * 100),
          ("pozíció nélküli (h3) dedup. sor %, 128 nap", pn.h3_nelkuli_sor.sum() / pn.dedup_sor.sum() * 100)]
    sz = pd.read_csv(KIMENET / "szerver_napok_jun_aug.csv")
    e += [("szerver-késés min., óra", sz.keses_ora.min()), ("szerver-késés max., óra", sz.keses_ora.max())]
    fu = pd.read_csv(KIMENET / "eles_uzem" / "futasok.csv")
    fu = fu[fu.event == "schedule"]
    e += [("ütemezett futás, db", len(fu)), ("ütemezett futásidő min., mp", fu.futasido_mp.min()),
          ("ütemezett futásidő max., mp", fu.futasido_mp.max())]
    pq = KIMENET / "tarolo" / "ev=2026" / "ho=07" / "aisdk-2026-07-15.parquet"
    if pq.exists():
        con = duckdb.connect()
        t = con.execute(f"""SELECT "Type of mobile", sum(dup_db), count(DISTINCT MMSI)
                            FROM read_parquet('{pq.as_posix()}') GROUP BY 1""").fetchall()
        ossz = sum(x[1] for x in t)
        e += [("07-15 nyers sor", ossz), ("07-15 adótípusok száma", len(t)),
              ("07-15 különböző MMSI", con.execute(
                  f"SELECT count(DISTINCT MMSI) FROM read_parquet('{pq.as_posix()}')").fetchone()[0])]
        for nev, db, mmsi in t:
            e += [(f"07-15 {nev} sor %", db / ossz * 100), (f"07-15 {nev} sor", db), (f"07-15 {nev} MMSI", mmsi)]
        kicsi = sum(db for nev, db, _ in t if nev in ("Search and Rescue Transponder", "Emergency PIRB"))
        e.append(("07-15 SART + EPIRB sor", kicsi))
    z = ADAT / "aisdk-2026-07-15.zip"
    if z.exists():
        with zipfile.ZipFile(z) as zf, zf.open(zf.namelist()[0]) as f:
            e.append(("nyers CSV oszlopszám (07-15)", len(f.readline().decode("utf-8-sig").split(","))))
    if (FAGY / "merules_tortenet.csv").exists():
        sys.path.insert(0, str(GYOKER / "scripts"))
        import megrakottsag as m
        tort = pd.read_csv(FAGY / "merules_tortenet.csv", dtype={"nap": str})
        resz = pd.read_csv(FAGY / "atkelesek_reszletes.csv", dtype={"datum": str})
        r = m.relativ(resz, m.hajo_max(tort))
        for cs, kusz in m.kuszobok(r).items():
            g = r[r.csoport == cs]
            ert = int(g.ertekelheto.sum())
            e += [(f"Otsu-küszöb, {cs}", kusz), (f"{cs}-átkelés, 144 nap", len(g)),
                  (f"{cs}, értékelhető átkelés", ert), (f"{cs}, értékelhető %", ert / len(g) * 100),
                  (f"{cs}, értékelhető átkelés ≤ {P95_NAPOK} napi értékű hajóval %",
                   int((g.ertekelheto & (g.napok <= P95_NAPOK)).sum()) / ert * 100)]
        e += [("Otsu-osztályok (otsu() binek)", inspect.signature(m.otsu).parameters["binek"].default),
              ("max. percentilis", m.MAX_PERCENTILIS),
              ("hihető merülés alsó határa, m", m.HIHETO_MIN), ("hihető merülés felső határa, m", m.HIHETO_MAX)]
    return e


def szam_ellenoriz(u, szmd, adat, kezi):
    """Az uj bekezdes szamai: [(tok, statusz, hol)]."""
    ki = []
    if u["stilus"] == "hivatkozas":
        for tok in szamok_kinyer(u["szoveg"].split("http")[0]):
            ok = keres(tok, u["forras"])
            st, hol = ("ok", "a forrás-mező (Crossref / PDF-adat)") if ok else ("NINCS", "a forrás-mezőben sincs")
            k = kezi.get((u["utan_id"], u["sorrend"], tok))
            if k:
                st, hol = ("kézi-ok" if k[0] == "egyezik" else "kézi-eltér"), f"kézzel: {k[1]}; {hol}"
            ki.append((tok, st, hol))
        return ki
    fajlok = forras_fajlok(u["forras"])
    for tok in szamok_kinyer(u["szoveg"]):
        hol, figy = [], ""
        v, d = ertek(tok), tizedes(tok)
        kicsi = d == 0 and v < KIS_EGESZ
        for f in fajlok:
            if keres(tok, f.read_text(encoding="utf-8", errors="replace")):
                hol.append(f"fájl: {f.relative_to(GYOKER).as_posix()}")
                break
        # minden egyezo ujraszamolt erteket kiirunk: kis szamnal tobb is lehet, es
        # a cimkebol latszik, melyik a valodi forras
        talalt = [f"{c} = {fmt(x)}" for c, x in adat if round(float(x), d) == round(v, d)]
        if talalt:
            hol.append("újraszámolva: " + " | ".join(talalt[:3])
                       + (f" (+{len(talalt) - 3})" if len(talalt) > 3 else ""))
        if not kicsi:  # kis egesz a szamok.md-ben szinte mindig elofordul, nem bizonyit
            sor = [i for i, s, _ in szmd if keres(tok, s)]
            if sor:
                hol.append(f"szamok.md {sor[0]}. sor" + (f" (+{len(sor) - 1})" if len(sor) > 1 else ""))
            elif any(keres(tok, a) for _, _, a in szmd):
                figy = "szamok.md-ben csak áthúzva (régi érték)"
        if not hol and keres(tok, u["forras"]):
            hol.append("csak a forrás-mezőben (eseti futás kimenete)")
        statusz = "ok" if any(h.startswith(("újra", "szamok", "fájl")) for h in hol) else \
                  ("forrás-mező" if hol else ("kis egész" if kicsi else "NINCS"))
        if figy:
            hol.append(figy)
        k = kezi.get((u["utan_id"], u["sorrend"], tok))
        if k:
            statusz = "kézi-ok" if k[0] == "egyezik" else "kézi-eltér"
            hol.insert(0, f"kézzel: {k[1]}")
        ki.append((tok, statusz, "; ".join(hol) or "nem található"))
    return ki


def kezi_olvas(ut: Path) -> dict:
    """Kezi ellenorzesek: (utan_id, sorrend, szam) -> (eredmeny, megjegyzes)."""
    if not ut or not ut.exists():
        return {}
    with open(ut, encoding="utf-8") as f:
        return {(int(r["utan_id"]), int(r["sorrend"]), r["szam"]): (r["eredmeny"], r["megjegyzes"])
                for r in csv.DictReader(f)}


JELOLES = {"ok": "egyezik", "kézi-ok": "egyezik (kézi ellenőrzés)", "kézi-eltér": "⚠ ELTÉR (kézi ellenőrzés)",
           "forrás-mező": "⚠ csak a forrás-mezőben", "kis egész": "– kis egész, a szövegkörnyezetből",
           "NINCS": "⚠ NEM TALÁLHATÓ"}


def fmt(x) -> str:
    x = float(x)
    return f"{x:,.0f}".replace(",", " ") if x == int(x) and abs(x) >= 1000 else (
        f"{int(x)}" if x == int(x) else f"{x:.4f}".rstrip("0").replace(".", ","))


# ---------------------------------------------------------------- markdown

def esc(s: str) -> str:
    s = re.sub(r"\s*\n\s*", " ", s)
    for c in "\\`*_~|[]":
        s = s.replace(c, "\\" + c)
    return s.replace("<", "&lt;").replace(">", "&gt;")


def rovidit(s: str) -> str:
    if len(s) <= KIVAG_HATAR:
        return esc(s)
    return esc(s[:KIVAG_MARAD]) + " […] " + esc(s[-KIVAG_MARAD:])


def kiemel(regi: str, uj: str) -> str:
    a, b = re.findall(r"\s+|\S+", regi), re.findall(r"\s+|\S+", uj)
    resz = [(op == "equal", "".join(a[i1:i2]), "".join(b[j1:j2]))
            for op, i1, i2, j1, j2 in difflib.SequenceMatcher(None, a, b, autojunk=False).get_opcodes()]
    # ket valtozas kozti rovid egyezes (szokoz, nevelo) a valtozas resze lesz, kulonben
    # a kiemeles szavankent szetesik
    ossz = []
    for i, (egyen, ra, ub) in enumerate(resz):
        kozte = egyen and 0 < i < len(resz) - 1 and len(ra.strip()) <= OSSZEVON
        if ossz and not ossz[-1][0] and (not egyen or kozte):
            ossz[-1] = (False, ossz[-1][1] + ra, ossz[-1][2] + (ra if egyen else ub))
        else:
            ossz.append((egyen, ra, ub))
    ki = []
    for egyen, ra, ub in ossz:
        if egyen:
            ki.append(rovidit(ra))
            continue
        el = " " if (ra or ub)[:1].isspace() else ""
        ut = " " if (ra or ub)[-1:].isspace() else ""
        resz = []
        if ra.strip():
            resz.append(f"~~{esc(ra.strip())}~~")
        if ub.strip():
            resz.append(f"**{esc(ub.strip())}**")
        ki.append(el + " ".join(resz) + ut)
    return "".join(ki)


def tartomany(idk):
    idk = sorted(idk)
    ki, eleje = [], None
    for i, x in enumerate(idk):
        if eleje is None:
            eleje = x
        if i + 1 == len(idk) or idk[i + 1] != x + 1:
            ki.append(f"{eleje}" if eleje == x else f"{eleje}–{x}")
            eleje = None
    return ", ".join(ki)


# ---------------------------------------------------------------- main

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--javitasok", type=Path, default=MUNKA / "javitasok_ellenorzott.json")
    ap.add_argument("--eredmeny", type=Path, default=MUNKA / "javitasok_eredmeny.json")
    ap.add_argument("--bekezdesek", type=Path, default=MUNKA / "bekezdesek_v2.txt")
    ap.add_argument("--szamok", type=Path, default=GYOKER / "szamok.md")
    ap.add_argument("--docx", type=Path, default=GYOKER / "dolgozat" / "szakdolgozat_teljes_piszkozat.docx",
                    help="csak olvasva: benne vannak-e mar a cserek (ures: kihagyja)")
    ap.add_argument("--kezi", type=Path, default=MUNKA / "javitasok_kezi_ellenorzes.csv",
                    help="kezi szamellenorzesek (utan_id, sorrend, szam, eredmeny, megjegyzes)")
    ap.add_argument("--ki", type=Path, default=MUNKA / "javitasok_attekintes.md")
    ap.add_argument("--kiel-ki", type=Path, default=MUNKA / "kiel_bekezdesek.csv")
    args = ap.parse_args()

    j = json.loads(args.javitasok.read_text(encoding="utf-8"))
    er = json.loads(args.eredmeny.read_text(encoding="utf-8"))
    valt, ujb = j["valtozasok"], j["uj_bekezdesek"]
    b = bekezdesek(args.bekezdesek)
    szmd = szamok_md(args.szamok)
    print(f"Beolvasva: {len(valt)} csere, {len(ujb)} új bekezdés, {len(b)} bekezdés (v2), "
          f"{len(szmd)} szamok.md-sor")

    egy = egyezes(valt, b)
    kiel_v = [kiel_csere(v, b) for v in valt]
    kiel_u = [kiel_uj(u, b) for u in ujb]
    adat = adatbol()
    print(f"Újraszámolt érték: {len(adat)}")
    kezi = kezi_olvas(args.kezi)
    szam_u = [szam_ellenoriz(u, szmd, adat, kezi) for u in ujb]

    docx_v = docx_u = None
    if args.docx and str(args.docx) and args.docx.exists():
        dp, rev = docx_bekezdesek(args.docx)
        nagy, halmaz = " ".join(dp), set(dp)
        docx_v = [re.sub(r"\s+", " ", v["uj"]).strip() in nagy for v in valt]
        # a lista-bekezdes a docx-ben szo szerinti "–" elotaggal all
        docx_u = [md_nelkul(u["szoveg"]) in halmaz or "–" + md_nelkul(u["szoveg"]) in halmaz for u in ujb]
        docx_info = (args.docx, len(dp), rev)

    # ---- kiel lista
    kl = kiel_lista(b)
    with open(args.kiel_ki, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(kl[0]))
        w.writeheader()
        w.writerows(kl)

    # ---- markdown
    L = []
    o = L.append
    csoportok = list(OrderedDict.fromkeys(v["csoport"] for v in valt))
    nem_egy = [i for i, (d0, d) in egy.items() if d0 != 1 or d != 1]
    n_kiel_v = sum(k.startswith("KIEL –") for k in kiel_v)
    n_kiel_u = sum(k.startswith("KIEL –") for k in kiel_u)
    o("# Javítás-csomag: áttekintő a tételenkénti jóváhagyáshoz")
    o("")
    o(f"Generálva: {datetime.now():%Y-%m-%d %H:%M}, `scripts/javitasok_attekintes.py`. Bemenet: "
      f"`{args.javitasok.relative_to(GYOKER).as_posix()}` ({len(valt)} csere, {len(ujb)} új bekezdés), "
      f"`{args.bekezdesek.relative_to(GYOKER).as_posix()}`, `szamok.md`, `{args.eredmeny.relative_to(GYOKER).as_posix()}`. "
      "A bekezdés-azonosítók a `bekezdesek_v2.txt` (2026-10-26) számozását követik.")
    o("")
    if docx_v is not None:
        ut, np_, rev = docx_info
        o("## Fontos: a csomag már benne van a docx-ben")
        o("")
        o(f"A `{ut.relative_to(GYOKER).as_posix()}` (csak olvasva, {np_} bekezdés, {rev} nyitott beszúrás) elfogadott nézetében "
          f"a {len(valt)} csere új szövegéből **{sum(docx_v)}**, a {len(ujb)} új bekezdésből **{sum(docx_u)}** már szerepel. "
          "A naplo.md 2026-10-27/28-i bejegyzése szerint a csomagot a `javitas_beiras.py` beírta "
          "(„Valtoztatas: 139, beirva: 139 … Uj bekezdes: 28, beszurva: 28”), 2026-10-28-án pedig "
          "a követett változtatásokat elfogadták (779 → 0). A jóváhagyás ezért utólagos: amit kihúzol "
          "vagy átírsz, azt a docx-ben vissza kell csinálni. A 4. fázis beírása a mostani docx-re "
          "nem alkalmazható (a régi szövegek már nincsenek benne).")
        o("")
    o("## Összesítő")
    o("")
    o("| csoport | csere | ebből KIEL – kikerül | új bekezdés | ebből KIEL – kikerül |")
    o("|---|---|---|---|---|")
    ucs = list(OrderedDict.fromkeys(u["csoport"] for u in ujb))
    for cs in OrderedDict.fromkeys(csoportok + ucs):
        iv = [i for i, v in enumerate(valt) if v["csoport"] == cs]
        iu = [i for i, u in enumerate(ujb) if u["csoport"] == cs]
        o(f"| {esc(cs)} | {len(iv)} | {sum(kiel_v[i].startswith('KIEL –') for i in iv)} | {len(iu)} | "
          f"{sum(kiel_u[i].startswith('KIEL –') for i in iu)} |")
    o(f"| **összesen** | **{len(valt)}** | **{n_kiel_v}** | **{len(ujb)}** | **{n_kiel_u}** |")
    o("")
    o(f"- `regi`-egyezés: {len(valt) - len(nem_egy)}/{len(valt)} csere „régi” szövege pontosan egyszer szerepel a "
      f"megfelelő bekezdésben (eredeti szövegen és a beírás sorrendjében is); nem egyező: {len(nem_egy)} (ld. 3. pont).")
    db = lambda *st: sum(1 for s in szam_u for x in s if x[1] in st)
    nsz, nfm = db("NINCS", "kézi-eltér"), db("forrás-mező")
    o(f"- Az új bekezdések számai: {sum(len(s) for s in szam_u)} szám; egyezik: {db('ok', 'kézi-ok')} "
      f"(ebből kézi ellenőrzéssel {db('kézi-ok')}); ⚠ nem található / eltér: {nsz}; ⚠ csak a forrás-mezőben: {nfm}; "
      f"kis egész, a szövegkörnyezetből: {db('kis egész')} (ld. 2. pont, a számtáblák). Kézi ellenőrzések: "
      f"`{args.kezi.relative_to(GYOKER).as_posix()}`.")
    o("- Jelölések: **KIEL – kikerül**: a Kiel-esetre vonatkozik, beírásra nem javasolt. "
      "**KIEL-név**: csak a backtest „Kiel-méretű” szintetikus eseményének neve, a szám marad, az elnevezés változik. "
      "**KIEL?**: Kiel-bekezdésben vagy lezárás-utalással, kézzel eldöntendő.")
    o("- A „Döntés” oszlopba: **J** (jóváhagyva), **K** (kihúzva) vagy az átírt szöveg.")
    o("- A kiemelés: ~~törölt~~ **új**. A hosszú, változatlan részek rövidítve […].")
    o("")
    o("## 1. Cserék csoportonként")
    sorszam = {i: i + 1 for i in range(len(valt))}
    for cs in csoportok:
        iv = [i for i, v in enumerate(valt) if v["csoport"] == cs]
        o("")
        o(f"### {esc(cs)} ({len(iv)} csere)")
        o("")
        o("| # | bek. | tétel | régi → új | indok | forrás | jelölés | Döntés |")
        o("|---|---|---|---|---|---|---|---|")
        for i in iv:
            v = valt[i]
            d0, d = egy[i]
            jel = []
            if kiel_v[i]:
                jel.append(f"**{esc(kiel_v[i])}**")
            if d0 != 1 or d != 1:
                jel.append(f"⚠ regi: {d0}× / sorrendben {d}×")
            if docx_v is not None and not docx_v[i]:
                jel.append("⚠ az új szöveg nincs a docx-ben")
            o(f"| {sorszam[i]} | [{v['id']}] {esc(szakasz(b, v['id']).split(' ')[0])} | {esc(v['tetel'])} | "
              f"{kiemel(v['regi'], v['uj'])} | {esc(v['indok'])} | {esc(v['forras'])} | {'<br>'.join(jel)} | |")

    o("")
    o("## 2. Új bekezdések")
    for cs in ucs:
        iu = [i for i, u in enumerate(ujb) if u["csoport"] == cs]
        o("")
        o(f"### {esc(cs)} ({len(iu)})")
        for i in iu:
            u = ujb[i]
            hely = b.get(u["utan_id"], ("?", ""))
            o("")
            o(f"#### Ú-{i + 1} · a [{u['utan_id']}] után, {u['sorrend']}. · {u['stilus']} · {esc(u['tetel'])}"
              + (f" · **{kiel_u[i]}**" if kiel_u[i] else ""))
            o("")
            o(f"Hely: {esc(hely[0])}; az előző bekezdés eleje: „{esc(hely[1][:110])}…”"
              + ("" if docx_u is None else ("" if docx_u[i] else " · ⚠ nincs a docx-ben")))
            o("")
            o("> " + u["szoveg"].replace("\n", "\n> "))
            o("")
            o(f"*Indok:* {esc(u['indok'])}")
            o("")
            o(f"*Forrás:* {esc(u['forras'])}")
            if szam_u[i]:
                o("")
                o("| szám | ellenőrzés | hol |")
                o("|---|---|---|")
                for tok, st, hol in szam_u[i]:
                    jel = JELOLES[st]
                    o(f"| {esc(tok)} | {jel} | {esc(hol)} |")

    o("")
    o("## 3. A „régi” szövegek egyezése a bekezdesek_v2.txt-vel")
    o("")
    o("Ellenőrzés: a „regi” pontosan egyszer szerepel-e a megadott bekezdés szövegében, (a) az eredeti szövegen, "
      "(b) a `javitas_beiras.py` sorrendjében, vagyis az ugyanazon bekezdés korábbi cseréi után.")
    o("")
    if not nem_egy:
        o(f"Mind a {len(valt)} csere egyezik (a: 1×, b: 1×).")
    else:
        o("| # | bek. | tétel | eredeti | sorrendben | régi szöveg |")
        o("|---|---|---|---|---|---|")
        for i in nem_egy:
            v = valt[i]
            o(f"| {sorszam[i]} | [{v['id']}] | {esc(v['tetel'])} | {egy[i][0]} | {egy[i][1]} | {rovidit(v['regi'])} |")

    o("")
    o("## 4. Kimaradt / elutasított tételek (javitasok_eredmeny.json)")
    o("")
    ekul = []
    eredeti = {(x["id"], x["regi"]) for x in valt}
    for c in er["csoportok"]:
        for x in c["valtozasok"]:
            if (x["id"], x["regi"]) not in eredeti:
                ekul.append((c["k"], x))
    o(f"Az eredmény-fájl {sum(len(c['valtozasok']) for c in er['csoportok'])} cserét tartalmaz, az ellenőrzött csomag "
      f"{len(valt)}-at. A különbség ({len(ekul)}) a naplo.md 2026-10-27/28-i bejegyzése szerint duplikátum "
      "(„két csoport ugyanazt a D3a-20 javítást írta”):")
    o("")
    for k, x in ekul:
        o(f"- {esc(k)}: [{x['id']}] {esc(x.get('tetel', ''))}: {kiemel(x['regi'], x['uj'])}")
    for c in er["csoportok"]:
        o("")
        o(f"### {esc(c['k'])}: kimaradt {len(c['kihagyott_tetelek'])}, elutasított {len(c['elutasitott'])}")
        o("")
        if c["kihagyott_tetelek"] or c["elutasitott"]:
            o("| típus | tétel | ok |")
            o("|---|---|---|")
            for x in c["kihagyott_tetelek"]:
                o(f"| kimaradt | {esc(x['tetel'])} | {esc(x['ok'])} |")
            for x in c["elutasitott"]:
                o(f"| elutasított | {esc(x['tetel'])} | {esc(x['ok'])} |")
    o("")
    o(f"### Hiányzó csoport: {', '.join(er['hiany'])}")
    o("")
    o("A `hiany` mező szerint a **szakirodalom** csoport nem futott végig (az ellenőrzője a limiten elbukott). "
      "A csomagba csak az a 6 új hivatkozási tétel került be kézi ellenőrzéssel, amelyre a beírt szöveg hivatkozik "
      "(2. pont, „szakirodalom (kezzel ellenorizve 2026-10-28)” csoport). A szerző többi javaslata "
      "(`dolgozat/munka/szakirodalom_szerzo_ellenorizetlen.json`) ellenőrizetlen, és nincs ebben az áttekintőben.")

    o("")
    o("## 5. A Kiel-esetet említő bekezdések (a későbbi, egy körös törléshez)")
    o("")
    o(f"Forrás: `bekezdesek_v2.txt`, kulcsszavak: Kiel, Rendsburg, Nord-Ostsee, NOK, Rader, Implenia, lezár*, placebo. "
      f"Teljes lista szövegrészlettel: `{args.kiel_ki.relative_to(GYOKER).as_posix()}`. Az azonosítók a v2-számozásúak, "
      "a mostani docx-ben az új bekezdések miatt eltolódnak, ezért a törlés előtt friss kinyerés kell.")
    o("")
    kat = defaultdict(list)
    for s in kl:
        kat[s["kategoria"]].append(s["id"])
    o("| kategória | db | bekezdések |")
    o("|---|---|---|")
    for k, ids in kat.items():
        o(f"| {esc(k)} | {len(ids)} | {tartomany(ids)} |")
    o("")
    o("A 3.5 / 4.4 alfejezeten kívüli találatok:")
    o("")
    o("| bek. | szakasz | kategória | kulcsszó | szöveg eleje |")
    o("|---|---|---|---|---|")
    for s in kl:
        if not s["kategoria"].startswith("3.5"):
            o(f"| [{s['id']}] | {esc(s['szakasz'][:60])} | {esc(s['kategoria'])} | {esc(s['kulcsszavak'])} | "
              f"{esc(s['szoveg_eleje'][:110])}… |")
    o("")
    o("Az új bekezdések közül KIEL-jelölésű: " +
      (", ".join(f"Ú-{i + 1} ([{ujb[i]['utan_id']}] után)" for i, k in enumerate(kiel_u) if k) or "nincs") + ".")

    args.ki.write_text("\n".join(L) + "\n", encoding="utf-8")

    # ---- osszefoglalo
    print(f"regi-egyezes: {len(valt) - len(nem_egy)}/{len(valt)} rendben, nem egyezo: {len(nem_egy)}")
    for i in nem_egy:
        print(f"  NEM EGYEZIK #{sorszam[i]} [{valt[i]['id']}] {valt[i]['tetel']}: eredeti {egy[i][0]}x, sorrendben {egy[i][1]}x")
    print(f"KIEL - kikerul: {n_kiel_v} csere, {n_kiel_u} uj bekezdes; "
          f"KIEL-nev: {sum(k.startswith('KIEL-név') for k in kiel_v)}; KIEL?: {sum(k.startswith('KIEL?') for k in kiel_v)} csere, "
          f"{sum(k.startswith('KIEL?') for k in kiel_u)} uj bekezdes")
    print(f"Kiel-bekezdes (v2): {len(kl)} -> {args.kiel_ki}")
    for k, ids in kat.items():
        print(f"  {k}: {len(ids)}")
    print(f"Uj bekezdesek szamai: {sum(len(s) for s in szam_u)}, ebbol egyezik {db('ok', 'kézi-ok')} "
          f"(kezi: {db('kézi-ok')}), csak forras-mezo {nfm}, kis egesz {db('kis egész')}, nem talalhato / elter {nsz}")
    for i, s in enumerate(szam_u):
        for tok, st, hol in s:
            if st not in ("ok", "kézi-ok"):
                print(f"  U-{i + 1} [{ujb[i]['utan_id']}].{ujb[i]['sorrend']} {tok!r}: {st} ({hol})")
    if docx_v is not None:
        print(f"docx (csak olvasva): uj szoveg megvan {sum(docx_v)}/{len(valt)}, uj bekezdes {sum(docx_u)}/{len(ujb)}, "
              f"nyitott beszuras {docx_info[2]}")
    print(f"-> {args.ki}")


if __name__ == "__main__":
    main()
