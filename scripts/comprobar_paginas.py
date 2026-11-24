"""Browser checks on every built page (Playwright, Chromium).

Usage: python3 scripts/comprobar_paginas.py <public/> <base URL of a local server, e.g. http://127.0.0.1:8765>

At 320, 375, 768, 1280 and 1440 px (touch emulation at 320 and 375) it checks, on every page:
horizontal overflow; clickable labels that wrap; fonts loaded; computed underlines (at rest and on hover);
«Menú» open, Escape and focus return; the spotlight from Ctrl K and ⌘K, «sem» finding «Seminarios AJL»,
Escape and focus return; the docked pill after scrolling; broken images. On Estatutos it checks that the
PDF reader draws pages; on Congreso anual, that the map is visible.
"""
import asyncio, json, sys
from pathlib import Path
from playwright.async_api import async_playwright

PUB = Path(sys.argv[1]).resolve()
BASE = sys.argv[2].rstrip('/')
WIDTHS = [320, 375, 768, 1280, 1440]
PAGES = []
for f in sorted(PUB.rglob('index.html')):
    rel = f.parent.relative_to(PUB).as_posix()
    rel = '/' if rel == '.' else '/' + rel + '/'
    if 'http-equiv="refresh"' in f.read_text(encoding='utf-8')[:600] or 'http-equiv=refresh' in f.read_text(encoding='utf-8')[:600]:
        continue  # alias redirect pages
    PAGES.append(rel)

LAYOUT_JS = r"""
() => {
  const vw = document.documentElement.clientWidth;
  const out = { overflow: [], wrapped: [], underline: [], scrollW: document.documentElement.scrollWidth, vw };
  const clipped = (el) => {
    for (let a = el.parentElement; a && a !== document.body; a = a.parentElement) {
      const cs = getComputedStyle(a);
      if (/(hidden|clip|auto|scroll)/.test(cs.overflowX + cs.overflow)) {
        const r = a.getBoundingClientRect();
        if (r.right <= vw + 1 && r.left >= -1) return true;
      }
    }
    return false;
  };
  const visible = (el) => {
    const cs = getComputedStyle(el);
    if (cs.display === 'none' || cs.visibility === 'hidden') return false;
    const r = el.getBoundingClientRect();
    return r.width > 0 && r.height > 0;
  };
  for (const el of document.body.querySelectorAll('*')) {
    if (el.closest('dialog:not([open])') || el.closest('.sprite')) continue;
    if (!visible(el)) continue;
    const r = el.getBoundingClientRect();
    if ((r.right > vw + 1 || r.left < -1) && !clipped(el) && !el.closest('.vh')) {
      out.overflow.push((el.className && el.className.baseVal === undefined ? el.className : el.tagName) + ' ' + Math.round(r.left) + '..' + Math.round(r.right));
    }
    const td = getComputedStyle(el).textDecorationLine;
    if (td && td.includes('underline')) out.underline.push(el.tagName + '.' + el.className);
  }
  const blockOf = (el) => { let b = el.parentElement; while (b && getComputedStyle(b).display.startsWith('inline')) b = b.parentElement; return b; };
  for (const el of document.querySelectorAll('a[href], button')) {
    if (!visible(el) || el.closest('.vh') || el.closest('dialog:not([open])')) continue;
    const txt = el.textContent.replace(/\s+/g, ' ').trim();
    if (!txt) continue;
    const b = blockOf(el);
    const own = b ? b.textContent.replace(/\s+/g, ' ').trim() : txt;
    if (own.length > txt.length + 2) continue;  // a link inside running text may wrap like the text around it
    if (el.classList.contains('c3--wrap')) continue;  // Seminarios AJL cycle titles: heading links that wrap, arrow kept on the last word (approved s1, 24 Nov 2026)
    const range = document.createRange();
    range.selectNodeContents(el);
    const tops = new Set();
    for (const rc of range.getClientRects()) if (rc.width > 1 && rc.height > 1) tops.add(Math.round(rc.top + rc.height / 2));
    const lines = [...tops].sort((a, b) => a - b).filter((t, i, arr) => i === 0 || t - arr[i - 1] > 6).length;
    if (lines > 1) out.wrapped.push(txt.slice(0, 60));
  }
  return out;
}
"""


