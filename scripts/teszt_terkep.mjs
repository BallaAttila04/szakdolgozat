/**
 * A terkep-sablon JavaScript logikajanak tesztje, valodi bongeszo nelkul.
 *
 * Miert kell: a szinezes es a tipusszures logikaja a sablon JS-eben el, amit
 * a Python-szkriptek nem erintenek. A `node --check` csak szintaxist nez, a
 * futtatas nelkul maradt hibak (TDZ, rossz elemnev, elrontott szurofeltetel)
 * csak a bongeszoben derulnenek ki - akkor viszont mar a konzulens elott.
 *
 * Amit csinal: felepit egy minimalis DOM-csonkot (csak azok az API-k, amiket
 * a sablon tenylegesen hasznal - ld. a getElementById-listat), betolti a
 * sablon <script> blokkjat egy szintetikus adathalmazzal, majd allitasokat
 * ellenoriz a szinezesre, a jelmagyarazatra es a szuresre.
 *
 * Hasznalat:
 *     node scripts/teszt_terkep.mjs
 *
 * Kilepesi kod: 0 ha minden allitas teljesul, 1 egyebkent.
 */

import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

const ITT = dirname(fileURLToPath(import.meta.url));

// --- Allitasok -----------------------------------------------------------
let futott = 0, bukott = 0;
function allit(felteves, leiras) {
  futott++;
  if (felteves) { console.log(`  OK    ${leiras}`); }
  else { bukott++; console.log(`  BUKIK ${leiras}`); }
}

// --- DOM-csonk -----------------------------------------------------------
// A CSS-valtozok ugyanazok az ertekek, mint a sablon :root blokkjaban.
const TOKENEK = {
  "--v1": "#b6ccd8", "--v2": "#7aa9bf", "--v3": "#3f83a1",
  "--v4": "#145f7e", "--v5": "#06394f",
  "--t1": "#2a78d6", "--t2": "#eb6834", "--t3": "#1baf7a", "--t0": "#8a97a1",
  "--water": "#e6ecf0", "--grid": "rgba(22,35,45,0.07)", "--accent": "#0f6f8c",
};

function elem(id) {
  const e = {
    id, textContent: "", innerHTML: "", hidden: false, value: "0",
    _attr: {}, _fig: {},
    setAttribute(k, v) { this._attr[k] = String(v); },
    getAttribute(k) { return this._attr[k]; },
    addEventListener(nev, fn) { (this._fig[nev] ||= []).push(fn); },
    dispatch(nev) { (this._fig[nev] || []).forEach(fn => fn({ clientX: 0, clientY: 0 })); },
    classList: { toggle() {} },
    getBoundingClientRect: () => ({ width: 800, height: 600, left: 0, top: 0 }),
    _sorok: null, _sorokHtml: null,
    querySelectorAll(valaszto) {
      // A jelmagyarazat sorait a script innerHTML-bol epiti. A visszaadott
      // gombokat CACHE-eljuk az aktualis markuphoz: a script ezekre koti fel a
      // kattintaskezelot, es a tesztnek ugyanazt a peldanyt kell visszakapnia,
      // kulonben nem tudja elsutni. Ujraepitett markupnal uj keszlet jon.
      if (valaszto !== ".jm-sor") return [];
      if (this._sorokHtml === this.innerHTML) return this._sorok;
      const ki = [];
      const re = /data-g="(\d+)"/g;
      let m;
      while ((m = re.exec(this.innerHTML))) {
        const g = m[1];
        ki.push({
          dataset: { g }, _fig: {},
          addEventListener(n, fn) { (this._fig[n] ||= []).push(fn); },
          dispatch(n) { (this._fig[n] || []).forEach(fn => fn({})); },
        });
      }
      this._sorok = ki;
      this._sorokHtml = this.innerHTML;
      return ki;
    },
  };
  e.parentElement = { getBoundingClientRect: e.getBoundingClientRect };
  return e;
}

const elemek = new Map();
const rajzoltSzinek = [];   // ide gyujtjuk, milyen szinnel rajzolt a vaszon

