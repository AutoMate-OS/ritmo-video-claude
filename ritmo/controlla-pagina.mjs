#!/usr/bin/env node
/* CONTROLLO DI OGNI FOTOGRAMMA di un video fatto in HTML (HyperFrames / GSAP), prima del render.
   Apre la pagina in Chrome, va su ogni fotogramma e misura dove sono davvero gli elementi visibili:
     - SOVRAPPOSIZIONI tra blocchi diversi (testo sopra testo, casella sopra didascalia...)
     - FUORI ZONA: elementi visibili fuori dalle zone sicure (9:16: x 60-1020, y 200-1520)
     - DA GUARDARE: tratti senza nessun testo a schermo (>= 0,3 s): ogni fotogramma deve avere una lettura
   Uso:  CHROME=/percorso/chrome node ritmo/controlla-pagina.mjs index.html [--fps 30] [--blocchi "#dom > *, #cap .row"] [--ignora ".sp,.cur"] [--min-fuori 0.4]
   --blocchi: i pezzi da misurare (non i contenitori a tutto schermo: misura i loro figli). --min-fuori: un'entrata da fuori schermo piu' breve di cosi' e' voluta.
   Serve playwright-core (npm i playwright-core). Esce con codice 1 se trova problemi.
   Regola: la pagina deve esporre window.__timelines.main (GSAP) o ascoltare l'evento "hf-seek".
   Canvas/3D: la pagina mette in window.__qaBlocchi = [{n, x0, y0, x1, y1}] i riquadri a schermo dei suoi oggetti, cosi' entrano nel controllo. */
import { chromium } from "playwright-core";
import { resolve } from "node:path";

const a = process.argv.slice(2);
const file = a.find(x => !x.startsWith("--") && !a[a.indexOf(x) - 1]?.startsWith("--"));
const opt = (k, d) => { const i = a.indexOf("--" + k); return i >= 0 ? a[i + 1] : d; };
if (!file) { console.log("uso: node controlla-pagina.mjs index.html [--fps 30]"); process.exit(2); }
const FPS = +opt("fps", 30), BLOCCHI = opt("blocchi", "#dom > *, #cap .row"), IGNORA = opt("ignora", ".sp,.cur,.burst");
const ZONA = (opt("zona", "60,200,1020,1520")).split(",").map(Number), MINF = +opt("min-fuori", 0.4);

const b = await chromium.launch({ executablePath: process.env.CHROME || undefined });
const p = await b.newPage({ viewport: { width: 1080, height: 1920 } });
const errori = []; p.on("pageerror", e => errori.push(e.message));
await p.goto("file://" + resolve(file)); await p.waitForTimeout(1200);
const dur = await p.evaluate(() => +(document.querySelector("[data-duration]")?.dataset.duration || 0));
const trovati = [];
for (let f = 0; f <= Math.floor(dur * FPS); f++) {
  const t = f / FPS;
  const r = await p.evaluate(({ t, BLOCCHI, IGNORA, ZONA }) => {
    window.__timelines?.main?.seek(t, false); window.dispatchEvent(new CustomEvent("hf-seek", { detail: { time: t } }));
    const vis = el => { if (el.closest(IGNORA)) return false; let o = 1, e = el;
      while (e && e !== document.body) { const cs = getComputedStyle(e); if (cs.display === "none" || cs.visibility === "hidden") return false; o *= +cs.opacity; e = e.parentElement; }
      return o > .15; };
    const nome = el => (el.id ? "#" + el.id : "") + "." + [...el.classList].join(".") + (el.textContent ? " «" + el.textContent.trim().slice(0, 24) + "»" : "");
    const B = [...document.querySelectorAll(BLOCCHI)].filter(vis).map(el => { const q = el.getBoundingClientRect(); return { el, n: nome(el), x0: q.left, y0: q.top, x1: q.right, y1: q.bottom }; })
      .filter(q => q.x1 - q.x0 > 4 && q.y1 - q.y0 > 4)
      .concat((window.__qaBlocchi || []).map(q => ({ n: q.n, x0: q.x0, y0: q.y0, x1: q.x1, y1: q.y1 })));   // oggetti disegnati su canvas (3D, voxel): la pagina li espone qui
    const out = [];
    for (let i = 0; i < B.length; i++) for (let j = i + 1; j < B.length; j++) {
      const A = B[i], C = B[j];
      if (A.el && C.el && (A.el.contains(C.el) || C.el.contains(A.el))) continue;   // un pezzo dentro il suo contenitore non e' una sovrapposizione
      const w = Math.min(A.x1, C.x1) - Math.max(A.x0, C.x0), h = Math.min(A.y1, C.y1) - Math.max(A.y0, C.y0);
      if (w > 6 && h > 6) { const area = w * h, min = Math.min((A.x1 - A.x0) * (A.y1 - A.y0), (C.x1 - C.x0) * (C.y1 - C.y0));
        if (area / min > .04) out.push("SOVRAPPOSTI: " + A.n + "  ×  " + C.n); } }
    B.forEach(q => { if (q.x0 < ZONA[0] - 2 || q.x1 > ZONA[2] + 2 || q.y0 < ZONA[1] - 2 || q.y1 > ZONA[3] + 2) out.push("FUORI ZONA: " + q.n + ` (${q.x0 | 0},${q.y0 | 0} - ${q.x1 | 0},${q.y1 | 0})`); });
    const testo = B.some(q => q.el && q.el.innerText && q.el.innerText.trim().length > 1);
    if (!testo) out.push("SENZA TESTO");
    return out;
  }, { t, BLOCCHI, IGNORA, ZONA });
  r.forEach(m => trovati.push([t, m]));
}
await b.close();
/* raggruppa lo stesso problema su fotogrammi consecutivi (le coordinate tra parentesi non contano per il raggruppamento) */
const g = new Map(); trovati.forEach(([t, m]) => { const k = m.replace(/ \(.*\)$/, ""); const v = g.get(k) || []; v.push(t); g.set(k, v); });
const righe = [], muti = [];
for (const [m, ts] of g) { let s = ts[0], e = ts[0];
  for (let i = 1; i <= ts.length; i++) { if (i < ts.length && ts[i] - e < 1.5 / FPS) { e = ts[i]; continue; }
    if (m === "SENZA TESTO") { if (e - s >= .3) muti.push([s, e]); }
    else if (!(m.startsWith("FUORI ZONA") && e - s < MINF)) righe.push([s, e, m]); if (i < ts.length) s = e = ts[i]; } }
righe.sort((x, y) => x[0] - y[0]).forEach(([s, e, m]) => console.log(`${s.toFixed(2)}-${e.toFixed(2)}s  ${m}`));
if (muti.length) console.log("DA GUARDARE (nessun testo a schermo per >= 0,3 s: c'e' comunque una lettura visiva chiara?): " + muti.map(([s, e]) => s.toFixed(2) + "-" + e.toFixed(2) + "s").join(", "));
if (errori.length) console.log("ERRORI JS:", [...new Set(errori)].slice(0, 5).join(" | "));
console.log(righe.length ? `${righe.length} problemi da guardare (${Math.floor(dur * FPS) + 1} fotogrammi controllati)` : `nessun problema su ${Math.floor(dur * FPS) + 1} fotogrammi`);
process.exit(righe.length || errori.length ? 1 : 0);
