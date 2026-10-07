#!/usr/bin/env python3
"""Build two source-led research series, reusable evidence ledgers and discovery cards."""
from pathlib import Path
from html import escape
import csv
import io
import json
import re
import argparse
from access_render import Citations, esc, render_blocks
from author_identity import site_author, author_schema, author_byline
from build_disease_signatures import head, controls, chapters, faq, cite_panel, SUFFIX
from check_host_series import EXPECTED, validate_article, release_scope

ROOT = Path(__file__).resolve().parents[1]
ORIGIN = 'https://microbialmetallomics.com'
DATA = ROOT / 'assets/data/host-defense'


def metadata(d, route, collection, hub=False):
    page = {'@type': 'CollectionPage' if hub else 'Article', 'headline': d['title'], 'name': d['title'],
            'description': d['description'], 'url': ORIGIN + route, 'mainEntityOfPage': ORIGIN + route,
            'datePublished': d['published'], 'dateModified': d['updated'], 'inLanguage': 'en-US',
            'author': author_schema(site_author(d.get('authorSlug', 'karen-pendergrass'))),
            'publisher': {'@type': 'Organization', 'name': 'Microbial Metallomics', 'url': ORIGIN},
            'keywords': d['keywords'], 'image': {'@type': 'ImageObject', 'url': ORIGIN + '/assets/series-covers/' + (route.lstrip('/') if hub else d['slug']) + '.png', 'width': 1200, 'height': 630}}
    if hub:
        page['hasPart'] = [{'@type': 'Article', 'url': ORIGIN + '/library/' + r['slug'], 'name': r['title']} for r in reviews if r['series'] == collection['id']]
    else:
        page['citation'] = [s['url'] for s in d['sources']]
        page['isPartOf'] = {'@type': 'CollectionPage', '@id': ORIGIN + collection['route'], 'name': collection['title']}
        page['about'] = [{'@type': 'Thing', 'name': part.strip()} for part in d['keywords'].split(',')[:8]]
    crumbs = [{'@type': 'ListItem', 'position': 1, 'name': 'Home', 'item': ORIGIN + '/'}]
    if not hub: crumbs.append({'@type': 'ListItem', 'position': 2, 'name': collection['title'], 'item': ORIGIN + collection['route']})
    crumbs.append({'@type': 'ListItem', 'position': len(crumbs) + 1, 'name': d['shortTitle'], 'item': ORIGIN + route})
    graph = [page, {'@type': 'BreadcrumbList', 'itemListElement': crumbs}]
    if d.get('faqs'):
        graph.append({'@type': 'FAQPage', 'mainEntity': [{'@type': 'Question', 'name': f['question'], 'acceptedAnswer': {'@type': 'Answer', 'text': f['answer']}} for f in d['faqs']]})
    return {'@context': 'https://schema.org', '@graph': graph}


def page_head(d, route, collection, hub=False):
    out = head(d, route, hub, structured=metadata(d, route, collection, hub))
    image = ORIGIN + '/assets/series-covers/' + (route.lstrip('/') if hub else d['slug']) + '.png'
    for attr, key in [('property', 'og:image'), ('name', 'twitter:image')]:
        out = re.sub(r'<meta\b(?=[^>]*' + attr + '="' + key + '")[^>]*>', '<meta ' + attr + '="' + key + '" content="' + image + '">', out)
    out = out.replace('</head>', '<meta property="og:image:alt" content="' + esc(d['title']) + ' — Microbial Metallomics research series"><meta property="og:image:width" content="1200"><meta property="og:image:height" content="630"><link rel="stylesheet" href="/assets/host-defense.css">\n</head>')
    return out.replace('class="journal-article signature-page"', 'class="journal-article signature-page host-series-page"')


def page_suffix():
    return SUFFIX.replace('</body>', '<script src="/assets/host-defense.js" defer></script>\n</body>')