const ctx = {
  _fill: "", _alpha: 1,
  set fillStyle(v) { this._fill = v; }, get fillStyle() { return this._fill; },
  set globalAlpha(v) { this._alpha = v; }, get globalAlpha() { return this._alpha; },
  strokeStyle: "", lineWidth: 1,
  setTransform() {}, fillRect() { rajzoltSzinek.push([this._fill, this._alpha]); },
  drawImage() {}, beginPath() {}, moveTo() {}, lineTo() {}, stroke() {}, arc() {},
};

globalThis.document = {
  documentElement: {},
  getElementById(id) {
    if (!elemek.has(id)) elemek.set(id, elem(id));
    return elemek.get(id);
  },
  // A hatter kulon, kepernyon kivuli vaszonra rajzolodik - annak SAJAT
  // contextet adunk, kulonben a hatterpontok is bekerulnenek a merésbe.
  createElement() {
    const ures = { ...ctx, fillRect() {}, _fill: "", _alpha: 1 };
    return { width: 0, height: 0, getContext: () => ures };
  },
};
globalThis.getComputedStyle = () => ({
  getPropertyValue: n => TOKENEK[n] ?? "",
});
globalThis.window = {
  devicePixelRatio: 1,
  addEventListener() {},
  matchMedia: () => ({ addEventListener() {} }),
};
globalThis.requestAnimationFrame = () => {};

// A vaszon getContext-je a kozos ctx-et adja
elemek.set("vaszon", Object.assign(elem("vaszon"), { getContext: () => ctx }));

// --- Szintetikus adat ----------------------------------------------------
// 6 hajo, csoportonkent egy, mind ugyanabban az idokockaban, ervenyes
// poziciokkal. Igy egyetlen rajzolas pontosan 6 negyzetet tesz a listaba.
const HAJO_DB = 6;
const u16 = new Uint16Array(HAJO_DB).fill(30000);
const u8 = new Uint8Array(HAJO_DB).fill(10);          // 10 csomo -> 4. sav
const b64 = b => Buffer.from(b.buffer).toString("base64");

const ADAT = {
  meta: { nap: "2026-07-15", perc: 10, frame_db: 1, hajo_db: HAJO_DB,
          lat_min: 54.5, lat_max: 56.5, lon_min: 10.0, lon_max: 13.0 },
  x: b64(u16), y: b64(u16), sog: b64(u8),
  hajok: Array.from({ length: HAJO_DB }, (_, i) => ({ s: 0, n: 1, m: 1000 + i, g: i })),
  info: {},
  csoportok: [
    { nev: "Áruszállítás", db: 303, sajat_szin: true },
    { nev: "Személyszállítás", db: 133, sajat_szin: true },
    { nev: "Kedvtelési", db: 3186, sajat_szin: true },
    { nev: "Halászat", db: 64, sajat_szin: false },
    { nev: "Szolgálati", db: 158, sajat_szin: false },
    { nev: "Egyéb / ismeretlen", db: 233, sajat_szin: false },
  ],
};

// --- A sablon scriptjenek betoltese --------------------------------------
const html = readFileSync(join(ITT, "terkep_sablon.html"), "utf8");
const m = html.match(/<script>([\s\S]*?)<\/script>/);
if (!m) { console.error("Nem talaltam <script> blokkot a sablonban"); process.exit(1); }
const js = m[1].replace("/*ADATHELY*/", JSON.stringify(ADAT));

console.log("A terkep-sablon JS logikajanak tesztje\n");
try {
  new Function(js)();
} catch (e) {
  console.error(`  BUKIK  a script futas kozben elszallt: ${e.message}`);
  console.error(e.stack.split("\n").slice(0, 4).join("\n"));
  process.exit(1);
}
allit(true, "a script lefut DOM-csonkon, futasidoben nem szall el");

