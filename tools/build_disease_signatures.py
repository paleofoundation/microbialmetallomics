#!/usr/bin/env python3
"""Build the disease-signature research pathway and its source-led paper reviews."""
from pathlib import Path
from urllib.parse import quote
from html import unescape
import json
import re
from access_render import Citations, esc, render_blocks, claim_nodes

ROOT = Path(__file__).resolve().parents[1]
ORIGIN = 'https://microbialmetallomics.com'
DATA = ROOT / 'assets/data/disease-signatures'
TEMPLATE = (ROOT / 'library/spatial-metallomics-colorectal-cancer.html').read_text()
PREFIX = TEMPLATE.split('<main')[0]
SUFFIX = TEMPLATE[TEMPLATE.index('</main>') + 7:]
OLD_URL = ORIGIN + '/library/spatial-metallomics-colorectal-cancer'
OLD_TITLE = unescape(re.search(r'<h1>(.*?)</h1>', TEMPLATE, re.S)[1])
START = re.search(r'<div\b(?=[^>]*class="share-row")[^>]*>', TEMPLATE).start()
END = re.search(r'<p\b(?=[^>]*data-reading-status)[^>]*>.*?</p>', TEMPLATE, re.S).end()
CONTROLS = TEMPLATE[START:END]


def schema(data, route, hub=False):
    url = ORIGIN + route
    page = {'@type': 'CollectionPage' if hub else 'Article', 'headline': data['title'],
            'name': data['title'], 'description': data['description'], 'url': url,
            'mainEntityOfPage': url, 'datePublished': data['published'], 'dateModified': data['updated'],
            'inLanguage': 'en-US', 'keywords': data['keywords'],
            'author': {'@type': 'Organization', 'name': 'Microbial Metallomics', 'url': ORIGIN + '/about'},
            'publisher': {'@type': 'Organization', 'name': 'Microbial Metallomics', 'url': ORIGIN}}
    if not hub:
        page['citation'] = data['paper']['url']
        page['isPartOf'] = {'@type': 'CollectionPage', '@id': ORIGIN + '/disease-signatures', 'name': 'Metallomic signatures of disease'}
    else:
        page['hasPart'] = [{'@type': 'Article', 'url': ORIGIN + '/library/' + r['slug'], 'name': r['title']} for r in reviews]
    faq = {'@type': 'FAQPage', 'mainEntity': [{'@type': 'Question', 'name': f['question'], 'acceptedAnswer': {'@type': 'Answer', 'text': f['answer']}} for f in data.get('faqs', [])]}
    crumbs = {'@type': 'BreadcrumbList', 'itemListElement': [
        {'@type': 'ListItem', 'position': 1, 'name': 'Home', 'item': ORIGIN + '/'},
        *([] if hub else [{'@type': 'ListItem', 'position': 2, 'name': 'Disease signatures', 'item': ORIGIN + '/disease-signatures'}]),
        {'@type': 'ListItem', 'position': 2 if hub else 3, 'name': data['shortTitle'], 'item': url}]}
    return {'@context': 'https://schema.org', '@graph': [page, *([faq] if data.get('faqs') else []), crumbs]}


def head(data, route, hub=False, structured=None):
    out = re.sub(r'<script type="application/ld\+json">.*?</script>\s*', '', PREFIX, flags=re.S)
    out = re.sub(r'<title>.*?</title>', '<title>' + esc(data['title']) + ' | Microbial Metallomics</title>', out, flags=re.S)
    for attr, key, value in [('name', 'description', data['description']), ('property', 'og:title', data['title']), ('property', 'og:description', data['description']), ('property', 'og:url', ORIGIN + route), ('name', 'twitter:title', data['title']), ('name', 'twitter:description', data['description'])]:
        out = re.sub(r'<meta\b(?=[^>]*\b' + attr + '="' + re.escape(key) + '")[^>]*>', '<meta ' + attr + '="' + key + '" content="' + esc(value) + '">', out)
    out = re.sub(r'<link rel="canonical"[^>]*>', '<link rel="canonical" href="' + ORIGIN + route + '">', out)
    out = re.sub(r'<link\b[^>]*href="/assets/(?:metal-access|disease-signatures)\.css[^>]*>\s*', '', out)
    out = re.sub(r'<body[^>]*>', '<body class="journal-article signature-page">', out, count=1)
    if hub:
        out = out.replace('property="og:type" content="article"', 'property="og:type" content="website"')
    return out.replace('</head>', '<link rel="stylesheet" href="/assets/metal-access.css">\n<link rel="stylesheet" href="/assets/disease-signatures.css">\n<script type="application/ld+json">' + json.dumps(structured if structured is not None else schema(data, route, hub), ensure_ascii=False) + '</script>\n</head>')


