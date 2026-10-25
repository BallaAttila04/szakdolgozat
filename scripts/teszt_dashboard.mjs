/**
 * A dashboard-sablon JavaScript logikajanak tesztje, valodi bongeszo nelkul
 * (a teszt_terkep.mjs mintajara).
 *
 * Ket resz:
 *  A) Szintetikus adat: a sablon <script> blokkja DOM-csonkon fut, kezzel
 *     ellenorizheto adatokkal. Allitasok a magyar szamformazasra, a
 *     sorozatkepzesre, a monitor-szabaly (alapszint, kuszob, jelzes)
 *     ujraszamolasara, a sav szamolasara, a jelzett napok kiemelesere, az
 *     idoszak-szuresre, a billentyuzetes fokuszra es az ures / hianyzo adat
 *     kezelesere.
 *  B) Valodi adat (ha a docs/dashboard.html es az outputs/ CSV-k megvannak):
 *     a dashboard JS-e a beagyazott adatbol napra pontosan ugyanazt szamolja-e,
 *     mint a monitor.py (outputs/monitor/jelzesek*.csv) es a kapu_elemzes.py
 *     (outputs/kapuk_kiterjesztes/jelzesek.csv).
 *
 * Hasznalat:
 *     node scripts/teszt_dashboard.mjs
 *
 * Kilepesi kod: 0 ha minden allitas teljesul, 1 egyebkent.
 */

