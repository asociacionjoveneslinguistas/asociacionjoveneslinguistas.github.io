"""Content preservation check: every sentence of the 30 WordPress pages must appear in the built site.

Usage: python3 scripts/comprobar_contenido.py <pages_v1.json> <public/>

For each WordPress page it extracts the visible text (title and content), splits it into sentences and looks
for each one in the visible text of the corresponding built page. A sentence found only in the header or the
footer of the built page counts as present and is listed separately. Missing sentences are printed page by page,
each with the reason recorded for it in EXPECTED (approved removals and approved changes) or as UNEXPLAINED.
"""
import json, re, sys, unicodedata
from pathlib import Path
from bs4 import BeautifulSoup

# WordPress slug -> built page(s), relative to public/
PAGES = {
    'pagina-principal': ['index.html'],
    'la-asociacion': ['la-asociacion/index.html'],
    'the-association-en': ['the-association-en/index.html'],
    'lassociacio': ['lassociacio/index.html'],
    'a-asociacion-gal': ['a-asociacion-gal/index.html'],
    'eus': ['eus/index.html'],
    'welcome-to-the-ajl-web-page': ['welcome-to-the-ajl-web-page/index.html'],
    'benvinguts-a-la-web-de-lajl': ['benvinguts-a-la-web-de-lajl/index.html'],
    'damosvos-a-benvida-a-web-da-ajl': ['damosvos-a-benvida-a-web-da-ajl/index.html'],
    'ongi-etorri-ajlren-webgunera': ['ongi-etorri-ajlren-webgunera/index.html'],
    'estatutos': ['estatutos/index.html'],
    'junta-directiva': ['junta-directiva/index.html'],
    'juntas-anteriores': ['junta-directiva/index.html'],  # merged into Junta Directiva (approved layout)
    'socios-fundadores': ['socios-fundadores/index.html'],
    'ayudas-economicas': ['ayudas-economicas/index.html'],
    'congresos-anteriores': ['congresos-anteriores/index.html'],
    'xxxiv-congreso-santiago-2024': ['xxxiv-congreso-santiago-2024/index.html'],
    'sorteo-ajl': ['sorteo-ajl/index.html'],
    'sorteo-ajl-2': ['sorteo-ajl-2/index.html'],
    'premios-ajl': ['premios-ajl/index.html'],
    'seminarios-ajl': ['seminarios-ajl/index.html'],
    'seminarios-formativos-ajl-ciclo-2024': ['seminarios-formativos-ajl-ciclo-2024/index.html'],
    'seminarios-formativos-ajl-ciclo-2025': ['seminarios-ajl/seminarios-formativos-ajl-ciclo-2025/index.html'],
    'seminarios-formativos-ajl-ciclo-2026': ['seminarios-ajl/seminarios-formativos-ajl-ciclo-2026/index.html'],
    'curso-formativo-2026-estadistica-hablemos-de-regresion-lineal': ['seminarios-ajl/curso-formativo-2026-estadistica-hablemos-de-regresion-lineal/index.html'],
    'convenio-ajl-sel': ['convenio-ajl-sel/index.html'],
    'publicaciones': ['publicaciones/index.html'],
    'estudios-interlinguisticos': ['estudios-interlinguisticos/index.html'],
    'hazte-socio': ['hazte-socio/index.html'],
    'contacto': ['contacto/index.html'],
}

# Differences the user approved, matched against the normalised missing sentence
EXPECTED = [
    (r'^Tweets by ajl_info$', 'removed: the WordPress X/Twitter widget (approved)'),
    (r'Asociación de Jóvenes Lingüistas, creada en Barcelona en 1992, está composta|Cada ano, a Asociación de Jóvenes Lingüistas organiza', 'Galician name «Asociación de Novas Lingüistas» in the Galician pages (her decision, 24 Nov 2026)'),
    (r'^Disponible a través de la URL: http://estudiosinterlinguisticos\.com, esta nueva publicación', 'RECYT address added before the old one (her wording choice, 24 Nov 2026)'),
    (r'^Seminarios 202[456]$', 'removed: the three cycle links of Seminarios AJL, replaced by the overview of every cycle (s1, approved 24 Nov 2026)'),
    (r'^(Carmen Varo Varo \(UCA\)|Adrián Cabedo Nebot \(UV\)|María José Ginzo Villamayor \(USC\)|Magdalena Romera \(UPNA\)|Susana Quicios Molina \(UAM\)|María del Carmen Méndez Santos \(UVigo\)|Federación de Jóvenes Investigadoras Precarias|Paula Albitre Lamata \(UCM\) y José García Pérez \(UCO\)):$', 'session fields (approved 24 Nov 2026): speakers now follow the session title; the name, affiliation and title are all present'),
    (r'^\w+ \d+ de \w+ de 202[45] \| \d\d:\d\d \(CEST\) \| Inscripción$', 'session fields (approved 24 Nov 2026): the date line and the «Inscripción» link are on separate lines; both present'),
    (r'^[–…\.]+$', 'removed: WordPress spacer line («–», «……»), replaced by hairlines in the approved template'),
    (r'^V_Edición_Premios_Trayectoria_Predoctoral_AJL$', 'file-block file name: the approved template names the file by its heading «Bases V Edición Premios AJL»'),
    (r'^Descarga$', 'file-block button label, kept as «Descarga» in «Documentos»'),
    (r'^(Presidenta|Secretaria|Tesorera|Vocales):$', 'group label replaced by the per-person role in sentence case («Presidenta», «Secretaria», «Tesorera», «Vocal»), approved'),
]