def controls(data, route):
    out = CONTROLS
    out = out.replace(quote(OLD_URL, safe=''), quote(ORIGIN + route, safe=''))
    out = out.replace(OLD_URL, ORIGIN + route).replace('/library/spatial-metallomics-colorectal-cancer', route)
    title = quote(data['title'], safe='')
    url = quote(ORIGIN + route, safe='')
    out = re.sub(r'href="https://twitter.com/intent/tweet[^\"]*"', 'href="https://twitter.com/intent/tweet?url=' + url + '&amp;text=' + title + '"', out)
    out = re.sub(r'href="mailto:[^\"]*"', 'href="mailto:?subject=' + title + '&amp;body=' + title + '%0A%0A' + url + '"', out)
    return out


def cite_panel(data, route):
    url = ORIGIN + route
    text = 'Microbial Metallomics. ' + data['title'] + '. ' + data['published'] + '. ' + url
    payload = {'title': data['title'], 'date': data['published'], 'authors': ['Microbial Metallomics'], 'url': url}
    return '<details class="citation-panel" id="cite-this-page" data-citation><summary>Cite this page</summary><p data-citation-text>' + esc(text) + '</p><div class="article-tools"><button class="text-action" data-citation-copy type="button">Copy citation</button><button class="text-action" data-citation-bibtex type="button">Download BibTeX</button><button class="text-action" data-citation-ris type="button">Download RIS</button></div><p class="tool-status" data-citation-status role="status"></p></details><script id="page-citation-data" type="application/json">' + json.dumps(payload, ensure_ascii=False) + '</script><p class="print-source">Published at ' + url + '</p>'


def chapters(data, cite):
    seen = set()
    parts = []
    for section in data['sections']:
        for identifier in [section['id'], *section.get('aliases', [])]:
            assert re.fullmatch(r'[a-z][a-z0-9-]+', identifier) and identifier not in seen, identifier
            seen.add(identifier)
        for node in claim_nodes(section['blocks']):
            assert all(isinstance(n, int) and 0 < n <= len(data['sources']) for n in node['refs'])
        aliases = ''.join('<span class="anchor-alias" id="' + esc(a) + '"></span>' for a in section.get('aliases', []))
        parts.append('<section class="access-section" id="' + esc(section['id']) + '">' + aliases + '<h2>' + esc(section['title']) + '</h2>' + render_blocks(section['blocks'], cite) + '</section>')
    return ''.join(parts)


def faq(data):
    return '<section id="faq" class="faq-block"><h2>Questions worth asking</h2><div class="faq">' + ''.join('<details><summary>' + esc(f['question']) + '</summary><p>' + esc(f['answer']) + '</p></details>' for f in data.get('faqs', [])) + '</div></section>'


def sidebar(data, hub=False):
    nav = '<a href="#article-summary">The central idea</a>'
    if hub:
        nav += '<a href="#papers">Compare the papers</a>'
    nav += ''.join('<a href="#' + esc(s['id']) + '">' + esc(s.get('nav', s['title'])) + '</a>' for s in data['sections'])
    nav += '<a href="#faq">Questions</a><a href="#references">References</a>'
    return '<aside class="signature-sidebar"><div class="toc-label">In this ' + ('research pathway' if hub else 'review') + '</div><nav aria-label="On this page">' + nav + '</nav><div class="signature-sidebar-links"><a href="/disease-signatures">Disease-signature collection →</a><a href="/blog/metal-microbiome-disease-axis">The organizing essay →</a><a href="/metal-access">Follow the metal →</a></div></aside>'


def render_review(data):
    route = '/library/' + data['slug']
    cite = Citations(data['sources'])
    summary = '<section id="article-summary" class="signature-summary"><p class="access-evidence-label">What this changes</p><h2>' + esc(data.get('summaryTitle', 'The scientific opportunity')) + '</h2><p>' + cite.cite(data['summary']) + '</p></section>'
    body = chapters(data, cite.cite)
    assert set(cite.order) == set(range(1, len(data['sources']) + 1)), data['slug']
    paper = data['paper']
    source = '<div class="journal-source-link"><a href="' + esc(paper['url']) + '" target="_blank" rel="noopener noreferrer">Read the primary paper ↗</a><span>' + esc(paper['journal']) + ' · ' + str(paper['year']) + ' · DOI: ' + esc(paper['doi']) + '</span></div>'
    primary = '<div class="citation-box"><span class="lbl">Primary study</span><p>' + esc(paper['authors']) + '. <cite>' + esc(paper['title']) + '</cite>. ' + esc(paper['journal']) + ' (' + str(paper['year']) + ').</p></div>'
    hero = '<section class="hero-band signature-hero"><div class="wrap"><nav class="breadcrumb" aria-label="Breadcrumb"><a href="/">Home</a><span>/</span><a href="/disease-signatures">Disease signatures</a><span>/</span><span>' + esc(data['shortTitle']) + '</span></nav><p class="eyebrow">Disease signatures · Paper review</p><h1>' + esc(data['title']) + '</h1><p class="article-lead">' + esc(data['deck']) + '</p><p class="signature-byline">Review and research synthesis by <a href="/about">Microbial Metallomics</a></p>' + controls(data, route) + source + '</div></section>'
    article = '<div class="article-format">Source study: ' + esc(data['design']) + ' · ' + esc(data['setting']) + '. <a href="/evidence-guide#from-mechanism-to-hypothesis">Reading findings, mechanisms, and proposals</a></div>' + summary + primary + body + faq(data) + cite.references() + cite_panel(data, route)
    content = '<main id="main-content">' + hero + '<div class="wrap signature-layout"><article class="article-body access-prose">' + article + '</article>' + sidebar(data) + '</div></main>'
    (ROOT / (route.lstrip('/') + '.html')).write_text(head(data, route) + content + SUFFIX)


