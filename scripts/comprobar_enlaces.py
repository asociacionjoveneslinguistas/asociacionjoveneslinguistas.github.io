"""Link check for the built site: every internal link resolves, every fragment exists, every document link points to a file.

Usage: python3 scripts/comprobar_enlaces.py <public/> [<base URL>] [--wp <pages_v1.json>]

With --wp, it also checks that every document (PDF, DOCX) the WordPress pages linked to is served at the same
/wp-content/uploads/ path, so old links keep working once the domain points here.

Internal means a relative URL or one on the base URL. External URLs are counted and listed by host, not fetched.
"""
import re, sys
from collections import Counter, defaultdict
from pathlib import Path
from urllib.parse import urlsplit, unquote
from bs4 import BeautifulSoup

pub = Path(sys.argv[1]).resolve()
args = sys.argv[2:]
wp = None
if '--wp' in args:
    wp = args[args.index('--wp') + 1]
    args = args[:args.index('--wp')]
base = args[0] if args else 'https://asociacionjoveneslinguistas.github.io/'
base_host = urlsplit(base).netloc
ids = {}
pages = sorted(pub.rglob('*.html'))


def ids_of(path):
    if path not in ids:
        soup = BeautifulSoup(path.read_text(encoding='utf-8'), 'html.parser')
        ids[path] = {el['id'] for el in soup.find_all(id=True)}
    return ids[path]


def target(path_part):
    p = pub / unquote(path_part).lstrip('/')
    if p.is_dir():
        p = p / 'index.html'
    return p


broken, missing_frag, external = [], [], Counter()
docs = set()
checked = 0
for page in pages:
    soup = BeautifulSoup(page.read_text(encoding='utf-8'), 'html.parser')
    refs = [(t.name, t.get('href')) for t in soup.find_all(['a', 'link']) if t.get('href')]
    refs += [(t.name, t.get('src')) for t in soup.find_all(['img', 'script', 'source', 'iframe']) if t.get('src')]
    refs += [('div', t.get('data-src')) for t in soup.find_all(attrs={'data-src': True})]
    refs += [('div', t.get(a)) for a in ('data-lib', 'data-worker') for t in soup.find_all(attrs={a: True})]
    for tag, url in refs:
        u = urlsplit(url)
        if u.scheme in ('mailto', 'tel'):
            continue
        if u.scheme in ('http', 'https') and u.netloc != base_host:
            external[u.netloc] += 1
            continue
        checked += 1
        if not u.path:  # same-page fragment
            t = page
        else:
            path = u.path if u.path.startswith('/') else str((page.parent / u.path).relative_to(pub))
            t = target(path)
        rel = page.relative_to(pub)
        if not t.exists():
            broken.append((str(rel), url))
            continue
        if t.suffix.lower() in ('.pdf', '.docx', '.doc'):
            docs.add(str(t.relative_to(pub)))
        if u.fragment and t.suffix == '.html' and u.fragment not in ids_of(t):
            missing_frag.append((str(rel), url))

print(f'{len(pages)} HTML files; {checked} internal references checked; {len(docs)} distinct documents (PDF/DOCX) linked, all present: {not any(b[1].lower().endswith((".pdf", ".docx")) for b in broken)}')
print(f'broken internal references: {len(broken)}')
for p, u in broken:
    print('   BROKEN', p, '->', u)
print(f'missing fragments: {len(missing_frag)}')
for p, u in missing_frag:
    print('   NO ID', p, '->', u)
print(f'external references (not fetched): {sum(external.values())} to {len(external)} hosts')
for h, n in external.most_common():
    print(f'   {n:4d} {h}')
old_missing = []
if wp:
    import json
    old = set()
    for post in json.load(open(wp, encoding='utf-8'))['posts']:
        for url in re.findall(r'(?:href|data)="([^"]+)"', post['content']):
            m = re.match(r'https?://(?:www\.)?asociacionjoveneslinguistas\.(?:org|wordpress\.com)(/wp-content/uploads/[^?#"]+\.(?:pdf|docx?))', url, re.I)
            if m:
                old.add(m.group(1))
    old_missing = [u for u in sorted(old) if not target(u).exists()]
    print(f'documents linked from the WordPress pages: {len(old)}; served at the same path: {len(old) - len(old_missing)}')
    for u in old_missing:
        print('   NOT SERVED', u)
sys.exit(1 if broken or missing_frag or old_missing else 0)
