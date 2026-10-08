"""Locate complete HTML elements without rewriting their text or attributes.

The publishing passes use source offsets so moving a block preserves citations,
links, and author-maintained markup byte for byte. No third-party parser needed.
"""
from dataclasses import dataclass, field
from html.parser import HTMLParser

VOID = {'area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input', 'link',
        'meta', 'param', 'source', 'track', 'wbr'}


@dataclass
class Block:
    tag: str
    attrs: dict
    start: int
    inner: int
    close: int = 0
    end: int = 0
    parent: object = None
    children: list = field(default_factory=list)

    def has(self, name):
        return name in self.attrs.get('class', '').split()

    def within(self, parent):
        return parent.start < self.start and self.end <= parent.end


class Blocks(HTMLParser):
    def __init__(self, source):
        super().__init__(convert_charrefs=False)
        self.source = source
        self.offsets = [0]
        for line in source.splitlines(keepends=True):
            self.offsets.append(self.offsets[-1] + len(line))
        self.nodes = []
        self.stack = []
        self.feed(source)

    def position(self):
        line, col = self.getpos()
        return self.offsets[line - 1] + col

    def handle_starttag(self, tag, attrs):
        start = self.position()
        node = Block(tag, dict(attrs), start, start + len(self.get_starttag_text()),
                     parent=self.stack[-1] if self.stack else None)
        if node.parent:
            node.parent.children.append(node)
        self.nodes.append(node)
        if tag in VOID:
            node.close = node.end = node.inner
        else:
            self.stack.append(node)

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in VOID:
            node = self.stack.pop()
            node.close = node.end = node.inner

    def handle_endtag(self, tag):
        for index in range(len(self.stack) - 1, -1, -1):
            if self.stack[index].tag == tag:
                node = self.stack[index]
                node.close = self.position()
                node.end = self.source.index('>', node.close) + 1
                self.stack = self.stack[:index]
                return

    def find(self, *, tag=None, cls=None, id=None, attr=None, within=None):
        return [n for n in self.nodes if n.end and
                (tag is None or n.tag == tag) and
                (cls is None or n.has(cls)) and
                (id is None or n.attrs.get('id') == id) and
                (attr is None or attr in n.attrs) and
                (within is None or n.within(within))]

    def one(self, **kwargs):
        return next(iter(self.find(**kwargs)), None)

    def raw(self, node):
        return self.source[node.start:node.end]

    def content(self, node):
        return self.source[node.inner:node.close]


def edit(source, changes):
    """Apply nonoverlapping (start, end, replacement) edits from right to left."""
    last = len(source) + 1
    for start, end, replacement in sorted(changes, reverse=True):
        if end > last:
            raise ValueError('Overlapping HTML edits')
        source = source[:start] + replacement + source[end:]
        last = start
    return source
