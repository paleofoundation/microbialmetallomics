#!/usr/bin/env python3
"""Build the sourced thesis and qualitative metal-access explorer."""
from pathlib import Path
import json, re
from access_render import Citations, esc, render_blocks, claim_nodes
ROOT = Path(__file__).resolve().parents[1]
ORIGIN = 'https://microbialmetallomics.com'
data = json.loads((ROOT / 'assets/data/metal-access.json').read_text())
for source in data['sources']:
    assert source['url'].startswith('https://')
    assert source['title'] and source['authors'] and source['year']
for section in [*data['thesis']['sections'], *data['explorer']['cases']]:
    assert re.fullmatch(r'[a-z][a-z0-9-]+', section['id'])
    for node in claim_nodes(section['blocks']):
        assert all(isinstance(n, int) and 0 < n <= len(data['sources']) for n in node['refs'])
original = (ROOT / 'start-here.html').read_text()
prefix = original.split('<main')[0]
suffix = original[original.index('</main>') + 7:]
suffix = re.sub(r'<script src="/assets/metal-access.js[^>]*></script>\s*', '', suffix)

def page(title, description, path, body, script=False):
    head = prefix
    head = re.sub(r'<title>.*?</title>', '<title>' + esc(title) + ' — Microbial Metallomics</title>', head, flags=re.S)
    head = re.sub(r'<script type="application/ld\+json">.*?</script>\s*', '', head, flags=re.S)
    head = re.sub(r'<link rel="canonical"[^>]*>', '<link rel="canonical" href="' + ORIGIN + path + '">', head)
    for attr, key, value in [('name','description',description),('property','og:title',title),('property','og:description',description),('property','og:url',ORIGIN+path),('name','twitter:title',title),('name','twitter:description',description)]:
        head = re.sub(r'<meta ' + attr + '="' + key + '"[^>]*>', '<meta ' + attr + '="' + key + '" content="' + esc(value) + '">', head)
    head = re.sub(r'<link rel="stylesheet" href="/assets/metal-access.css[^>]*>\s*', '', head)
    ld = {'@context':'https://schema.org','@type':'WebPage','name':title,'headline':title,'description':description,'url':ORIGIN+path,'inLanguage':'en-US','dateModified':data['updated'],'publisher':{'@type':'Organization','name':'Microbial Metallomics'}}
    head = head.replace('</head>', '<link rel="stylesheet" href="/assets/metal-access.css">\n<script type="application/ld+json">' + json.dumps(ld, ensure_ascii=False) + '</script>\n</head>')
    tail = suffix.replace('</body>', '<script src="/assets/metal-access.js" defer></script>\n</body>') if script else suffix
    return head + '<main id="main-content">' + body + '</main>' + tail

def hero(item, label):
    return '<section class="access-hero"><div class="wrap"><nav class="breadcrumb" aria-label="Breadcrumb"><a href="/">Home</a><span>/</span><span>' + esc(label) + '</span></nav><p class="eyebrow">' + esc(item['eyebrow']) + '</p><h1>' + esc(item['title']) + '</h1><p class="article-lead">' + esc(item['deck']) + '</p><p class="access-summary">' + esc(item['intro']) + '</p></div></section>'

thesis = data['thesis']
book = Citations(data['sources'])
sections = ''.join('<section id="' + esc(s['id']) + '"><h2>' + esc(s['title']) + '</h2>' + render_blocks(s['blocks'], book.cite) + '</section>' for s in thesis['sections'])
nav = ''.join('<a href="#' + esc(s['id']) + '">' + esc(s.get('nav', s['title'])) + '</a>' for s in thesis['sections'])
body = hero(thesis, 'Start here') + '<div class="wrap access-layout"><nav class="access-toc" aria-label="In this thesis"><h2>Start with the question</h2>' + nav + '<a href="#references">Sources</a><a href="/metal-access">Explore the compartments →</a></nav><article class="article-body access-prose">' + sections + book.references() + '</article></div>'
(ROOT / 'start-here.html').write_text(page(thesis['title'], thesis['description'], '/start-here', body))

explorer = data['explorer']
book = Citations(data['sources'])
buttons = '<button type="button" data-case="all" aria-pressed="true">All cases</button>' + ''.join('<button type="button" data-case="' + esc(c['id']) + '" aria-pressed="false" aria-controls="' + esc(c['id']) + '">' + esc(c['label']) + '</button>' for c in explorer['cases'])
panels = ''.join('<section class="access-scenario" id="' + esc(c['id']) + '" data-scenario aria-labelledby="' + esc(c['id']) + '-heading"><p class="access-evidence-label">' + esc(c['scope']) + '</p><h2 id="' + esc(c['id']) + '-heading">' + esc(c['title']) + '</h2>' + render_blocks(c['blocks'], book.cite) + '</section>' for c in explorer['cases'])
body = hero(explorer, 'Follow the metal') + '<div class="wrap access-explorer"><div class="access-scenario-controls" data-scenario-controls aria-label="Choose a mechanism case" hidden>' + buttons + '</div><p class="access-scenario-status" data-scenario-status role="status" aria-live="polite" hidden></p>' + panels + '<div class="access-prose">' + book.references() + '</div><p><button type="button" class="access-print-button" data-print-cases>Print all cases</button></p></div>'
(ROOT / 'metal-access.html').write_text(page(explorer['title'], explorer['description'], '/metal-access', body, script=True))

home_path = ROOT / 'index.html'
home = home_path.read_text()
callout = '<section class="access-home-callout" data-access-intro><div class="wrap"><div><p class="eyebrow">Start with a better question</p><h2>Enough metal.<br>Available to whom?</h2></div><div><p>A low blood measurement, a metal-rich tissue, and a nutrient-starved microbe can coexist. Follow the chemical form, the compartment, and the competition before interpreting the dose.</p><a href="/start-here">Read the organizing thesis →</a><a href="/metal-access">Follow the metal →</a></div></div></section>'
if 'data-access-intro' in home:
    home, count = re.subn(r'<section[^>]*data-access-intro[^>]*>.*?</section>', callout, home, flags=re.S)
    assert count == 1
else:
    assert home.count('<section class="home-field-tools">') == 1
    home = home.replace('<section class="home-field-tools">', callout + '\n<section class="home-field-tools">')
if '/assets/metal-access.css' not in home:
    home = home.replace('</head>', '<link rel="stylesheet" href="/assets/metal-access.css">\n</head>')
home_path.write_text(home)
print('Built the access thesis,', len(explorer['cases']), 'mechanism cases, and homepage entry point.')
