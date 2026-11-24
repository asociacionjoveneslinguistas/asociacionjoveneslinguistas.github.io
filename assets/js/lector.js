// PDF reader for the «documento» layout (Estatutos, Convenio AJL-SEL; mockups/inner/a/estatutos.html), on self-hosted pdfjs-dist.
// The library and worker paths come from data attributes on #reader, so the page works under any base path.
const reader = document.getElementById("reader");
let pdfjsLib = null;
const view = document.getElementById("reader-view");
const sheetsEl = reader.querySelector(".reader__pages");
const input = document.getElementById("reader-page");
const countEl = reader.querySelector(".reader__count");
const msg = document.getElementById("reader-msg");
const btn = (a) => reader.querySelector(`[data-act="${a}"]`);
const fullBtn = btn("full");
const LABEL = { full: "Pantalla completa", exit: "Salir de pantalla completa", loading: "Cargando el documento…", failed: "No se ha podido mostrar el documento." };
const MAX_AUTO = 1.5, MIN = 0.25, MAX = 4, STEP = 1.25, KEEP = 6;
let pdf = null, pages = [], scale = 1, mode = "auto", current = 1, ticking = false, expanded = false, restoreFocus = null;
const say = (text) => { msg.hidden = !text; msg.querySelector(".reader__msgtext").textContent = text || ""; msg.querySelector(".doclink").hidden = text === LABEL.loading; };
const pad = () => parseFloat(getComputedStyle(sheetsEl).paddingLeft) || 0;
const fitScale = () => (view.clientWidth - 2 * pad()) / Math.max(...pages.map((p) => p.base.width));
const ratio = () => Math.min(window.devicePixelRatio || 1, 2);