def norm(t):
    t = unicodedata.normalize('NFC', t).replace('\xa0', ' ').replace('​', '')
    return re.sub(r'\s+', ' ', t).strip()


def units(html):
    """Visible text of a WordPress content block, split into sentences."""
    soup = BeautifulSoup(html, 'html.parser')
    for s in soup(['script', 'style', 'object']):
        s.decompose()
    for br in soup.find_all('br'):
        br.replace_with('\n')
    blocks = []
    for el in soup.find_all(['p', 'li', 'h1', 'h2', 'h3', 'h4', 'figcaption', 'a']):
        if el.name == 'a' and el.find_parent(['p', 'li']):
            continue
        if el.find(['p', 'li']):
            continue
        blocks.append(el.get_text())
    out = []
    for b in blocks:
        for line in b.split('\n'):
            for s in re.split(r'(?<=[.!?:])\s+(?=[¿¡A-ZÁÉÍÓÚÑ“«(0-9])', norm(line)):
                s = norm(s)
                if s:
                    out.append(s)
    return out


def page_text(path):
    soup = BeautifulSoup(Path(path).read_text(encoding='utf-8'), 'html.parser')
    for s in soup(['script', 'style', 'svg', 'dialog', 'template']):
        s.decompose()
    title = norm(soup.title.get_text()) if soup.title else ''
    main = soup.find('main')
    h1 = soup.find('h1')
    chrome = ' '.join(norm(x.get_text(' ')) for x in soup.find_all(['header', 'footer']))
    body = (norm(h1.get_text(' ')) if h1 else '') + ' ' + (norm(main.get_text(' ')) if main else '')
    return norm(body), norm(chrome), title


def squash(t):
    # compare without whitespace: inline markup (links, italics, language spans) moves spaces, never words
    return re.sub(r'\s+', '', t)


def main():
    src, pub = sys.argv[1], Path(sys.argv[2])
    posts = {p['slug']: p for p in json.load(open(src, encoding='utf-8'))['posts']}
    assert len(posts) == 30, len(posts)
    total = found_main = found_chrome = 0
    report = []
    for slug, built in PAGES.items():
        p = posts[slug]
        sents = [norm(BeautifulSoup(p['title'], 'html.parser').get_text())] + units(p['content'])
        body = chrome = ''
        for b in built:
            m, c, _ = page_text(pub / b)
            body += ' ' + m
            chrome += ' ' + c
        body, chrome = squash(norm(body)), squash(norm(chrome))
        missing, in_chrome = [], []
        for s in dict.fromkeys(sents):
            total += 1
            q = squash(s)
            if q in body:
                found_main += 1
            elif q in chrome:
                found_chrome += 1
                in_chrome.append(s)
            else:
                why = next((r for pat, r in EXPECTED if re.search(pat, s)), 'UNEXPLAINED')
                missing.append((s, why))
        report.append((slug, len(dict.fromkeys(sents)), missing, in_chrome))
    for slug, n, missing, in_chrome in report:
        print(f'== {slug}: {n} sentences, {len(missing)} missing, {len(in_chrome)} only in header/footer')
        for s in in_chrome:
            print(f'   in header/footer: «{s}»')
        for s, why in missing:
            print(f'   MISSING [{why}]: «{s}»')
    unexplained = sum(1 for _, _, m, _ in report for _, w in m if w == 'UNEXPLAINED')
    print(f'\nTotal {total} source sentences: {found_main} in the page body, {found_chrome} only in header/footer, '
          f'{total - found_main - found_chrome} missing ({unexplained} unexplained).')
    sys.exit(1 if unexplained else 0)


if __name__ == '__main__':
    main()