// --- Allitasok -----------------------------------------------------------
const sorok = elemek.get("jm-sorok");
allit((sorok.innerHTML.match(/data-g="/g) || []).length === 6,
      "a jelmagyarazat mind a 6 csoporthoz epit egy sort");
allit(sorok.innerHTML.includes("Halászat") && sorok.innerHTML.includes("Áruszállítás"),
      "a csoportnevek megjelennek a jelmagyarazatban");
allit(sorok.innerHTML.includes("3 186") || sorok.innerHTML.includes("3186"),
      "a hajoszamok kiirodnak a sorokban");

// Egy tiszta ujrarajzolas: a csuszka input-esemenye a script sajat
// kezelojen keresztul hivja a rajzol()-t, kulso hook nelkul.
const ujrarajzol = () => { rajzoltSzinek.length = 0; elemek.get("csuszka").dispatch("input"); };

ujrarajzol();
allit(rajzoltSzinek.length === HAJO_DB,
      `egy rajzolas pontosan ${HAJO_DB} hajot tesz ki (kapott: ${rajzoltSzinek.length})`);
allit(rajzoltSzinek[0][0] === TOKENEK["--t1"], "0. csoport szine --t1 (aruszallitas)");
allit(rajzoltSzinek[1][0] === TOKENEK["--t2"], "1. csoport szine --t2 (szemelyszallitas)");
allit(rajzoltSzinek[2][0] === TOKENEK["--t3"], "2. csoport szine --t3 (kedvtelesi)");
allit(rajzoltSzinek.slice(3).every(([sz]) => sz === TOKENEK["--t0"]),
      "a 3-5. csoport mind a semleges --t0 szint kapja");
allit(new Set(rajzoltSzinek.map(([sz]) => sz)).size === 4,
      "osszesen 4 kulonbozo szin kerul a terkepre - ennyi kulonitheto el biztonsagosan");
allit(rajzoltSzinek.every(([, a]) => a === 1),
      "szures nelkul minden hajo teljes fedessel rajzolodik");

// --- Szures a 3. csoportra (Halaszat) ---
const gombok = sorok.querySelectorAll(".jm-sor");
allit(gombok.length === 6, "a sorok kattinthato gombkent jonnek vissza");
gombok[3].dispatch("click");

ujrarajzol();
allit(rajzoltSzinek.length === HAJO_DB,
      "szuresnel sem tunik el hajo - a tobbi csak elhalvanyul");
allit(rajzoltSzinek[3][1] === 1, "a szurt csoport teljes fedessel rajzolodik");
allit(rajzoltSzinek.filter(([, a]) => a === 1).length === 1,
      "pontosan egy csoport marad kiemelve");
allit(rajzoltSzinek.every(([, a], i) => i === 3 || a < 1),
      "minden mas csoport halvanyabb lesz");
allit(rajzoltSzinek[0][0] === TOKENEK["--t1"],
      "a halvany hajok MEGTARTJAK a sajat szinuket (a szin az entitast koveti)");
allit(elemek.get("lathato-cimke").textContent.includes("Halászat"),
      "a szamlalo cimkeje megmondja, melyik csoportra szur");

// --- Szures torlese ugyanarra a sorra kattintva ---
sorok.querySelectorAll(".jm-sor")[3].dispatch("click");
ujrarajzol();
allit(rajzoltSzinek.every(([, a]) => a === 1),
      "ujra ugyanarra kattintva a szures megszunik");
allit(elemek.get("lathato-cimke").textContent === "Látható hajó",
      "a cimke visszaall alaphelyzetbe");

// --- Sebesseg-mod ---
elemek.get("mod-seb").dispatch("click");
ujrarajzol();
allit(rajzoltSzinek.every(([sz]) => sz === TOKENEK["--v4"]),
      "sebesseg-modban a 10 csomos hajok mind a 4. sav szinet kapjak");
allit(elemek.get("jm-tipus").hidden === true && elemek.get("jm-seb").hidden === false,
      "modvaltaskor a jelmagyarazat is valt");

console.log(`\n${futott} allitas, ${bukott} bukott`);
process.exit(bukott ? 1 : 0);
