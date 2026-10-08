"""Move complete source blocks into a consistent, idempotent reading hierarchy."""
import re
from html_blocks import Blocks, edit


def shared_navigation(source, nav, menu):
    """Attribute order varies between generators; locate actual elements."""
    doc = Blocks(source)
    changes = []
    for node in doc.find(cls='nav-links'):
        changes.append((node.start, node.end, nav))
    for node in doc.find(cls='mega-menu'):
        changes.append((node.start, node.end, menu))
    return edit(source, changes)


def add_class(source, name):
    def replace(match):
        tag = match.group()
        if 'class=' in tag:
            return re.sub(r'class="([^"]*)"', lambda m: 'class="' +
                          ' '.join(dict.fromkeys([*m[1].split(), name])) + '"', tag, count=1)
        return tag[:-1] + ' class="' + name + '">'
    return re.sub(r'<body\b[^>]*>', replace, source, count=1)


def article_layout(source):
    doc = Blocks(source)
    hero = doc.one(cls='hero-band')
    summary = doc.one(id='article-summary')
    if not hero or not summary or summary.within(hero):
        return source
    wrap = doc.one(cls='wrap', within=hero)
    if not wrap:
        return source
    changes = [(summary.start, summary.end, '')]
    overview = doc.raw(summary)
    takeaways = doc.one(cls='takeaways')
    if takeaways:
        listing = doc.one(tag='ul', within=takeaways) or doc.one(tag='ol', within=takeaways)
        items = [n for n in listing.children if n.tag == 'li'] if listing else []
        if items:
            overview += '<div class="reading-takeaways"><h2>Key takeaways</h2><ul>' + ''.join(doc.raw(n) for n in items[:3]) + '</ul></div>'
            remainder = ('<div class="reading-further-findings"><h2>Further findings</h2><ul>' +
                         ''.join(doc.raw(n) for n in items[3:]) + '</ul></div>') if len(items) > 3 else ''
            changes.append((takeaways.start, takeaways.end, remainder))
    context = doc.one(cls='article-format')
    if context and not context.within(hero):
        overview = doc.raw(context) + overview
        changes.append((context.start, context.end, ''))
    correction = doc.one(cls='editorial-correction')
    if correction and not correction.within(hero):
        overview += doc.raw(correction)
        changes.append((correction.start, correction.end, ''))
    utility = doc.one(cls='share-row', within=hero) or doc.one(cls='article-tools', within=hero)
    position = utility.start if utility else wrap.close
    changes.append((position, position, '<div class="reading-overview">' + overview + '</div>'))
    return add_class(edit(source, changes), 'reading-article')


def remove_routine_review_dates(source):
    # Keep dates in structured data and publication metadata. Corrections are
    # editorial content and must remain visible next to the summary.
    doc = Blocks(source)
    changes = []
    for meta in doc.find(cls='article-meta'):
        for index, node in enumerate(meta.children):
            text = re.sub('<[^>]+>', '', doc.content(node)).strip()
            if node.has('am-item') and re.match(r'Updated\s', text):
                start = node.start
                if index and meta.children[index-1].has('am-sep'):
                    start = meta.children[index-1].start
                changes.append((start, node.end, ''))
    return edit(source, changes)


def move_metadata(source):
    doc = Blocks(source)
    hero = doc.one(cls='hero-band')
    if not hero or 'reading-article' not in source:
        return source
    meta = doc.one(cls='meta-row', within=hero)
    if not meta or doc.one(cls='reading-topics'):
        return source
    pills = doc.find(cls='pill', within=meta)
    keep = {'Article', 'Original Research', 'Paper review', 'Paper Review', 'Case Study',
            'Preprint', 'Journal article', 'Journal', 'Standard', 'Critical Commentary', 'Essay'}
    topics = [n for n in pills if re.sub('<[^>]+>', '', doc.content(n)).strip() not in keep]
    if not topics:
        return source
    wrap = doc.one(cls='wrap', within=hero)
    tags = '<details class="reading-topics"><summary>Article topics</summary><div class="meta-row">' + ''.join(doc.raw(n) for n in topics) + '</div></details>'
    return edit(source, [(n.start, n.end, '') for n in topics] + [(wrap.close, wrap.close, tags)])


