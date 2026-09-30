#!/usr/bin/env python3
"""Validate static numbered citations and their reference/backlink relationships."""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from html.parser import HTMLParser
from pathlib import Path
import re
import sys


VOID_TAGS = {
    "area", "base", "br", "col", "embed", "hr", "img", "input", "link",
    "meta", "param", "source", "track", "wbr",
}
REFERENCE_ID = re.compile(r"ref-([1-9]\d*)\Z")
CITATION_ID = re.compile(r"cite-([1-9]\d*)-([1-9]\d*)\Z")
YEAR = re.compile(r"\b(?:19|20)\d{2}[a-z]?\b")
EXCLUDED_CLASSES = {
    "reference-list", "citation-box", "citation-panel", "citation",
    "related-module", "person-works",
}


@dataclass(eq=False)
class Element:
    tag: str
    attrs: dict[str, str | None]
    line: int
    parent: Element | None = None
    children: list[Element | str] = field(default_factory=list)

    @property
    def classes(self) -> set[str]:
        return set((self.attrs.get("class") or "").split())

    def ancestors(self):
        node = self.parent
        while node is not None:
            yield node
            node = node.parent

    def descendants(self):
        for child in self.children:
            if isinstance(child, Element):
                yield child
                yield from child.descendants()

    def text(self) -> str:
        return "".join(
            child.text() if isinstance(child, Element) else child
            for child in self.children
        )


class Document(HTMLParser):
    def __init__(self, source: str):
        super().__init__(convert_charrefs=True)
        self.root = Element("document", {}, 1)
        self.stack = [self.root]
        self.elements: list[Element] = []
        self.feed(source)
        self.close()

    def handle_starttag(self, tag, attrs):
        element = Element(tag, dict(attrs), self.getpos()[0], self.stack[-1])
        self.stack[-1].children.append(element)
        self.elements.append(element)
        if tag not in VOID_TAGS:
            self.stack.append(element)

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in VOID_TAGS:
            self.stack.pop()

    def handle_endtag(self, tag):
        for index in range(len(self.stack) - 1, 0, -1):
            if self.stack[index].tag == tag:
                del self.stack[index:]
                break

    def handle_data(self, data):
        self.stack[-1].children.append(data)


def normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def prose_warnings(document: Document, references: list[Element]) -> list[tuple[int, str]]:
    """Report possible leftovers, without treating dates as structural failures."""
    surnames = set()
    for reference in references:
        text = normalize_text(reference.text())
        # Most references start with a surname, optionally followed by initials.
        match = re.match(r"([A-ZÀ-Þ][\w’'-]+)(?:\s+[A-Z]{1,4}\b|,|\s+et al\.)", text)
        if match:
            surnames.add(match[1].casefold())
    warnings = []
    seen = set()
    for element in document.elements:
        if element.tag not in {"p", "li"}:
            continue
        lineage = [element, *element.ancestors()]
        if not any(node.classes & {"article-body", "prose"} for node in lineage):
            continue
        if any(
            node.tag in {"script", "style", "code", "pre"}
            or node.classes & EXCLUDED_CLASSES
            or node.attrs.get("id") in {"references", "sources", "cite-this-page"}
            for node in lineage
        ):
            continue
        text = normalize_text(element.text())
        candidates = []
        for match in re.finditer(r"\([^()]{0,240}\)", text):
            inner = match[0]
            if not YEAR.search(inner):
                continue
            author_cue = re.search(r"\bet al\.|\band colleagues\b|\b[A-ZÀ-Þ][\w’'-]+\s+(?:and|&)\s+[A-ZÀ-Þ]", inner)
            named_author = any(re.search(r"\b" + re.escape(name) + r"\b", inner, re.I) for name in surnames)
            # A year alone is meaningful only beside a clear author attribution.
            before = text[max(0, match.start() - 100):match.start()]
            narrative = re.search(r"\b(?:et al\.|and colleagues|[A-ZÀ-Þ][\w’'-]+(?:\s+(?:and|&)\s+[A-ZÀ-Þ][\w’'-]+)?)\s*$", before)
            if author_cue or named_author or (
                narrative and re.fullmatch(r"\((?:19|20)\d{2}[a-z]?\)", inner)
            ):
                candidates.append(text[max(0, match.start() - 55):min(len(text), match.end() + 35)])
        for candidate in candidates:
            if candidate not in seen:
                warnings.append((element.line, candidate))
                seen.add(candidate)
    return warnings


