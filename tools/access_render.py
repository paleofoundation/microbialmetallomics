"""Small static renderers for the metal-access framework and profile deep dives."""
from collections import defaultdict
from html import escape


def esc(value):
    return escape(str(value), quote=True)


class Citations:
    def __init__(self, sources):
        self.sources = sources
        self.order = []
        self.counts = defaultdict(int)

    def cite(self, value):
        result = esc(value['text'])
        for old in value.get('refs', []):
            assert isinstance(old, int) and 0 < old <= len(self.sources), old
            if old not in self.order:
                self.order.append(old)
            number = self.order.index(old) + 1
            self.counts[number] += 1
            occurrence = self.counts[number]
            source = self.sources[old - 1]
            result += f' <sup class="citation"><a id="cite-{number}-{occurrence}" href="#ref-{number}" role="doc-noteref" aria-label="Reference {number}" title="{esc(source["title"])}">[{number}]</a></sup>'
        return result

    def references(self):
        rows = []
        for number, old in enumerate(self.order, 1):
            source = self.sources[old - 1]
            links = ''.join(f'<a href="#cite-{number}-{k}" role="doc-backlink" aria-label="Return to citation {number}, occurrence {k}">↩</a>' for k in range(1, self.counts[number] + 1))
            rows.append(f'<li id="ref-{number}" tabindex="-1">{esc(source["authors"])} ({esc(source["year"])}). {esc(source["title"])}. <a href="{esc(source["url"])}" aria-label="View source for reference {number}">View source</a><span class="reference-backlinks">{links}</span></li>')
        return '<section class="references access-references" id="references" aria-labelledby="references-heading"><h2 id="references-heading">Sources &amp; further reading</h2><p>Primary studies supporting the linked statements. The framework and proposed experiments are editorial synthesis, not a clinical guideline or a systematic review.</p><ol class="reference-list">' + ''.join(rows) + '</ol></section>'


def claim_nodes(blocks):
    """Yield every source-bearing node for validation and search indexing."""
    for block in blocks:
        if 'refs' in block:
            yield block
        for key in ['rows', 'items', 'steps']:
            for item in block.get(key, []):
                if 'refs' in item:
                    yield item


def render_blocks(blocks, cite):
    parts = []
    for block in blocks:
        kind = block['type']
        if kind == 'paragraph':
            parts.append('<p>' + cite(block) + '</p>')
        elif kind == 'heading':
            parts.append('<h3>' + esc(block['text']) + '</h3>')
        elif kind == 'table':
            rows = []
            for row in block['rows']:
                assert len(row['cells']) == len(block['headers'])
                cells = [esc(value) for value in row['cells']]
                if row.get('refs'):
                    cells[-1] += cite({'text': '', 'refs': row['refs']})
                rows.append('<tr><th scope="row">' + cells[0] + '</th>' + ''.join('<td>' + cell + '</td>' for cell in cells[1:]) + '</tr>')
            parts.append('<div class="access-table-wrap" role="region" aria-label="' + esc(block['caption']) + '" tabindex="0"><table class="access-table"><caption>' + esc(block['caption']) + '</caption><thead><tr>' + ''.join('<th scope="col">' + esc(h) + '</th>' for h in block['headers']) + '</tr></thead><tbody>' + ''.join(rows) + '</tbody></table></div>')
        elif kind == 'claims':
            cards = []
            for item in block['items']:
                cards.append('<div class="access-claim"><p class="access-evidence-label">' + esc(item['status']) + '</p><h3>' + esc(item['claim']) + '</h3><p>' + cite({'text': item['finding'], 'refs': item.get('refs', [])}) + '</p><p class="access-next-test"><strong>' + esc(item.get('nextLabel', 'What is still needed.')) + '</strong> ' + esc(item['missing']) + '</p></div>')
            parts.append('<div class="access-claims">' + ''.join(cards) + '</div>')
        elif kind == 'proposal':
            parts.append('<aside class="access-proposal"><p class="access-evidence-label">Proposed research · not a completed result</p><h3>' + esc(block['title']) + '</h3><p>' + cite(block) + '</p><ul>' + ''.join('<li>' + esc(v) + '</li>' for v in block['measures']) + '</ul><p><strong>What would change the interpretation.</strong> ' + esc(block['decision']) + '</p></aside>')
        elif kind == 'path':
            fork = block.get('layout') == 'fork'
            tag = 'ul' if fork else 'ol'
            klass = 'access-path access-path-fork' if fork else 'access-path'
            parts.append('<figure class="' + klass + '"><figcaption>' + esc(block['caption']) + '</figcaption><' + tag + '>' + ''.join('<li><strong>' + esc(v['label']) + '</strong><p>' + cite(v) + '</p></li>' for v in block['steps']) + '</' + tag + '></figure>')
        elif kind == 'link':
            assert block['url'].startswith('/')
            parts.append('<p class="access-link"><a href="' + esc(block['url']) + '">' + esc(block['text']) + ' <span aria-hidden="true">→</span></a></p>')
        else:
            raise ValueError('Unsupported block: ' + kind)
    return '\n'.join(parts)


def render_deep_dive(access, cite):
    return ''.join('<section id="' + esc(section['id']) + '" class="access-section"><p class="access-evidence-label">' + esc(section.get('eyebrow', 'Follow the metal')) + '</p><h2>' + esc(section['title']) + '</h2>' + render_blocks(section['blocks'], cite) + '</section>' for section in access)
