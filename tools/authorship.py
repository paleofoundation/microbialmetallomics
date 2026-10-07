"""Keep page credits, export authors and the site's research identity consistent.

Only page-level authors are normalized. Cited studies, researcher subjects and
scientific content retain their own identities. Run before catalog generation
and after other page generators through refresh_site.py.
"""
from html import escape
from html.parser import HTMLParser
import json
import re
from author_identity import author_byline, author_schema

ORIGIN = 'https://microbialmetallomics.com'
BRAND = 'Microbial Metallomics'
DEFAULT_AUTHOR = 'Karen Pendergrass'
TOPICS = ['Microbial metallomics', 'Heavy metals', 'Microbiome']
ARTICLE_TYPES = {'Article', 'BlogPosting', 'ScholarlyArticle', 'NewsArticle'}
PAGE_TYPES = ARTICLE_TYPES | {'WebPage', 'CollectionPage', 'AboutPage', 'ProfilePage', 'FAQPage'}
SCRIPT = re.compile(r'(<script\b[^>]*>)(.*?)(</script>)', re.S)


class Tags(HTMLParser):
    def __init__(self, source):
        super().__init__(convert_charrefs=True)
        self.tags = []
        self.feed(source)

    def handle_starttag(self, tag, attrs):
        self.tags.append((tag, dict(attrs)))


def attrs(source):
    return Tags(source).tags[0][1]


def types(node):
    value = node.get('@type', [])
    return {value} if isinstance(value, str) else set(value)


def nodes(data):
    return data if isinstance(data, list) else data.get('@graph', [data])


def set_head_tags(head, tag, attribute, key, replacements):
    pattern = r'<' + tag + r'\b[^>]*>\s*'
    head = re.sub(pattern, lambda m: '' if key in attrs(m[0]).get(attribute, '').split() else m[0], head)
    return head.rstrip() + '\n' + '\n'.join(replacements) + '\n'