function layout(keep) {
  const anchor = keep ? anchorNow() : null;
  if (mode === "fit") scale = fitScale();
  else if (mode === "auto") scale = Math.min(fitScale(), MAX_AUTO);
  scale = Math.max(MIN, Math.min(MAX, scale));
  for (const p of pages) {
    p.el.style.width = p.base.width * scale + "px";
    p.el.style.height = p.base.height * scale + "px";
    p.el.style.setProperty("--total-scale-factor", scale);
    if (p.scale !== scale) p.stale = true;
  }
  btn("fit").setAttribute("aria-pressed", String(mode === "fit"));
  btn("zoom-out").disabled = scale <= MIN + 1e-6;
  btn("zoom-in").disabled = scale >= MAX - 1e-6;
  if (anchor) view.scrollTop = pages[anchor.i].el.offsetTop - pad() + anchor.f * pages[anchor.i].el.offsetHeight;
  renderNear();
}
function anchorNow() {
  const top = view.scrollTop + pad();
  for (let i = 0; i < pages.length; i++) {
    const el = pages[i].el;
    if (el.offsetTop + el.offsetHeight > top) return { i, f: Math.max(0, (top - el.offsetTop) / el.offsetHeight) };
  }
  return { i: 0, f: 0 };
}
function near(p) {
  const r = p.el.getBoundingClientRect(), v = view.getBoundingClientRect();
  return r.bottom > v.top - v.height && r.top < v.bottom + v.height;
}
function renderNear() {
  for (const p of pages) if (near(p) && (!p.canvas || p.stale)) draw(p);
  const drawn = pages.filter((p) => p.canvas);
  if (drawn.length > KEEP) {
    drawn.sort((a, b) => Math.abs(b.n - current) - Math.abs(a.n - current));
    for (const p of drawn.slice(0, drawn.length - KEEP)) if (!near(p)) drop(p);
  }
}
function drop(p) {
  p.task?.cancel(); p.text?.cancel();
  p.el.replaceChildren(); p.canvas = null; p.scale = 0;
}
async function draw(p) {
  p.task?.cancel(); p.text?.cancel();
  const s = scale, vp = p.page.getViewport({ scale: s }), r = ratio();
  const canvas = document.createElement("canvas");
  canvas.width = Math.floor(vp.width * r);
  canvas.height = Math.floor(vp.height * r);
  canvas.setAttribute("aria-hidden", "true");
  p.stale = false; p.scale = s;
  const task = p.page.render({ canvas, viewport: vp, transform: r !== 1 ? [r, 0, 0, r, 0, 0] : null });
  p.task = task;
  try { await task.promise; } catch (e) { return; }
  if (p.scale !== s) return;
  const layer = document.createElement("div");
  layer.className = "textLayer";
  p.el.replaceChildren(canvas, layer);
  p.canvas = canvas;
  p.el.dataset.drawn = "true";
  const text = new pdfjsLib.TextLayer({ textContentSource: p.page.streamTextContent(), container: layer, viewport: vp });
  p.text = text;
  try { await text.render(); } catch (e) { /* cancelled */ }
}
function track() {
  const { i } = anchorNow();
  const probe = view.scrollTop + view.clientHeight * 0.3;
  let n = 1;
  for (const p of pages) if (p.el.offsetTop <= probe) n = p.n;
  if (view.scrollTop + view.clientHeight >= view.scrollHeight - 2) n = pages.length;
  current = n || i + 1;
  if (document.activeElement !== input) input.value = current;
  btn("prev").disabled = current <= 1;
  btn("next").disabled = current >= pages.length;
  renderNear();
}
function go(n) {
  n = Math.max(1, Math.min(pages.length, n));
  view.scrollTop = pages[n - 1].el.offsetTop - pad();
  current = n; input.value = n; track();
}
function zoom(f) { mode = "manual"; scale = Math.max(MIN, Math.min(MAX, scale * f)); layout(true); }
function setFull(on) {
  reader.classList.toggle("is-full", on);
  fullBtn.setAttribute("aria-label", on ? LABEL.exit : LABEL.full);
  fullBtn.title = on ? LABEL.exit : LABEL.full;
  requestAnimationFrame(() => layout(true));
}
function expand(on) {
  expanded = on;
  reader.classList.toggle("is-expanded", on);
  document.documentElement.classList.toggle("is-locked", on);
  setFull(on);
  if (!on && restoreFocus) restoreFocus.focus();
}
fullBtn.addEventListener("click", () => {
  if (document.fullscreenElement) { document.exitFullscreen(); return; }
  if (expanded) { expand(false); return; }
  restoreFocus = fullBtn;
  if (reader.requestFullscreen && document.fullscreenEnabled) reader.requestFullscreen().catch(() => expand(true));
  else expand(true);
});
document.addEventListener("fullscreenchange", () => { setFull(document.fullscreenElement === reader); if (!document.fullscreenElement) fullBtn.focus(); });
document.addEventListener("keydown", (e) => {
  if (e.key !== "Escape") return;
  if (expanded) { e.preventDefault(); expand(false); }
  else if (document.fullscreenElement === reader) document.exitFullscreen();
});
btn("prev").addEventListener("click", () => go(current - 1));
btn("next").addEventListener("click", () => go(current + 1));
btn("zoom-in").addEventListener("click", () => zoom(STEP));
btn("zoom-out").addEventListener("click", () => zoom(1 / STEP));
btn("fit").addEventListener("click", () => { mode = "fit"; layout(true); });
input.addEventListener("keydown", (e) => { if (e.key === "Enter") { e.preventDefault(); const n = parseInt(input.value, 10); if (n) go(n); else input.value = current; } });
input.addEventListener("blur", () => { input.value = current; });
view.addEventListener("scroll", () => { if (ticking) return; ticking = true; requestAnimationFrame(() => { track(); ticking = false; }); }, { passive: true });
new ResizeObserver(() => { if (pages.length && mode !== "manual") layout(true); }).observe(view);

for (const a of ["prev", "next", "zoom-in", "zoom-out", "fit"]) btn(a).disabled = true;
say(LABEL.loading);
try {
  pdfjsLib = await import(reader.dataset.lib);
  pdfjsLib.GlobalWorkerOptions.workerSrc = reader.dataset.worker;
  pdf = await pdfjsLib.getDocument({ url: reader.dataset.src }).promise;
  countEl.textContent = pdf.numPages;
  for (let n = 1; n <= pdf.numPages; n++) {
    const page = await pdf.getPage(n);
    const el = document.createElement("div");
    el.className = "reader__sheet";
    el.dataset.page = n;
    sheetsEl.append(el);
    pages.push({ n, page, el, base: page.getViewport({ scale: 1 }), canvas: null, stale: true, scale: 0 });
  }
  say("");
  btn("fit").disabled = false;
  layout(false);
  track();
  reader.dataset.ready = "true";
} catch (e) {
  say(LABEL.failed);
  reader.dataset.ready = "failed";
}