def check_document(document: Document):
    errors: list[tuple[int, str]] = []

    def error(element: Element, message: str):
        errors.append((element.line, message))

    ids: dict[str, list[Element]] = defaultdict(list)
    for element in document.elements:
        identifier = element.attrs.get("id")
        if identifier:
            ids[identifier].append(element)
        if any(attribute.startswith("data-reference") for attribute in element.attrs):
            error(element, "Interim data-reference attribute remains.")
    for identifier, elements in ids.items():
        if len(elements) > 1:
            error(elements[1], f"Duplicate id {identifier!r} ({len(elements)} occurrences).")

    reference_lists = [element for element in document.elements if "reference-list" in element.classes]
    references: list[Element] = []
    for reference_list in reference_lists:
        if reference_list.tag != "ol":
            error(reference_list, "Reference list must be an ordered list (<ol>).")
        entries = [child for child in reference_list.children if isinstance(child, Element) and child.tag == "li"]
        references.extend(entries)
        try:
            native_number = int(reference_list.attrs.get("start") or "1")
        except ValueError:
            native_number = 1
            error(reference_list, "Reference list start is not an integer.")
        if "reversed" in reference_list.attrs:
            error(reference_list, "Reference list must not use reversed numbering.")
        for expected, entry in enumerate(entries, 1):
            match = REFERENCE_ID.fullmatch(entry.attrs.get("id") or "")
            if not match or int(match[1]) != expected:
                error(entry, f"Expected sequential reference id 'ref-{expected}'.")
            if "value" in entry.attrs:
                try:
                    native_number = int(entry.attrs.get("value") or "")
                except ValueError:
                    error(entry, "Reference list-item value is not an integer.")
            if native_number != expected:
                error(entry, f"Native ordered-list number {native_number} differs from reference {expected}.")
            native_number += 1

    reference_set = set(references)
    citation_links: list[Element] = []
    for superscript in document.elements:
        if superscript.tag != "sup" or "citation" not in superscript.classes:
            continue
        anchors = [element for element in superscript.descendants() if element.tag == "a"]
        if not anchors:
            error(superscript, "Citation superscript contains no link.")
        citation_links.extend(anchors)

    occurrence_numbers: dict[int, list[int]] = defaultdict(list)
    for link in citation_links:
        href = link.attrs.get("href") or ""
        ref_match = REFERENCE_ID.fullmatch(href[1:]) if href.startswith("#") else None
        cite_match = CITATION_ID.fullmatch(link.attrs.get("id") or "")
        if not ref_match:
            error(link, "Citation href must be '#ref-N'.")
            continue
        number = int(ref_match[1])
        if not cite_match or int(cite_match[1]) != number:
            error(link, f"Citation id must be 'cite-{number}-occurrence'.")
        else:
            occurrence_numbers[number].append(int(cite_match[2]))
        if normalize_text(link.text()) != f"[{number}]":
            error(link, f"Citation label must be '[{number}]'.")
        if link.attrs.get("role") != "doc-noteref":
            error(link, "Citation link must have role='doc-noteref'.")
        targets = ids.get(href[1:], [])
        if len(targets) != 1 or targets[0] not in reference_set:
            error(link, f"Citation target {href!r} must resolve to exactly one reference-list <li>.")
            continue
        citation_id = link.attrs.get("id")
        backlinks = [
            item for item in targets[0].descendants()
            if item.tag == "a" and item.attrs.get("href") == f"#{citation_id}"
        ]
        if len(backlinks) != 1:
            error(link, f"Reference {number} must contain exactly one backlink to {citation_id!r}.")

    for number, occurrences in occurrence_numbers.items():
        if occurrences != list(range(1, len(occurrences) + 1)):
            errors.append((1, f"Citation {number} occurrence IDs must run sequentially in document order."))

    citation_set = set(citation_links)
    backlink_count = 0
    for link in document.elements:
        if link.tag != "a":
            continue
        href = link.attrs.get("href") or ""
        is_backlink = href.startswith("#cite-") and href != "#cite-this-page"
        if not is_backlink and link.attrs.get("role") != "doc-backlink":
            continue
        backlink_count += 1
        target_match = CITATION_ID.fullmatch(href[1:]) if href.startswith("#") else None
        targets = ids.get(href[1:], []) if href.startswith("#") else []
        if not target_match or len(targets) != 1 or targets[0] not in citation_set:
            error(link, f"Backlink {href!r} must resolve to exactly one numbered citation.")
            continue
        owner = next((element for element in link.ancestors() if element in reference_set), None)
        expected_owner = f"ref-{target_match[1]}"
        if owner is None or owner.attrs.get("id") != expected_owner:
            error(link, f"Backlink {href!r} must belong to reference {expected_owner!r}.")
        if targets[0].attrs.get("href") != f"#{expected_owner}":
            error(link, f"Backlink {href!r} points to a citation of a different reference.")

    # Also reject citation-like anchors accidentally left outside <sup>.
    for element in document.elements:
        if element.tag == "a" and element.attrs.get("role") == "doc-noteref" and element not in citation_set:
            error(element, "doc-noteref link is outside sup.citation.")
    return errors, prose_warnings(document, references), len(citation_links), len(references), backlink_count


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", nargs="?", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--max-details", type=int, default=12, help="Maximum error/warning examples to print (default: 12).")
    args = parser.parse_args()
    root = args.root.resolve()
    files = sorted(
        path for path in root.rglob("*.html")
        if not any(part.startswith(".") or part == "node_modules" for part in path.relative_to(root).parts)
    )
    errors = []
    warnings = []
    totals = Counter()
    for path in files:
        relative = path.relative_to(root)
        try:
            document = Document(path.read_text(encoding="utf-8"))
            issues, notices, citations, references, backlinks = check_document(document)
        except (OSError, UnicodeError) as exc:
            errors.append(f"{relative}: Cannot read HTML: {exc}")
            continue
        errors.extend(f"{relative}:{line}: {message}" for line, message in issues)
        warnings.extend(f"{relative}:{line}: {message}" for line, message in notices)
        totals.update(citations=citations, references=references, backlinks=backlinks, pages_with_citations=bool(citations))
    print(
        f"Checked {len(files)} HTML pages; {totals['pages_with_citations']} with citations, "
        f"{totals['citations']} citation links, {totals['references']} references, "
        f"{totals['backlinks']} backlinks."
    )
    print(f"Structural errors: {len(errors)}. Possible author-year leftovers: {len(warnings)}.")
    for label, messages in (("ERROR", errors), ("WARNING", warnings)):
        for message in messages[:max(0, args.max_details)]:
            print(f"{label} {message}")
        if len(messages) > max(0, args.max_details):
            print(f"{label} … {len(messages) - max(0, args.max_details)} additional items (use --max-details to show more).")
    if not files:
        print(f"ERROR No HTML files found under {root}.")
        return 1
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
