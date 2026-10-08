"""Render the compact guide-first homepage from the published reading catalog."""
from pathlib import Path
from html import escape
import json
import re
from html_blocks import Blocks, edit
from author_identity import orcid_link

ROOT = Path(__file__).resolve().parents[1]
FEATURE = '/blog/metal-microbiome-disease-axis'


def build_home(root=ROOT):
    path = root / 'index.html'
    source = path.read_text()
    data = json.loads((root / 'assets/data/articles.json').read_text())
    feature = next(r for r in data if r['url'] == FEATURE)
    latest = sorted((r for r in data if r['url'] != FEATURE),
                    key=lambda r: (r['date'], r['title']), reverse=True)[:3]
    cards = ''
    for record in latest:
        label = record['kind'] + (' · ' + record['status'] if record['status'] else '')
        cards += ('<article class="home-recent-item"><p class="home-meta">' + escape(label) +
                  ' <time datetime="' + escape(record['date']) + '">' + escape(record['date']) +
                  '</time></p><h3><a href="' + record['url'] + '">' + escape(record['title']) +
                  '</a></h3><p class="home-author">' + escape(' · '.join(record['authors'])) + '</p></article>')
    topics = [
        ('/microbiome', 'Metals & the gut microbiome', 'Explore how metal exposure and microbial communities interact.'),
        ('/host-metal-defense', 'Host metal defenses', 'Follow how the body binds, withholds, and redistributes metals.'),
        ('/disease-signatures', 'Disease signatures', 'Compare metal patterns in disease and the questions they raise.'),
        ('/unexpected-metal-biology', 'Unexpected metal biology', 'Investigate surprising interactions and the evidence behind them.'),
    ]
    topic_links = ''.join('<a class="home-topic" href="' + url + '"><h3>' + escape(title) +
                          '</h3><p>' + escape(description) + '</p></a>' for url, title, description in topics)
    main = '''<main id="main-content">
<section class="home-orientation" aria-labelledby="home-introduction-heading">
  <div class="wrap">
    <span id="field-guide" class="anchor-alias" aria-hidden="true"></span>
    <p class="eyebrow">An open guide to metals and microbial life</p>
    <h1 id="home-introduction-heading">How metals shape microbes<br class="home-title-break"> and the microbiome.</h1>
    <p class="home-definition">Microbial metallomics studies how microbes acquire, use, and transform metals—and what that chemistry means for health and the environment.</p>
    <button class="home-search" type="button" data-search-toggle aria-label="Search metals, microbes, papers, or people"><svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" aria-hidden="true"><circle cx="10.5" cy="10.5" r="6.5"></circle><path d="m16 16 5 5"></path></svg><span>Search metals, microbes, papers, or people</span><kbd>⌘ K</kbd></button>
    <noscript><p>Browse the <a href="/metals">metals atlas</a>, <a href="/evidence">research catalog</a>, or <a href="/glossary">glossary</a>.</p></noscript>
    <nav class="home-starts" aria-label="Choose your starting point">
      <a href="/science"><strong>Learn the basics</strong><span>Understand the field and its key ideas.</span></a>
      <a href="/metals"><strong>Explore a metal</strong><span>Find its role, mechanisms, and evidence.</span></a>
      <a href="/evidence"><strong>Find research</strong><span>Browse papers, reviews, and essays.</span></a>
    </nav>
  </div>
</section>
<section class="home-journal" aria-labelledby="selected-reading-heading">
  <div class="wrap home-journal-grid">
    <article class="home-feature">
      <div class="home-section-label"><h2 id="selected-reading-heading">Featured essay</h2><a href="/blog">All essays</a></div>
      <div class="home-feature-grid"><div>
        <p class="home-meta">The organizing framework</p>
        <h3><a href="/blog/metal-microbiome-disease-axis">The Metal–Microbiome–Disease Axis</a></h3>
        <p>Metals change microbial ecology. Microbes change metal chemistry. Explore the evidence connecting metal access, inflammation, and disease.</p>
        <p class="home-author"><a href="/people/karen-pendergrass">Karen Pendergrass</a> ORCID_MARKUP</p>
        <a class="home-reading-link" href="/blog/metal-microbiome-disease-axis">Read the essay</a>
        <p class="home-thesis-link"><a href="/start-here">Why metal access matters</a></p>
      </div><figure><a href="/blog/metal-microbiome-disease-axis" tabindex="-1" aria-hidden="true"><img src="/assets/microbial-metallomics-hero.jpg" width="768" height="1024" alt="" loading="lazy" decoding="async"></a><figcaption>Conceptual illustration</figcaption></figure></div>
    </article>
    <div class="home-recent"><div class="home-section-label"><h2>Latest writing</h2><a href="/updates">All updates</a></div>LATEST_CARDS</div>
  </div>
</section>
<section class="home-topics" aria-labelledby="home-topics-heading"><div class="wrap">
  <div class="home-section-label"><h2 id="home-topics-heading">Explore by topic</h2><a href="/topics">All topics</a></div>
  <div class="home-topic-grid">TOPIC_LINKS</div>
</div></section>
<section class="home-follow" id="newsletter"><div class="wrap home-follow-grid">
  <div><h2>Science with sources you can follow.</h2><p>Written by <a href="/people/karen-pendergrass">Karen Pendergrass</a>. Findings, proposed mechanisms, and open questions are distinguished throughout the guide.</p><a href="/editorial">Read our editorial standards</a></div>
  <div><h2>Keep up with the field.</h2><p>New research, paper reviews, and commentary.</p><div class="home-follow-links"><a class="btn btn-primary" href="/newsletter">Get the email digest</a><a href="/feeds">Follow by RSS</a></div></div>
</div></section>
</main>'''
    main = main.replace('LATEST_CARDS', cards).replace('TOPIC_LINKS', topic_links).replace(
        'ORCID_MARKUP', orcid_link('0000-0002-2348-7259', 'Karen Pendergrass'))
    doc = Blocks(source)
    oldmain = doc.one(tag='main')
    source = edit(source, [(oldmain.start, oldmain.end, main)])
    # The brand is a link; the visible page purpose is the only H1.
    source = re.sub(r'<h1>(<a\b[^>]*class="journal-wordmark".*?</a>)</h1>', r'\1', source, flags=re.S)
    def schema(match):
        data = json.loads(match.group(1))
        if '@graph' in data:
            data['@graph'] = [n for n in data['@graph'] if n.get('@type') not in ['FAQPage', 'DefinedTerm']]
        return '<script type="application/ld+json">' + json.dumps(data, ensure_ascii=False) + '</script>'
    source = re.sub(r'<script type="application/ld\+json">(.*?)</script>', schema, source, flags=re.S)
    # These page-specific styles no longer serve homepage content.
    source = re.sub(r'<link rel="stylesheet" href="/assets/(?:metals|host-defense)\.css[^>]*>\s*', '', source)
    if source != path.read_text():
        path.write_text(source)


if __name__ == '__main__':
    build_home()
    print('Built the guide-first homepage with three recent articles.')
