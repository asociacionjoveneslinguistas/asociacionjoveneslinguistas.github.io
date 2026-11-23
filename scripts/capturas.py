"""Screenshots for review, written to _shots/ (kept out of the build and of git).

Usage: python3 scripts/capturas.py <base URL of a local server> [<out dir>]

1440 px: full-page capture. 375 px: touch emulation, viewport frames stitched together, because a full-page
capture switches touch emulation off and shows a mixed layout (design.md, Mobile rules).
"""
import asyncio, sys
from pathlib import Path
from playwright.async_api import async_playwright
from PIL import Image

BASE = sys.argv[1].rstrip('/')
OUT = Path(sys.argv[2] if len(sys.argv) > 2 else '_shots')
OUT.mkdir(exist_ok=True)
TYPES = {  # the home and the first page of each inner type
    'inicio': '/',
    'pagina-la-asociacion': '/la-asociacion/',
    'estatutos': '/estatutos/',
    'junta-directiva': '/junta-directiva/',
    'miembro-olga-popova': '/junta-directiva/olga-popova/',
    'socios-fundadores': '/socios-fundadores/',
    'congreso-anual': '/congresos-anteriores/',
    'convocatoria-premios-ajl': '/premios-ajl/',
    'publicaciones': '/publicaciones/',
    'contacto': '/contacto/',
}
WELCOME = {
    'bienvenida-en': '/welcome-to-the-ajl-web-page/',
    'bienvenida-ca': '/benvinguts-a-la-web-de-lajl/',
    'bienvenida-gl': '/damosvos-a-benvida-a-web-da-ajl/',
    'bienvenida-eu': '/ongi-etorri-ajlren-webgunera/',
}


async def settle(pg):
    await pg.evaluate('document.fonts.ready')
    h = await pg.evaluate('document.documentElement.scrollHeight')
    for y in range(0, h + 900, 600):
        await pg.evaluate(f'window.scrollTo(0, {y})')
        await pg.wait_for_timeout(50)
    await pg.wait_for_load_state('networkidle')
    if await pg.evaluate("!!document.getElementById('reader')"):
        await pg.wait_for_function("document.getElementById('reader').dataset.ready === 'true'", timeout=15000)
        await pg.evaluate("document.getElementById('reader').scrollIntoView()")
        await pg.wait_for_function("document.querySelector('.reader__sheet[data-drawn]')", timeout=15000)
    await pg.evaluate('window.scrollTo(0, 0)')
    await pg.wait_for_timeout(500)


async def wide(browser, name, path):
    ctx = await browser.new_context(viewport={'width': 1440, 'height': 900})
    pg = await ctx.new_page()
    await pg.goto(BASE + path + '?v=shot', wait_until='networkidle')
    await settle(pg)
    await pg.screenshot(path=str(OUT / f'{name}-1440.png'), full_page=True)
    await ctx.close()


async def phone(browser, name, path):
    ctx = await browser.new_context(viewport={'width': 375, 'height': 812}, has_touch=True, is_mobile=True, device_scale_factor=2)
    pg = await ctx.new_page()
    await pg.goto(BASE + path + '?v=shot', wait_until='networkidle')
    await settle(pg)
    total = await pg.evaluate('document.documentElement.scrollHeight')
    frames, y = [], 0
    while True:
        await pg.evaluate(f'window.scrollTo(0, {y})')
        await pg.wait_for_timeout(450)
        real = await pg.evaluate('window.scrollY')
        f = OUT / f'.{name}-{len(frames)}.png'
        await pg.screenshot(path=str(f))
        frames.append((real, f))
        if real + 812 >= total:
            break
        y += 812
    await ctx.close()
    imgs = [(r, Image.open(f)) for r, f in frames]
    scale = imgs[0][1].width / 375
    sheet = Image.new('RGB', (imgs[0][1].width, int(total * scale)), 'white')
    for r, im in imgs:
        sheet.paste(im, (0, int(r * scale)))
    sheet.save(OUT / f'{name}-375.png')
    for _, f in frames:
        f.unlink()


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        for name, path in TYPES.items():
            await wide(browser, name, path)
            await phone(browser, name, path)
            print('shot', name)
        for name, path in WELCOME.items():
            await wide(browser, name, path)
            print('shot', name)
        await browser.close()


asyncio.run(main())