def contents_disclosures(source):
    doc = Blocks(source)
    changes = []
    classes = {'toc-sidebar', 'toc', 'pillar-sidebar', 'signature-sidebar', 'atlas-toc', 'access-toc'}
    for node in doc.nodes:
        if not node.end or not classes.intersection(node.attrs.get('class', '').split()):
            continue
        if doc.one(cls='reading-toc', within=node):
            continue
        body = doc.content(node)
        label = next((n for n in node.children if n.tag in ['h2', 'h3'] or n.has('toc-label')), None)
        if label:
            body = body[:label.start-node.inner] + body[label.end-node.inner:]
            title = doc.content(label)
            identity = ' id="' + label.attrs['id'] + '"' if label.attrs.get('id') else ''
        else:
            title, identity = 'On this page', ''
        changes.append((node.inner, node.close, '<details class="reading-toc" open><summary' + identity + '>' + title + '</summary>' + body + '</details>'))
    return edit(source, changes)


def directory_layout(source, route):
    if route not in {'/library', '/evidence'}:
        return source
    doc = Blocks(source)
    catalogue = doc.one(attr='data-catalogue')
    feature = doc.one(cls='signature-entry')
    links = doc.one(cls='tool-links')
    moving = [n for n in [feature, links] if n and catalogue and n.start < catalogue.start]
    if moving:
        source = edit(source, [(n.start, n.end, '') for n in moving] +
                      [(catalogue.end, catalogue.end, ''.join(doc.raw(n) for n in moving))])
    return add_class(source, 'reading-directory')


def disease_hub(source):
    doc = Blocks(source)
    intro = doc.one(id='article-summary')
    collection = doc.one(id='papers')
    if intro and collection and intro.start < collection.start:
        source = edit(source, [(intro.start, intro.end, ''), (collection.end, collection.end, doc.raw(intro))])
    return add_class(source, 'reading-hub')


def profile_layout(source):
    doc = Blocks(source)
    significance = doc.one(id='significance')
    works = doc.one(cls='person-works')
    if significance and works and significance.end < works.start:
        source = edit(source, [(works.start, works.end, ''), (significance.end, significance.end, doc.raw(works))])
    return add_class(source, 'reading-profile')


def refresh_reading_layout(root):
    count = 0
    for path in sorted(root.rglob('*.html')):
        if any(p.startswith('.') or p == 'node_modules' for p in path.relative_to(root).parts):
            continue
        route = '/' + path.relative_to(root).with_suffix('').as_posix()
        source = old = path.read_text()
        if path.parent.name in {'blog', 'library', 'research'}:
            source = add_class(remove_routine_review_dates(move_metadata(article_layout(source))), 'reading-article')
        if path.parent.name == 'people':
            source = profile_layout(source)
        source = directory_layout(source, route)
        if route == '/disease-signatures':
            source = disease_hub(source)
        if route in {'/topics', '/host-metal-defense', '/unexpected-metal-biology', '/microbiome'}:
            source = add_class(source, 'reading-hub')
        source = contents_disclosures(source)
        source = re.sub(r'<link rel="stylesheet" href="/assets/reading\.css[^>]*>\s*', '', source)
        source = source.replace('</head>', '<link rel="stylesheet" href="/assets/reading.css">\n</head>')
        if '/assets/reading.js' not in source:
            source = source.replace('</body>', '<script src="/assets/reading.js" defer></script>\n</body>')
        if source != old:
            path.write_text(source)
            count += 1
    print('Applied shared reading layouts to', count, 'pages.')