import { readFileSync, existsSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

const ITT = dirname(fileURLToPath(import.meta.url));
const GYOKER = join(ITT, "..");

let futott = 0, bukott = 0;
function allit(felteves, leiras) {
  futott++;
  if (felteves) console.log(`  OK    ${leiras}`);
  else { bukott++; console.log(`  BUKIK ${leiras}`); }
}

// --- DOM-csonk -------------------------------------------------------------
// Csak az az API, amit a sablon tenylegesen hasznal: getElementById-vel kert
// elemek innerHTML/textContent/value/hidden mezokkel, esemenykezelokkel.
let elemek;
function elem(id) {
  return {
    id, innerHTML: "", textContent: "", value: "", hidden: false, style: {}, min: "", max: "",
    clientWidth: 720, _attr: {}, _fig: {},
    setAttribute(k, v) { this._attr[k] = String(v); },
    getAttribute(k) { return this._attr[k]; },
    addEventListener(nev, fn) { (this._fig[nev] ||= []).push(fn); },
    dispatch(nev, e = {}) { (this._fig[nev] || []).forEach(fn => fn({ preventDefault() {}, ...e })); },
    getBoundingClientRect: () => ({ width: 720, height: 300, left: 0, top: 0 }),
    focus() {},
  };
}
function dom() {
  elemek = new Map();
  globalThis.document = {
    getElementById(id) { if (!elemek.has(id)) elemek.set(id, elem(id)); return elemek.get(id); },
  };
  globalThis.window = { innerWidth: 1024, addEventListener() {} };
  globalThis.location = { hash: "" };
  globalThis.history = { replaceState() {} };
}
const E = id => elemek.get(id) || document.getElementById(id);

function futtat(html, adat) {
  const m = html.match(/<script>([\s\S]*?)<\/script>/);
  if (!m) throw new Error("Nincs <script> blokk");
  const js = adat === undefined ? m[1] : m[1].replace("/*DASHBOARD_ADAT*/", JSON.stringify(adat));
  dom();
  new Function(js)();
  return globalThis.window.AISDASH;
}

// --- Szintetikus adat ------------------------------------------------------
// 61 nap (06-01 - 07-31). Minden nap, kapunkent, iranyonkent: Tanker 10,
// Teherhajo 20, Kedvtelesi 5 -> "Mindket kapu, kereskedelmi" = 2 x 2 x 30 = 120.
// Zaj: a Nagy-Balti-ov del fele Teherhajo 20 + [0, 1, -1, 2, -2][nap % 5]. Az
// 5 napos ciklus hetente 2-vel tolodik, ezert az alapszint a masik negy ertek
// mediánja, az elteres {0; +1,3; -1,2; +2,1; -2,1}% - a kuszob igy kb. 3,7%.
// 07-15-en az Oresund eszak fele Tanker 40 (+30, kb. +25%): az egyetlen
// jelzett nap.
function szintetikus() {
  const napok = [];
  for (let d = new Date(Date.UTC(2026, 5, 1)); d <= new Date(Date.UTC(2026, 6, 31)); d = new Date(d.getTime() + 86400000))
    napok.push(d.toISOString().slice(0, 10));
  const kapu = ["Nagy-Balti-öv", "Øresund"], irany = ["dél", "észak"], csoport = ["Kedvtelési", "Tanker", "Teherhajó"];
  const sorok = [], megr = [];
  napok.forEach((d, di) => {
    for (let k = 0; k < 2; k++) for (let i = 0; i < 2; i++) {
      let t = 10, th = 20;
      if (d === "2026-07-15" && k === 1 && i === 1) t = 40;
      if (k === 0 && i === 0) th += [0, 1, -1, 2, -2][di % 5];
      sorok.push([di, k, i, 0, 5], [di, k, i, 1, t], [di, k, i, 2, th]);
      if (d !== "2026-06-20") {          // 06-20: van forgalmi adat, de nincs megrakott atkeles
        megr.push([di, k, i, 0, t, t, Math.round(t / 2), t * 1000]);
        megr.push([di, k, i, 1, th, th, Math.round(th / 2), th * 500]);
      }
    }
  });
  const hiv = (nev, tipus) => ({ nev, tipus, kuszob: 0.2, datum: napok.slice(-3),
    ertek: [120, 120, 150], alapszint: [null, 120, 120], elteres: [null, 0, 0.25],
    jelzes: ["nincs alapszint", "normál", "szokatlanul magas"] });
  return {
    epitve_utc: "2026-08-03T04:00:00+00:00", sema_verzio: 1, kiel: ["2026-07-15", "2026-07-16"], utolso_napok: 30,
    szabaly: { alap_hetek: 4, min_alapnap: 3, kuszob_szorzo: 2.0, mad_skala: 1.4826, gordulo_nap: 7 },
    allapot: { utolso_nap: "2026-07-31", elso_nap: "2026-06-01", napok_szama: 61, frissitve_utc: "2026-08-03T03:50:00+00:00",
      kuszob: { "Mindkét kapu": 0.2 }, kuszob_megrakottsag: {}, megrakott_kuszob_relativ_merules: { Tanker: 0.81, "Teherhajó": 0.79 },
      utolso_futas: { ido_utc: "2026-08-03T03:45:00+00:00", statusz: "ok", uzenet: "1 uj nap" } },
    napok,
    forgalom: { dim: ["kapu", "irany", "csoport"], ertekek: ["atkeles"], kapu, irany, csoport, sorok },
    megrakottsag: { dim: ["kapu", "irany", "csoport"], ertekek: ["atkeles", "ertekelheto", "megrakott", "volumenindex"],
      kapu, irany, csoport: ["Tanker", "Teherhajó"], sorok: megr },
    hivatalos: [hiv("Mindkét kapu <b>", "forgalom"), hiv("Megrakott tanker (7 nap)", "megrakottsag")],
    backtest: null, kapuk: null, fajlok: [],
  };
}

const sablon = readFileSync(join(ITT, "dashboard_sablon.html"), "utf8");
console.log("A dashboard-sablon JS logikajanak tesztje\n\nA) Szintetikus adat");
let D;
try { D = futtat(sablon, szintetikus()); }
catch (e) { console.error(`  BUKIK a script futas kozben elszallt: ${e.message}\n${e.stack}`); process.exit(1); }
allit(!!D, "a script lefut DOM-csonkon, es kiadja a tesztfeluletet");

// Magyar szamformazas
const NB = " ";
allit(D.szam(1234567) === `1${NB}234${NB}567`, "ezres tagolas nem tordelo szokozzel: 1 234 567");
allit(D.szam(3.14159, 2) === "3,14", "tizedesvesszo: 3,14");
allit(D.szam(-1500.5, 1) === `−1${NB}500,5`, "negativ szam valodi minuszjellel: −1 500,5");
allit(D.szam(-0.04, 1) === "0,0", "a nullara kerekitett negativ szam elojel nelkul");
allit(D.szam(null) === "–" && D.szam(NaN) === "–" && D.szam(undefined) === "–", "hianyzo ertek: nagykotojel");
allit(D.szazalek(0.1234, 1, true) === "+12,3%" && D.szazalek(-0.05) === "−5,0%", "szazalek elojellel: +12,3%, −5,0%");
allit(D.szazalek(0.00001, 1, true) === "0,0%", "nullara kerekitett szazalek elojel nelkul");
allit(D.datumHosszu("2026-07-15") === "2026. júl. 15., szerda", "magyar datum hetnappal");
allit(D.esc('<b x="1">') === "&lt;b x=&quot;1&quot;&gt;", "HTML-escape a cimkekre");

// Sorozatkepzes es szures
const sum = D.sorozatKepzes(szintetikus().forgalom, 61,
  { kapu: null, irany: null, csoport: ["Teherhajó", "Tanker"] }, "atkeles");
allit(sum[0] === 120 && sum[1] === 121 && sum[44] === 148, "Mindket kapu kereskedelmi: 120, 121, ... 07-15-en 150 - 2 = 148");
const ore = D.forgalomSorozat({ kapu: "Øresund", irany: "észak", csoport: "Tanker" });
allit(ore.ertek[44] === 40 && ore.ertek[0] === 10, "szures kapura, iranyra, csoportra: Øresund eszak Tanker 10 / 40");
const mind = D.forgalomSorozat({ kapu: D.OSSZES_KAPU, irany: D.MIND, csoport: D.MIND });
allit(mind.ertek[0] === 140, "minden hajo, mindket kapu: 140 / nap (a kedvtelesivel)");
allit(D.hivatalosForgalom({ kapu: "Øresund", irany: D.MIND, csoport: "kereskedelmi" }) === "Øresund"
  && D.hivatalosForgalom({ kapu: "Øresund", irany: "észak", csoport: "kereskedelmi" }) === null,
  "a hivatalos monitor-sorozat felismerese");

// A monitor szabalya kezzel szamolhato peldan
const het = ["2026-06-01", "2026-06-08", "2026-06-15", "2026-06-22", "2026-06-29"];
const j1 = D.jelzesSzamol(het, [10, 12, 14, 30, 12]);
allit(j1.alapszint[2] === null && j1.alapnapok[2] === 2, "2 korabbi nap: nincs alapszint (legalabb 3 kell)");
allit(j1.alapszint[3] === 12 && j1.alapszint[4] === 13, "alapszint = median: [10,12,14] -> 12, [10,12,14,30] -> 13");
allit(Math.abs(j1.elteres[4] - (12 / 13 - 1)) < 1e-12, "elteres = ertek / alapszint - 1");
const het8 = Array.from({ length: 8 }, (_, i) => D.napHozzaad("2026-06-01", 7 * i));
const j2 = D.jelzesSzamol(het8, [10, 10, 10, 10, 11, 9, 10, 30]);
allit(Math.abs(j2.kuszob - 2 * 1.4826 * 0.1) < 1e-12, "kuszob = 2 x 1,4826 x MAD (MAD = 0,1)");
allit(j2.jelzes[7] === 1 && j2.jelzes[4] === 0 && j2.jelzes[5] === 0 && j2.jelzes[2] === null,
  "jelzes: +200% magas, ±10% normal, alapszint nelkul null");
const j3 = D.jelzesSzamol(het8, [0, 0, 0, 0, 5, 0, 0, 0]);
allit(j3.alapszint[4] === null && j3.kuszob === null, "nulla alapszintnel nincs elteres es nincs kuszob");

// Sav
const sav = D.savSzamol([100, null, 10], 0.2);
allit(sav[0][0] === 80 && sav[0][1] === 120 && sav[1] === null, "sav = alapszint x (1 ± kuszob), alapszint nelkul nincs");
allit(D.savSzamol([10], 1.5)[0][0] === 0 && D.savSzamol([10], 1.5, false)[0][0] === -5, "darabszamnal a sav alja nem negativ");

// Gordulo osszeg adat nelkuli nappal, paros kerekites
const g = D.gordulo(["2026-06-01", "2026-06-02", "2026-06-03", "2026-06-05", "2026-06-06", "2026-06-07"], [1, 2, 3, 5, 6, 7], 3);
allit(g.napok.join() === "2026-06-03,2026-06-07" && g.ertek.join() === "6,18",
  "3 napos gordulo osszeg: a hianyzo napot (06-04) tartalmazo ablak kimarad");
allit(D.kerekitParos(2.5) === 2 && D.kerekitParos(3.5) === 4 && D.kerekitParos(2.4) === 2 && D.kerekitParos(-0.4) === 0,
  "kerekites mint a pandas .round(0): fel-egesznel paros");
const mt = D.megrSorozat({ mutato: "megrakott", csoport: "Tanker", kapu: D.OSSZES_KAPU, irany: D.MIND });
const mtv = d => mt.ertek[mt.napok.indexOf(d)];
allit(mt.napok[0] === "2026-06-07" && mtv("2026-06-19") === 140 && mtv("2026-06-26") === 120 && mtv("2026-06-27") === 140,
  "megrakottsag: adatos, de atkeles nelkuli nap 0-nak szamit (7 napos osszeg 140 -> 120 -> 140)");
const ar = D.megrSorozat({ mutato: "arany", csoport: "Tanker", kapu: D.OSSZES_KAPU, irany: D.MIND });
allit(ar.ertek.every(v => Math.abs(v - 0.5) < 1e-12), "megrakott arany = megrakott / ertekelheto a 7 napos ablakon (5/10)");

// Idoszak-szures, skala
allit(D.idoszakSzures(het, "2026-06-08", "2026-06-22").join() === "1,2,3", "idoszak-szures tol-ig, zart intervallum");
const sk = D.szepSkala(0, 97);
allit(sk.ticks[0] === 0 && sk.ticks[sk.ticks.length - 1] >= 97 && sk.ticks.length <= 7, "kerek tengelybeosztas: 0-tol 97 folott");

// DOM: attekintes
allit(E("kpi").innerHTML.includes("Mindkét kapu &lt;b&gt;"), "a KPI-csempe a sorozatnevet escape-elve irja ki");
allit(E("kpi").innerHTML.includes("szokatlanul magas") && E("kpi").innerHTML.includes("csempe jelez"),
  "a jelzo sorozat csempeje kiemelt, felirattal");
allit(E("aktiv").innerHTML.includes("+25,0%"), "aktiv jelzes: elteres magyar formaban (+25,0%)");
allit(E("allapotsor").innerHTML.includes("2026-07-31") && E("allapotsor").innerHTML.includes("rendben"),
  "allapotsor: utolso nap es a futas allapota");
allit(E("futas-figyelmeztetes").innerHTML === "", "sikeres futasnal nincs figyelmeztetes");

// DOM: forgalom nezet - a 07-15-i jelzes kiemelve, Kiel-sav, billentyuzet
D.nezetValt("forgalom");
const svg = E("forgalom-abra").innerHTML;
allit(E("nezet-forgalom").hidden === false && E("nezet-attekintes").hidden === true, "fulvaltas: csak az aktiv nezet lathato");
allit((svg.match(/fill="var\(--jel\)"/g) || []).length === 1, "pontosan egy jelzett nap (07-15) kap jelolot");
allit(svg.includes('fill="var(--kiel)"') && svg.includes(">Kiel<"), "a Kiel-lezaras idoszaka jelolve");
allit(svg.includes('fill="var(--sav)"'), "a jelzesi sav kirajzolodik");
E("forgalom-abra").dispatch("keydown", { key: "End" });
allit(E("tooltip").hidden === false && E("tooltip").innerHTML.includes("júl. 31."), "End billentyu: tooltip az utolso napon");
E("forgalom-abra").dispatch("keydown", { key: "ArrowLeft" });
allit(E("tooltip").innerHTML.includes("júl. 30."), "nyil balra: egy nappal korabbra lep");
allit(E("elo").textContent.includes("2026. júl. 30."), "a fokuszalt pont a kepernyoolvasonak is felolvashato");
allit((E("forgalom-tabla").innerHTML.match(/<tr class="kiemelt">/g) || []).length === 1, "a tablazatos nezetben a jelzett nap kiemelt");
E("forgalom-idoszak").dispatch("click", { target: { closest: () => ({ dataset: { napok: "30" } }) } });
allit(D.FORG.tol === "2026-07-02" && D.FORG.ig === "2026-07-31", "30 napos idoszak: 07-02 - 07-31");
allit((E("forgalom-tabla").innerHTML.match(/<tr/g) || []).length === 31, "a tablazat az idoszak 30 napjat (+ fejlec) mutatja");
const sel = E("forgalom-kapu"); sel.value = "Nagy-Balti-öv"; sel.dispatch("change");
allit(!E("forgalom-abra").innerHTML.includes('fill="var(--jel)"'), "kapuvaltas: a Nagy-Balti-ovon nincs jelzett nap");
allit(E("forgalom-alcim").innerHTML.includes("hivatalos monitor-sorozat"), "a kereskedelmi kapu-sorozat hivatalosnak jelolve");

// Ures / hianyzo adat
allit(E("bt-bevezeto").textContent.includes("nem érhetők el"), "hianyzo backtest-blokk: uzenet, nem hiba");
allit(E("kapuk-tartalom").innerHTML.includes("nem érhetők el"), "hianyzo kapu-blokk: uzenet, nem hiba");
const ures = D.idosorAbra("x", { napok: [], sorozatok: [{ ertekek: [] }], fmt: String });
allit(ures.geo === null && ures.svg.includes("nincs adat"), "ures idoszak: szoveges uzenet, nincs diagram");
const hibas = szintetikus();
hibas.allapot.utolso_futas = { ido_utc: "2026-08-03T03:45:00+00:00", statusz: "hiba", uzenet: "nem validalt nap(ok): 2026-07-31: hianyzik" };
hibas.megrakottsag = null;
let D2 = null;
try { D2 = futtat(sablon, hibas); } catch (e) { console.log("    " + e.message); }
allit(!!D2 && E("futas-figyelmeztetes").innerHTML.includes("role=\"alert\""), "hibas futas: figyelmeztetes a lap tetejen");
allit(!!D2 && E("megrakottsag-bevezeto").textContent.length > 0, "hianyzo megrakottsagi tabla mellett is lefut");

// --- B) Valodi adat -------------------------------------------------------
function csvOlvas(ut) {
  const sorok = [];
  for (const sor of readFileSync(ut, "utf8").split(/\r?\n/)) {
    if (!sor) continue;
    const m = []; let mezo = "", idez = false;
    for (let i = 0; i < sor.length; i++) {
      const c = sor[i];
      if (idez) { if (c === '"' && sor[i + 1] === '"') { mezo += '"'; i++; } else if (c === '"') idez = false; else mezo += c; }
      else if (c === '"') idez = true; else if (c === ",") { m.push(mezo); mezo = ""; } else mezo += c;
    }
    m.push(mezo); sorok.push(m);
  }
  const [fej, ...test] = sorok;
  return test.map(r => Object.fromEntries(fej.map((f, i) => [f, r[i]])));
}
const kozel = (js, csv) => (csv === "" ? js === null : js !== null && Math.abs(js - Number(csv)) <= 0.00005 + 1e-9);
function osszevet(nev, js, sorok) {
  let elter = 0;
  const idx = new Map(js.napok.map((d, i) => [d, i]));
  for (const r of sorok) {
    const i = idx.get(r.datum);
    if (i === undefined) { elter++; continue; }
    const jo = js.ertek[i] === Number(r.ertek) && kozel(js.alapszint[i], r.alapszint) && kozel(js.elteres[i], r.elteres)
      && kozel(js.kuszob, r.kuszob) && (["normál", "szokatlanul magas", "szokatlanul alacsony"].includes(r.jelzes)
        ? js.jelzes[i] === { "normál": 0, "szokatlanul magas": 1, "szokatlanul alacsony": -1 }[r.jelzes] : js.jelzes[i] === null);
    if (!jo) { elter++; if (elter <= 3) console.log(`    eltérés: ${nev} ${r.datum} csv=${JSON.stringify(r)} js=${js.ertek[i]},${js.alapszint[i]},${js.elteres[i]},${js.jelzes[i]}`); }
  }
  return { elter, n: sorok.length, extra: js.napok.length - sorok.length };
}

const DASH = join(GYOKER, "docs", "dashboard.html");
const MON = join(GYOKER, "outputs", "monitor");
if (!existsSync(DASH) || !existsSync(join(MON, "jelzesek.csv"))) {
  console.log("\nB) Valodi adat: kihagyva (nincs docs/dashboard.html vagy outputs/monitor/jelzesek.csv)");
} else {
  console.log("\nB) Valodi adat: docs/dashboard.html vs. outputs/ CSV-k");
  const R = futtat(readFileSync(DASH, "utf8"));
  const forg = csvOlvas(join(MON, "jelzesek.csv"));
  let ossz = 0, elt = 0;
  for (const s of [...new Set(forg.map(r => r.sorozat))]) {
    const js = R.forgalomSorozat({ kapu: s, irany: R.MIND, csoport: "kereskedelmi" });
    const e = osszevet(s, js, forg.filter(r => r.sorozat === s));
    ossz += e.n; elt += e.elter + Math.abs(e.extra);
  }
  allit(elt === 0 && ossz === forg.length, `forgalmi jelzesek: ${ossz} sor, ${elt} elteres (jelzesek.csv)`);
  const mf = join(MON, "jelzesek_megrakottsag.csv");
  if (existsSync(mf)) {
    const megr = csvOlvas(mf);
    const DEF = { "Megrakott tanker (7 nap)": ["megrakott", "Tanker"], "Megrakott teherhajó (7 nap)": ["megrakott", "Teherhajó"],
      "Tanker-volumen (7 nap, 1000 m³)": ["volumen", "Tanker"] };
    let o2 = 0, e2 = 0;
    for (const [s, [mutato, csoport]] of Object.entries(DEF)) {
      const js = R.megrSorozat({ mutato, csoport, kapu: R.OSSZES_KAPU, irany: R.MIND });
      const e = osszevet(s, js, megr.filter(r => r.sorozat === s));
      o2 += e.n; e2 += e.elter + Math.abs(e.extra);
    }
    allit(e2 === 0 && o2 === megr.length, `megrakottsagi jelzesek: ${o2} sor, ${e2} elteres (jelzesek_megrakottsag.csv)`);
  }
  const kf = join(GYOKER, "outputs", "kapuk_kiterjesztes", "jelzesek.csv");
  if (existsSync(kf)) {
    const kj = csvOlvas(kf);
    let o3 = 0, e3 = 0;
    for (const s of [...new Set(kj.map(r => r.sorozat))]) {
      const [kapu, irany] = s.split(" | ");
      const js = R.kapuSorozat({ kapu, irany: irany || R.MIND });
      const e = osszevet(s, js, kj.filter(r => r.sorozat === s));
      o3 += e.n; e3 += e.elter + Math.abs(e.extra);
    }
    allit(e3 === 0 && o3 === kj.length, `kiserleti kapuk: ${o3} sor, ${e3} elteres (kapuk_kiterjesztes/jelzesek.csv)`);
  }
  // a KPI-csempek az utolso nap ertekeit mutatjak
  const utolso = forg[forg.length - 1].datum;
  const kpi = E("kpi").innerHTML;
  const jo = forg.filter(r => r.datum === utolso).every(r => kpi.includes(`>${R.szam(Number(r.ertek))}<span class="csempe-egyseg">`));
  allit(jo, `a KPI-csempek a(z) ${utolso} nap ertekeit mutatjak`);
  allit(!/\/\*DASHBOARD_/.test(readFileSync(DASH, "utf8")), "nincs kicsereletlen helyorzo a dashboardban");
  const wff = join(GYOKER, "outputs", "backtest", "walkforward.csv");
  if (existsSync(wff)) {
    const wf = csvOlvas(wff).filter(r => r.valtozat.startsWith("bovulo (min. 21")).map(r => Number(r.elter_nap));
    const vart = `${Math.min(...wf)}–${Math.max(...wf)} napon tér el`;
    allit(E("modszer").innerHTML.includes(vart), `a modszertani szoveg a walkforward.csv-bol szamol: "${vart}"`);
  }
}

console.log(`\n${futott} allitas, ${bukott} bukott`);
process.exit(bukott ? 1 : 0);
