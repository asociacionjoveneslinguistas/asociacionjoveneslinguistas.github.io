"""Design-system gates measured in the browser (Hallmark slop test, the gates that can be measured on rendered pages).

Usage: python3 scripts/comprobar_diseno.py <public/> <base URL of a local server>

On every page at 1440 and 375 px: text contrast against the first opaque background behind it (gate 40), italic
headings (38a), display heads without long-word wrap (51), SVGs without a name or aria-hidden (33), images
without alt (33), and the inner band's height against a 1280x800 and a 375x812 first screen (44).
"""
import asyncio, json, sys
from pathlib import Path
from playwright.async_api import async_playwright

PUB = Path(sys.argv[1]).resolve()
BASE = sys.argv[2].rstrip('/')
PAGES = []
for f in sorted(PUB.rglob('index.html')):
    t = f.read_text(encoding='utf-8')[:600]
    if 'http-equiv=refresh' in t or 'http-equiv="refresh"' in t:
        continue
    rel = f.parent.relative_to(PUB).as_posix()
    PAGES.append('/' if rel == '.' else '/' + rel + '/')

JS = r"""
() => {
  // computed colours come back as oklch(); resolve each through a canvas pixel to sRGB
  const cv = document.createElement('canvas'); cv.width = cv.height = 1; const cx = cv.getContext('2d', { willReadFrequently: true });
  const cache = new Map();
  const parse = (c) => {
    if (!c || c === 'transparent') return null;
    if (cache.has(c)) return cache.get(c);
    const am = c.match(/\/\s*([\d.]+%?)\s*\)$/) || c.match(/^rgba\([^)]*,\s*([\d.]+)\)$/);
    let a = am ? (am[1].endsWith('%') ? parseFloat(am[1]) / 100 : parseFloat(am[1])) : 1;
    cx.clearRect(0, 0, 1, 1); cx.fillStyle = '#000'; cx.fillStyle = c; cx.globalAlpha = 1; cx.fillRect(0, 0, 1, 1);
    const d = cx.getImageData(0, 0, 1, 1).data;
    const v = a === 0 ? {r: 0, g: 0, b: 0, a: 0} : {r: d[0], g: d[1], b: d[2], a};
    cache.set(c, v); return v;
  };
  const lum = (c) => { const f = (v) => { v /= 255; return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4); }; return 0.2126 * f(c.r) + 0.7152 * f(c.g) + 0.0722 * f(c.b); };
  const ratio = (a, b) => { const x = lum(a), y = lum(b); return (Math.max(x, y) + 0.05) / (Math.min(x, y) + 0.05); };
  const bgOf = (el) => { for (let e = el; e; e = e.parentElement) { const c = parse(getComputedStyle(e).backgroundColor); if (c && c.a > 0.95) return c; } return {r: 255, g: 255, b: 255, a: 1}; };
  const out = { low: [], minBody: 99, minLarge: 99, italicHeads: [], noWrap: [], svg: [], noAlt: [] };
  const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  const seen = new Set();
  while (walker.nextNode()) {
    const n = walker.currentNode; const el = n.parentElement;
    if (!n.textContent.trim() || !el || seen.has(el)) continue;
    seen.add(el);
    if (el.closest('.vh, dialog:not([open]), .sprite, .map__art, [hidden]')) continue;
    const cs = getComputedStyle(el);
    if (cs.display === 'none' || cs.visibility === 'hidden' || parseFloat(cs.opacity) === 0) continue;
    const r = el.getBoundingClientRect(); if (!r.width || !r.height) continue;
    let hidden = false; for (let e = el; e; e = e.parentElement) { const s = getComputedStyle(e); if (s.display === 'none' || s.visibility === 'hidden') { hidden = true; break; } }
    if (hidden) continue;
    const fg = parse(cs.color); if (!fg) continue;
    const k = ratio(fg, bgOf(el));
    const size = parseFloat(cs.fontSize), w = parseInt(cs.fontWeight, 10);
    const large = size >= 24 || (size >= 18.66 && w >= 700);
    if (large) out.minLarge = Math.min(out.minLarge, k); else out.minBody = Math.min(out.minBody, k);
    if (k < (large ? 3 : 4.5)) out.low.push(el.tagName + '.' + el.className + ' ' + k.toFixed(2) + ' «' + n.textContent.trim().slice(0, 30) + '»');
  }
  for (const h of document.querySelectorAll('h1, h2, h3, h4, [class*="__title"], .mast__name, .colophon__wordmark')) {
    for (const e of [h, ...h.querySelectorAll('*')]) if (getComputedStyle(e).fontStyle !== 'normal') { out.italicHeads.push(h.tagName + '.' + h.className); break; }
    const cs = getComputedStyle(h);
    if (/^H[1-4]$/.test(h.tagName) && cs.overflowWrap !== 'anywhere' && !h.closest('.prose')) out.noWrap.push(h.tagName + '.' + h.className);
  }
  for (const s of document.querySelectorAll('svg')) {
    if (s.closest('[aria-hidden="true"]') || s.getAttribute('aria-hidden') === 'true' || s.classList.contains('sprite')) continue;
    if (!(s.getAttribute('role') === 'img' && s.getAttribute('aria-label'))) out.svg.push(s.outerHTML.slice(0, 80));
  }
  for (const i of document.images) if (!i.hasAttribute('alt')) out.noAlt.push(i.getAttribute('src'));
  const band = document.querySelector('.mast--band');
  out.band = band ? Math.round(band.getBoundingClientRect().bottom + scrollY) : null;
  return out;
}
"""


async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch()
        results = []
        for w, h, touch in ((1440, 900, False), (1280, 800, False), (375, 812, True)):
            ctx = await b.new_context(viewport={'width': w, 'height': h}, has_touch=touch, is_mobile=touch)
            pg = await ctx.new_page()
            for path in PAGES:
                await pg.goto(BASE + path + '?v=gates', wait_until='networkidle')
                await pg.evaluate('document.fonts.ready')
                r = await pg.evaluate(JS)
                r.update(page=path, width=w, vh=h)
                results.append(r)
            await ctx.close()
        await b.close()
    fails = 0
    minb = min(r['minBody'] for r in results); minl = min(r['minLarge'] for r in results)
    print(f'contrast: lowest body-text ratio {minb:.2f}, lowest large-text ratio {minl:.2f}')
    for r in results:
        bad = {k: r[k] for k in ('low', 'italicHeads', 'noWrap', 'svg', 'noAlt') if r[k]}
        if bad:
            fails += 1
            print(r['page'], r['width'], json.dumps(bad, ensure_ascii=False)[:400])
    bands = sorted(((r['band'], r['page'], r['width'], r['vh']) for r in results if r['band'] and r['width'] in (1280, 375)), reverse=True)
    print('tallest inner bands (bottom edge, viewport height):')
    for bb, pth, w, vh in bands[:6]:
        print(f'   {bb}px of {vh} at {w}: {pth}')
    over = [x for x in bands if x[0] > x[3] - 120]
    print(f'bands leaving under 120 px of content on the first screen: {len(over)}')
    for bb, pth, w, vh in over:
        print(f'   {pth} @ {w}: band ends at {bb}px')
    print(f'{len(results)} runs; {fails} with gate failures')


asyncio.run(main())