def cards():
    parts = []
    for r in reviews:
        c = hub_data['cards'][r['slug']]
        parts.append('<article class="signature-card" data-signature-group="' + esc(c['group']) + '"><p class="access-evidence-label">' + esc(c['label']) + '</p><h3><a href="/library/' + r['slug'] + '">' + esc(r['shortTitle']) + '</a></h3><p>' + esc(c['finding']) + '</p><dl><dt>What becomes possible</dt><dd>' + esc(c['opportunity']) + '</dd><dt>The missing microbial measurement</dt><dd>' + esc(c['missing']) + '</dd></dl><a class="signature-card-link" href="/library/' + r['slug'] + '">Read the full review →</a></article>')
    return '<section id="papers" class="signature-collection"><p class="eyebrow">Five close readings</p><h2>Compare the evidence. Choose the next experiment.</h2><p>Three studies map dementia brain tissue; a tumor study adds spatial gene expression; a pregnancy cohort tests prospective serum associations. These are complementary designs, not interchangeable biomarkers or a pooled dataset.</p><div class="signature-filters" role="group" aria-label="Filter paper reviews" hidden><button type="button" data-signature-filter="all" aria-pressed="true">All five papers</button><button type="button" data-signature-filter="brain" aria-pressed="false">Brain tissue</button><button type="button" data-signature-filter="tumor" aria-pressed="false">Tumor microenvironment</button><button type="button" data-signature-filter="serum" aria-pressed="false">Serum &amp; pregnancy</button></div><p class="signature-filter-status" role="status" aria-live="polite" data-signature-count>Showing all five papers</p><div class="signature-card-grid">' + ''.join(parts) + '</div></section>'


def render_hub():
    d = hub_data
    route = '/disease-signatures'
    cite = Citations(d['sources'])
    summary = '<section id="article-summary" class="signature-summary"><p class="access-evidence-label">The central idea</p><h2>' + esc(d['summaryTitle']) + '</h2><p>' + cite.cite(d['summary']) + '</p></section>'
    body = chapters(d, cite.cite)
    assert set(cite.order) == set(range(1, len(d['sources']) + 1))
    hero = '<section class="hero-band signature-hero"><div class="wrap"><nav class="breadcrumb" aria-label="Breadcrumb"><a href="/">Home</a><span>/</span><span>Disease signatures</span></nav><p class="eyebrow">A research pathway</p><h1>' + esc(d['title']) + '</h1><p class="article-lead">' + esc(d['deck']) + '</p><div class="signature-hero-links"><a href="#papers">Explore the five papers →</a><a href="/library/dementia-lewy-bodies-brain-metallomic-signatures">Begin with the dementia study →</a></div></div></section>'
    content = '<main id="main-content">' + hero + '<div class="wrap signature-layout"><article class="article-body access-prose">' + summary + cards() + body + faq(d) + cite.references() + '</article>' + sidebar(d, True) + '</div></main>'
    suffix = re.sub(r'<script[^>]*src="/assets/disease-signatures.js[^>]*></script>\s*', '', SUFFIX)
    suffix = suffix.replace('</body>', '<script src="/assets/disease-signatures.js" defer></script>\n</body>')
    (ROOT / 'disease-signatures.html').write_text(head(d, route, True) + content + suffix)


reviews = [json.loads(p.read_text()) for p in sorted(DATA.glob('*-review.json'))]
hub_data = json.loads((DATA / 'hub.json').read_text())
order = list(hub_data['cards'])
reviews.sort(key=lambda r: order.index(r['slug']))
assert len(reviews) == 5
if __name__ == '__main__':
    for review in reviews:
        render_review(review)
    render_hub()
    print('Built disease-signature pathway and', len(reviews), 'paper reviews.')