async def check(browser, path, width):
    touch = width <= 414
    ctx = await browser.new_context(viewport={'width': width, 'height': 800}, has_touch=touch, is_mobile=touch,
                                    device_scale_factor=2 if touch else 1)
    pg = await ctx.new_page()
    errors = []
    pg.on('pageerror', lambda e: errors.append(str(e)))
    res = {'page': path, 'width': width, 'fail': []}
    await pg.goto(BASE + path + '?v=check', wait_until='networkidle')
    await pg.evaluate('document.fonts.ready')
    fonts = await pg.evaluate("""() => ({
      spectral800: document.fonts.check('800 16px Spectral'),
      gs400: document.fonts.check('400 16px "General Sans"'),
      gs500: document.fonts.check('500 16px "General Sans"'),
      gs600: document.fonts.check('600 16px "General Sans"'),
      loaded: [...document.fonts].filter(f => f.status === 'loaded').map(f => f.family + ' ' + f.weight)
    })""")
    if not all([fonts['spectral800'], fonts['gs400'], fonts['gs500'], fonts['gs600']]) or not any('Spectral' in x for x in fonts['loaded']) or not any('General Sans' in x for x in fonts['loaded']):
        res['fail'].append('fonts: ' + json.dumps(fonts))
    lay = await pg.evaluate(LAYOUT_JS)
    if lay['scrollW'] > lay['vw'] + 1:
        res['fail'].append(f"scrollWidth {lay['scrollW']} > {lay['vw']}")
    if lay['overflow']:
        res['fail'].append('overflow: ' + '; '.join(lay['overflow'][:5]))
    if lay['wrapped']:
        res['fail'].append('wrapped labels: ' + ' | '.join(lay['wrapped'][:5]))
    if lay['underline']:
        res['fail'].append('underline: ' + ', '.join(lay['underline'][:5]))

    # hover underline (fine pointers only): every link on the page
    if not touch:
        und = []
        for a in (await pg.query_selector_all('main a[href], footer a[href]'))[:40]:
            try:
                if not await a.is_visible():
                    continue
                await a.hover(timeout=1500)
                if 'underline' in await a.evaluate('el => getComputedStyle(el).textDecorationLine'):
                    und.append(await a.text_content())
            except Exception:
                pass
        if und:
            res['fail'].append('underline on hover: ' + ', '.join(und[:5]))
        await pg.mouse.move(0, 0)

    # «Menú»: open, Escape, focus return
    toggle = pg.locator('.menu-toggle')
    await toggle.click()
    await pg.wait_for_timeout(260)
    st = await pg.evaluate("() => ({exp: document.querySelector('.menu-toggle').getAttribute('aria-expanded'), vis: getComputedStyle(document.getElementById('indice')).display !== 'none'})")
    if st != {'exp': 'true', 'vis': True}:
        res['fail'].append('menu did not open: ' + json.dumps(st))
    lay2 = await pg.evaluate(LAYOUT_JS)
    if lay2['overflow'] or lay2['wrapped']:
        res['fail'].append('menu open: overflow/wrap ' + '; '.join(lay2['overflow'][:3] + lay2['wrapped'][:3]))
    await pg.keyboard.press('Escape')
    await pg.wait_for_timeout(220)
    st = await pg.evaluate("() => ({exp: document.querySelector('.menu-toggle').getAttribute('aria-expanded'), focus: document.activeElement.classList.contains('menu-toggle'), vis: getComputedStyle(document.getElementById('indice')).display !== 'none'})")
    if st != {'exp': 'false', 'focus': True, 'vis': False}:
        res['fail'].append('menu Escape/focus: ' + json.dumps(st))

    # spotlight: Ctrl K and ⌘K from the search pill, «sem», Escape returns focus to the pill
    for combo in ('Control+k', 'Meta+k'):
        await pg.focus('.searchpill')
        await pg.keyboard.press(combo)
        await pg.wait_for_timeout(80)
        ok = await pg.evaluate("() => document.getElementById('cmdk').open && document.activeElement.id === 'cmdk-input'")
        if not ok:
            res['fail'].append(f'spotlight did not open with {combo}')
            continue
        await pg.keyboard.type('sem')
        opts = await pg.evaluate("() => [...document.querySelectorAll('#cmdk-list .cmdk__opt')].map(o => o.textContent.trim())")
        if 'Seminarios AJL' not in opts:
            res['fail'].append('«sem» did not find Seminarios AJL: ' + json.dumps(opts))
        lay3 = await pg.evaluate(LAYOUT_JS)
        if lay3['overflow']:
            res['fail'].append('spotlight open: overflow ' + '; '.join(lay3['overflow'][:3]))
        await pg.keyboard.press('Escape')
        await pg.wait_for_timeout(80)
        st = await pg.evaluate("() => ({open: document.getElementById('cmdk').open, focus: document.activeElement.classList.contains('searchpill')})")
        if st != {'open': False, 'focus': True}:
            res['fail'].append(f'spotlight Escape/focus ({combo}): ' + json.dumps(st))

    # docked pill after scrolling past the masthead (pages too short to scroll that far never dock)
    can_dock = await pg.evaluate("document.documentElement.scrollHeight - innerHeight > document.querySelector('.mast').offsetHeight - 80")
    if not can_dock:
        res['note'] = 'page too short to dock'
    await pg.evaluate('window.scrollTo(0, document.documentElement.scrollHeight)')
    await pg.wait_for_timeout(450)
    dock = await pg.evaluate("""() => {
      const d = document.querySelector('.dock'), r = d.getBoundingClientRect(), cs = getComputedStyle(d);
      const langs = getComputedStyle(d.querySelector('.langs')).display;
      return {docked: document.documentElement.classList.contains('is-docked'), pos: cs.position, top: Math.round(r.top), left: Math.round(r.left), right: Math.round(r.right), vw: document.documentElement.clientWidth, langs};
    }""")
    if can_dock and not (dock['docked'] and dock['pos'] == 'fixed' and dock['top'] >= 0 and dock['left'] >= 0 and dock['right'] <= dock['vw']):
        res['fail'].append('docked pill: ' + json.dumps(dock))
    if can_dock and width < 640 and dock['langs'] != 'none':
        res['fail'].append('docked pill shows the language row below 40rem')
    lay4 = await pg.evaluate(LAYOUT_JS)
    if lay4['overflow'] or lay4['wrapped']:
        res['fail'].append('docked: overflow/wrap ' + '; '.join(lay4['overflow'][:3] + lay4['wrapped'][:3]))
    # docked menu: on phones the languages sit at the top of «Menú»
    await pg.locator('.menu-toggle').click()
    await pg.wait_for_timeout(260)
    il = await pg.evaluate("() => getComputedStyle(document.querySelector('.index__langs')).display")
    if can_dock and width < 640 and il == 'none':
        res['fail'].append('docked «Menú» on phone lacks the language row')
    await pg.keyboard.press('Escape')
    await pg.wait_for_timeout(200)
    if not await pg.evaluate("() => document.activeElement.classList.contains('menu-toggle')"):
        res['fail'].append('docked menu Escape: focus not returned')

    # images: walk the page so lazy images load, then look for broken ones
    h = await pg.evaluate('document.documentElement.scrollHeight')
    for y in range(0, h + 800, 700):
        await pg.evaluate(f'window.scrollTo(0, {y})')
        await pg.wait_for_timeout(60)
    await pg.wait_for_load_state('networkidle')
    broken = await pg.evaluate("() => [...document.images].filter(i => !(i.complete && i.naturalWidth > 0)).map(i => i.getAttribute('src'))")
    if broken:
        res['fail'].append('broken images: ' + ', '.join(broken))

    if path in ('/estatutos/', '/convenio-ajl-sel/'):
        await pg.evaluate("document.getElementById('reader').scrollIntoView()")
        try:
            await pg.wait_for_function("document.getElementById('reader').dataset.ready === 'true' && document.querySelector('.reader__sheet[data-drawn]')", timeout=15000)
            ink = await pg.evaluate("""() => { const c = document.querySelector('.reader__sheet[data-drawn] canvas'); const x = c.getContext('2d');
              const d = x.getImageData(0, 0, c.width, c.height).data; let n = 0; for (let i = 0; i < d.length; i += 400) if (d[i] < 200) n++; return {w: c.width, h: c.height, dark: n, pages: document.querySelectorAll('.reader__sheet').length}; }""")
            res['reader'] = ink
            if ink['dark'] < 50:
                res['fail'].append('reader canvas looks blank: ' + json.dumps(ink))
        except Exception as e:
            res['fail'].append('reader did not draw: ' + str(e)[:120])
    if path == '/congresos-anteriores/':
        m = await pg.evaluate("""() => { const a = document.querySelector('.map__art').getBoundingClientRect();
          const lbl = [...document.querySelectorAll('.node__lbl')].filter(l => getComputedStyle(l).display !== 'none').length;
          return {w: Math.round(a.width), h: Math.round(a.height), legs: document.querySelectorAll('.route__leg').length, nodes: document.querySelectorAll('.node').length, labels: lbl}; }""")
        res['map'] = m
        if m['w'] < 200 or m['legs'] != 4 or m['nodes'] != 24:
            res['fail'].append('map: ' + json.dumps(m))
    if errors:
        res['fail'].append('script errors: ' + '; '.join(errors[:3]))
    await ctx.close()
    return res


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        sem = asyncio.Semaphore(6)
        async def run(path, w):
            async with sem:
                try:
                    return await check(browser, path, w)
                except Exception as e:
                    return {'page': path, 'width': w, 'fail': ['exception: ' + str(e)[:200]]}
        results = await asyncio.gather(*(run(pth, w) for pth in PAGES for w in WIDTHS))
        await browser.close()
    fails = [r for r in results if r['fail']]
    for r in results:
        if 'reader' in r: print('reader', r['width'], r['reader'])
        if 'map' in r: print('map', r['width'], r['map'])
        if 'note' in r: print('note', r['page'], r['width'], r['note'])
    print(f'{len(PAGES)} pages x {len(WIDTHS)} widths = {len(results)} runs; {len(fails)} with failures')
    for r in fails:
        print(f"  {r['page']} @ {r['width']}: " + ' || '.join(r['fail']))
    sys.exit(1 if fails else 0)


asyncio.run(main())