def source_provenance(references, cite):
    for number, old in enumerate(cite.order, 1):
        s = cite.sources[old - 1]
        detail = '<details class="host-source-context"><summary>Study setting &amp; source access</summary><p><strong>' + esc(s['studyType']) + '.</strong> ' + esc(s['setting']) + '</p><p>' + esc(s['note']) + '</p><p>Source access: ' + esc(s['access'].replace('-', ' ')) + ' · ' + esc(s['kind']) + '</p></details>'
        pattern = r'(<li id="ref-' + str(number) + r'".*?)(</li>)'
        references = re.sub(pattern, lambda m: m[1] + detail + m[2], references, count=1, flags=re.S)
    return references


def evidence_ledger(d, cite):
    rows = []
    for claim in d['claims']:
        rows.append('<tr id="claim-' + esc(claim['id']) + '"><th scope="row">' + esc(claim['claim']) + '</th><td><span class="host-evidence">' + esc(claim['evidence'].replace('-', ' ')) + '</span><br>' + esc(claim['setting']) + '</td><td>' + cite({'text': claim['boundary'], 'refs': claim['refs']}) + '</td></tr>')
    return '<section id="evidence-ledger"><h2>Trace the central claims</h2><p>Each claim carries its setting, source, and interpretation boundary. Experimental proposals are identified separately in the review.</p><details class="host-ledger"><summary>Open the evidence ledger (' + str(len(rows)) + ' claims)</summary><div class="access-table-wrap" role="region" aria-label="Central claim evidence ledger" tabindex="0"><table class="access-table"><thead><tr><th scope="col">Claim</th><th scope="col">Evidence &amp; setting</th><th scope="col">Boundary &amp; source</th></tr></thead><tbody>' + ''.join(rows) + '</tbody></table></div></details><p><a href="/assets/data/host-defense/claims.csv" download>Download the complete series claim ledger (CSV) →</a></p></section>'


def sidebar(d, collection):
    nav = '<a href="#article-summary">The question</a>' + ''.join('<a href="#' + s['id'] + '">' + esc(s.get('nav', s['title'])) + '</a>' for s in d['sections']) + '<a href="#field-note">Shareable field note</a><a href="#evidence-ledger">Evidence ledger</a><a href="#faq">Questions</a><a href="#references">Sources</a>'
    return '<aside class="signature-sidebar"><div class="toc-label">In this deep dive</div><nav aria-label="On this page">' + nav + '</nav><div class="signature-sidebar-links"><a href="' + collection['route'] + '">' + esc(collection['title']) + ' →</a><a href="/disease-signatures">Disease signatures →</a><a href="/metal-access">Follow the metal →</a></div></aside>'


def field_note(d, cite):
    note = d['share']
    text = note['hook'] + ' ' + note['explanation'] + ' ' + note['qualification'] + '\n' + ORIGIN + '/library/' + d['slug']
    return '<section id="field-note" class="host-field-note"><p class="eyebrow">A field note worth sharing</p><h2>' + esc(note['hook']) + '</h2><p>' + cite({'text': note['explanation'], 'refs': note['refs']}) + '</p><p class="host-note-context">' + esc(note['qualification']) + '</p><button type="button" class="text-action" data-copy-field-note>Copy this note with context</button><textarea class="host-copy-fallback" readonly aria-label="Field note with context and source link" hidden>' + esc(text) + '</textarea><p class="tool-status" data-field-note-status role="status"></p></section>'