def refresh_page(source, authors):
    # Generators may inherit the previous page's shared head. Replace this block.
    source = SCRIPT.sub(lambda m: '' if attrs(m[1]).get('id') == 'site-identity' else m[0], source)
    head, body = source.split('</head>', 1)
    tags = Tags(head).tags
    metadata = {a.get('name', a.get('property')): a.get('content', '') for t, a in tags if t == 'meta'}
    canonical = next((a.get('href') for t, a in tags if t == 'link' and a.get('rel') == 'canonical'), None)
    if not canonical:
        raise ValueError('Every public page needs a canonical URL before authorship is refreshed')
    names = [name.strip() for name in metadata.get('author', '').split(';') if name.strip() and name.strip() != BRAND]
    names = names or [DEFAULT_AUTHOR]
    unknown = set(names) - authors.keys()
    if unknown:
        raise ValueError('Unregistered page authors: ' + ', '.join(sorted(unknown)))
    identities = [author_schema(authors[name]) for name in names]
    credit = identities[0] if len(identities) == 1 else identities
    is_article = False
    has_page = False

    def structured(match):
        nonlocal is_article, has_page
        if attrs(match[1]).get('type') != 'application/ld+json':
            return match[0]
        data = json.loads(match[2])
        for node in nodes(data):
            if not PAGE_TYPES.intersection(types(node)):
                continue
            identity = node.get('url') or node.get('mainEntityOfPage') or node.get('@id')
            if isinstance(identity, dict):
                identity = identity.get('@id') or identity.get('url')
            if identity and identity.split('#')[0].rstrip('/') != canonical.rstrip('/'):
                continue
            has_page = True
            is_article |= bool(ARTICLE_TYPES.intersection(types(node)))
            node['author'] = credit
            parent = node.get('isPartOf')
            if isinstance(parent, dict) and 'CollectionPage' in types(parent):
                parent['isPartOf'] = {'@id': ORIGIN + '/#website'}
            else:
                node['isPartOf'] = {'@id': ORIGIN + '/#website'}
            node.setdefault('publisher', {'@type': 'Organization', 'name': BRAND})['@id'] = ORIGIN + '/#org'
        return match[1] + json.dumps(data, ensure_ascii=False) + match[3]

    head = SCRIPT.sub(structured, head)
    head = set_head_tags(head, 'meta', 'name', 'author',
                         ['<meta name="author" content="' + escape('; '.join(names), quote=True) + '">'])
    keywords = [x.strip() for x in metadata.get('keywords', '').split(',') if x.strip()]
    for keyword in [DEFAULT_AUTHOR, *TOPICS]:
        if keyword.casefold() not in {x.casefold() for x in keywords}:
            keywords.append(keyword)
    head = set_head_tags(head, 'meta', 'name', 'keywords',
                         ['<meta name="keywords" content="' + escape(', '.join(keywords), quote=True) + '">'])
    head = set_head_tags(head, 'link', 'rel', 'author',
                         ['<link rel="author" href="' + person['url'] + '">' for person in identities])
    head = set_head_tags(head, 'meta', 'property', 'article:author',
                         ['<meta property="article:author" content="' + person['url'] + '">' for person in identities] if is_article else [])
    primary = author_schema(authors[DEFAULT_AUTHOR])
    graph = [primary, {
        '@type': 'WebSite', '@id': ORIGIN + '/#website', 'url': ORIGIN + '/', 'name': BRAND,
        'inLanguage': 'en-US', 'author': {'@id': primary['@id']},
        'publisher': {'@id': ORIGIN + '/#org'},
        'about': [{'@type': 'Thing', 'name': topic} for topic in TOPICS],
    }, {
        '@type': 'Organization', '@id': ORIGIN + '/#org', 'name': BRAND, 'url': ORIGIN + '/',
        'founder': {'@id': primary['@id']},
    }]
    if not has_page:
        graph.append({'@type': 'WebPage', '@id': canonical + '#webpage', 'url': canonical,
                      'author': credit, 'isPartOf': {'@id': ORIGIN + '/#website'},
                      'publisher': {'@id': ORIGIN + '/#org'}})
    head += '<script id="site-identity" type="application/ld+json">' + json.dumps(
        {'@context': 'https://schema.org', '@graph': graph}, ensure_ascii=False) + '</script>\n'

    byline = author_byline(authors[DEFAULT_AUTHOR])
    body = body.replace('By <b>Microbial Metallomics</b>', 'By <b>' + byline + '</b>')
    body = body.replace('Reviewed by <b>Microbial Metallomics</b>', 'Reviewed by <b>' + byline + '</b>')
    body = body.replace('synthesis by <a href="/about">Microbial Metallomics</a>', 'synthesis by ' + byline)
    # Cards are often inside an article link; keep their author labels as text.
    body = body.replace('<div class="journal-card-author">Microbial Metallomics</div>',
                        '<div class="journal-card-author">' + DEFAULT_AUTHOR + '</div>')
    body = body.replace('Review by Microbial Metallomics', 'Review by ' + DEFAULT_AUTHOR)

    def citation(match):
        if attrs(match[1]).get('id') != 'page-citation-data':
            return match[0]
        data = json.loads(match[2])
        data['authors'] = names
        return match[1] + json.dumps(data, ensure_ascii=False) + match[3]

    body = SCRIPT.sub(citation, body)
    body = re.sub(r'(<p\b[^>]*\bdata-citation-text[^>]*>)[^<]*?(?=\. \()',
                  lambda m: m[1] + escape('; '.join(names)), body, flags=re.S)
    return head + '</head>' + body


def refresh_authorship(root):
    authors = {person['name']: person for person in json.loads((root / 'assets/data/people.json').read_text())
               if person.get('siteAuthor')}
    count = 0
    for path in sorted(root.rglob('*.html')):
        if any(part.startswith('.') or part == 'node_modules' for part in path.relative_to(root).parts):
            continue
        old = path.read_text()
        new = refresh_page(old, authors)
        if new != old:
            path.write_text(new)
        count += 1
    return count