def render_article(d, collection):
    route = '/library/' + d['slug']
    cite = Citations(d['sources'])
    summary = '<section id="article-summary" class="signature-summary"><p class="access-evidence-label">The question that changes the interpretation</p><h2>' + esc(d.get('summaryTitle', 'Follow the metal to its next destination')) + '</h2><p>' + cite.cite(d['summary']) + '</p></section>'
    body = chapters(d, cite.cite)
    note = field_note(d, cite.cite)
    ledger = evidence_ledger(d, cite.cite)
    assert set(cite.order) == set(range(1, len(d['sources']) + 1))
    references = source_provenance(cite.references(), cite).replace('Primary studies supporting the linked statements. The framework and proposed experiments are editorial synthesis, not a clinical guideline or a systematic review.', 'Sources supporting the numbered claims. This is a narrative research synthesis. Each study’s model and the limits of its interpretation are recorded in the evidence ledger; proposed experiments are editorial analysis.')
    related = '<section class="host-related"><h2>Continue the investigation</h2><div class="access-reading-links">' + ''.join('<a href="' + esc(r['url']) + '"><strong>' + esc(r['title']) + '</strong><span>' + esc(r['description']) + '</span></a>' for r in d['related']) + '</div></section>'
    hero = '<section class="hero-band signature-hero"><div class="wrap"><nav class="breadcrumb" aria-label="Breadcrumb"><a href="/">Home</a><span>/</span><a href="' + collection['route'] + '">' + esc(collection['title']) + '</a><span>/</span><span>' + esc(d['shortTitle']) + '</span></nav><p class="eyebrow">' + esc(collection['title']) + ' · Deep dive</p><h1>' + esc(d['title']) + '</h1><p class="article-lead">' + esc(d['deck']) + '</p><p class="signature-byline">Research synthesis by ' + author_byline(site_author(d.get('authorSlug', 'karen-pendergrass'))) + '</p>' + controls(d, route) + '<div class="journal-source-link"><a href="#references">Explore the primary sources ↓</a><span>Narrative synthesis · ' + str(len(d['sources'])) + ' sources · model and compartment stated beside the claims</span></div></div></section>'
    article = '<div class="article-format">Mechanisms, microbial counterstrategies, and experiments worth doing. <a href="/evidence-guide#from-mechanism-to-hypothesis">How this guide connects evidence and hypotheses</a></div>' + summary + body + note + ledger + faq(d) + references + cite_panel(d, route) + related
    out = page_head(d, route, collection) + '<main id="main-content">' + hero + '<div class="wrap signature-layout"><article class="article-body access-prose">' + article + '</article>' + sidebar(d, collection) + '</div></main>' + page_suffix()
    (ROOT / (route.lstrip('/') + '.html')).write_text(out)


def render_hub(collection):
    selected = [d for d in reviews if d['series'] == collection['id']]
    all_sources = []
    positions = {}
    for d in selected:
        for s in d['sources']:
            if s['url'] not in positions: positions[s['url']] = len(all_sources) + 1; all_sources.append(s)
    cite = Citations(all_sources)
    cards = []
    for d in selected:
        meta = config['articles'][d['slug']]
        refs = [positions[d['sources'][r - 1]['url']] for r in d['share']['refs']]
        cards.append('<article class="host-study-card" data-metal-action="' + esc(meta['action']) + '"><p class="access-evidence-label">' + esc(meta['label']) + '</p><h3><a href="/library/' + d['slug'] + '">' + esc(d['shortTitle']) + '</a></h3><p class="host-card-hook">' + esc(d['share']['hook']) + '</p><p>' + cite.cite({'text': d['share']['explanation'], 'refs': refs}) + '</p><p class="host-note-context">' + esc(d['share']['qualification']) + '</p><a class="signature-card-link" href="/library/' + d['slug'] + '">Read the full investigation →</a></article>')
    actions = list(dict.fromkeys(config['articles'][d['slug']]['action'] for d in selected))
    filters = '<div class="signature-filters" data-host-filters role="group" aria-label="Filter by metal-handling strategy" hidden><button type="button" data-metal-filter="all" aria-pressed="true">All strategies</button>' + ''.join('<button type="button" data-metal-filter="' + esc(a) + '" aria-pressed="false">' + esc(config['actions'][a]) + '</button>' for a in actions) + '</div><p class="tool-status" data-host-count role="status" aria-live="polite">' + str(len(selected)) + ' deep dives</p>'
    intro = '<section class="host-hub-intro"><div class="wrap"><p class="eyebrow">A connected research series</p><h1>' + esc(collection['title']) + '</h1><p class="article-lead">' + esc(collection['deck']) + '</p><p>' + esc(collection['opening']) + '</p><div class="signature-hero-links"><a href="#deep-dives">Explore the deep dives →</a><a href="' + collection['companion']['url'] + '">' + esc(collection['companion']['label']) + ' →</a></div></div></section>'
    path = render_blocks([{'type': 'path', 'caption': 'The same questions travel with every mechanism.', 'steps': [{'label': 'The interaction', 'text': 'Which ligand or transporter acts on which metal species, under what conditions?'}, {'label': 'The destination', 'text': 'Does the metal stay bound, change compartments, reach a microbe, or leave the body?'}, {'label': 'The consequence', 'text': 'What function changes—and what experiment would separate the competing explanations?'}]}], cite.cite)
    notes = '<section class="host-framework"><h2>' + esc(collection['frameworkTitle']) + '</h2>' + ''.join('<p>' + esc(p) + '</p>' for p in collection['framework']) + path + '<p><a href="/assets/data/host-defense/claims.csv" download>Download the source-linked claim ledger for both series (CSV) →</a></p></section>'
    refs = cite.references().replace('Primary studies supporting the linked statements. The framework and proposed experiments are editorial synthesis, not a clinical guideline or a systematic review.', 'These primary sources support the field notes above. Each full review includes its complete bibliography, evidence ledger, competing explanations, and proposed next experiments.')
    d = {**collection, 'shortTitle': collection['title'], 'published': '2026-10-02', 'updated': '2026-10-02'}
    content = '<main id="main-content">' + intro + '<div class="wrap host-hub-body"><section id="deep-dives"><h2>' + esc(collection['collectionTitle']) + '</h2>' + filters + '<div class="host-card-grid">' + ''.join(cards) + '</div></section>' + notes + refs + '</div></main>'
    (ROOT / (collection['route'].lstrip('/') + '.html')).write_text(page_head(d, collection['route'], collection, True) + content + page_suffix())


def export_ledger():
    out = io.StringIO()
    columns = ['article', 'claimId', 'claim', 'evidence', 'setting', 'boundary', 'sources', 'url']
    writer = csv.DictWriter(out, fieldnames=columns, lineterminator='\n'); writer.writeheader()
    for d in reviews:
        for c in d['claims']:
            writer.writerow(dict(article=d['title'], claimId=c['id'], claim=c['claim'], evidence=c['evidence'], setting=c['setting'], boundary=c['boundary'], sources='; '.join(d['sources'][n - 1]['url'] for n in c['refs']), url=ORIGIN + '/library/' + d['slug'] + '#claim-' + c['id']))
    (DATA / 'claims.csv').write_text(out.getvalue())


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--preview-selection', type=Path, help='Explicit draft subset; does not change the complete-series release gate')
    parser.add_argument('--release', type=Path, default=DATA / 'release.json', help='Explicit publication scope (default: current release.json)')
    args = parser.parse_args()
    config = json.loads((DATA / 'series.json').read_text())
    reviews = []
    selected = json.loads(args.preview_selection.read_text()) if args.preview_selection else release_scope(json.loads(args.release.read_text()))[0]
    assert selected and len(selected) == len(set(selected)) and set(selected).issubset(EXPECTED), 'Invalid preview selection'
    for slug in selected:
        path = DATA / 'reviews' / (slug + '.json')
        d = json.loads(path.read_text())
        errors = validate_article(d, slug)
        assert not errors, (slug, errors)
        reviews.append(d)
    for d in reviews: render_article(d, config['series'][d['series']])
    for collection in config['series'].values(): render_hub(collection)
    export_ledger()
    print('Built', len(reviews), 'deep dives, two research hubs, and a source-linked claim ledger.' + (' DRAFT SUBSET: complete-series release remains gated.' if args.preview_selection else ''))
