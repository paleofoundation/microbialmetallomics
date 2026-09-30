#!/usr/bin/env python3
"""Check the published static site with Python's standard library and Node.

This is a local integrity check, not a remote link checker or HTML conformance
validator. It makes no network requests and never reads local environment files.
"""

from __future__ import annotations

import argparse
from collections import Counter
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import subprocess
import sys
from urllib.parse import unquote, urljoin, urlsplit
import xml.etree.ElementTree as ET

from check_citations import Document

ORIGIN = "https://microbialmetallomics.com"
HOSTS = {"microbialmetallomics.com", "www.microbialmetallomics.com"}
IGNORED = {"node_modules", "work", "outputs", "__pycache__"}


def public_files(root: Path):
    return sorted(path for path in root.rglob("*") if path.is_file() and not any(
        part.startswith(".") or part in IGNORED for part in path.relative_to(root).parts
    ))


def route(path: Path, root: Path) -> str:
    value = "/" + path.relative_to(root).with_suffix("").as_posix()
    return value[:-5] if value.endswith("index") else value


class DuplicateAttributes(HTMLParser):
    def __init__(self, source: str):
        super().__init__()
        self.errors = []
        self.feed(source)

    def handle_starttag(self, tag, attrs):
        for name, count in Counter(name for name, _ in attrs).items():
            if count > 1:
                self.errors.append((self.getpos()[0], f"Duplicate attribute {name!r} on <{tag}>."))

    handle_startendtag = handle_starttag


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", nargs="?", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--max-details", type=int, default=35)
    args = parser.parse_args()
    root = args.root.resolve()
    files = public_files(root)
    pages = {path: Document(path.read_text(encoding="utf-8")) for path in files if path.suffix == ".html"}
    errors = []
    counts = Counter(pages=len(pages))
    ids = {path: {el.attrs["id"] for el in doc.elements if el.attrs.get("id")} for path, doc in pages.items()}

    def error(path, message, line=1):
        errors.append(f"{path.relative_to(root)}:{line}: {message}")

    def local_target(source, value):
        if not value or value.startswith(("mailto:", "tel:", "data:", "blob:")):
            return None
        parsed = urlsplit(urljoin(ORIGIN + route(source, root), value))
        if parsed.hostname not in HOSTS:
            return None
        target = (root / unquote(parsed.path).lstrip("/")).resolve()
        if not target.is_relative_to(root):
            return None
        options = [target]
        if not target.suffix:
            options.extend([target.with_suffix(".html"), target / "index.html"])
        if parsed.path.startswith("/api/"):
            options.append(target.with_suffix(".js"))
        return next((p for p in options if p.is_file()), None), parsed.fragment

    def check_link(path, value, line=1):
        if value and value.lower().startswith("javascript:"):
            error(path, "JavaScript URL is not allowed.", line)
            return
        try:
            target = local_target(path, value)
        except ValueError as exc:
            error(path, f"Malformed URL {value!r}: {exc}.", line)
            return
        if target is None:
            return
        counts["links"] += 1
        destination, fragment = target
        if destination is None:
            error(path, f"Missing local target: {value!r}.", line)
        elif fragment and destination in pages and not fragment.startswith(":~:text="):
            identifier = unquote(fragment.split(":~:text=", 1)[0])
            if identifier and identifier not in ids[destination]:
                error(path, f"Missing fragment target: {value!r}.", line)

    def check_json_urls(path, value, line=1):
        if isinstance(value, list):
            for item in value:
                check_json_urls(path, item, line)
        elif isinstance(value, dict):
            for key, item in value.items():
                if key in {"url", "href", "src", "image", "contentUrl", "home_page_url", "feed_url", "item"} and isinstance(item, str) and item.startswith(("/", "https://", "http://")):
                    check_link(path, item, line)
                else:
                    check_json_urls(path, item, line)

    for path, doc in pages.items():
        source = path.read_text(encoding="utf-8")
        for line, message in DuplicateAttributes(source).errors:
            error(path, message, line)
        elements = doc.elements
        for name, count in Counter(el.attrs.get("id") for el in elements if el.attrs.get("id")).items():
            if count > 1:
                error(path, f"Duplicate id {name!r} ({count} occurrences).")
        html = [el for el in elements if el.tag == "html"]
        if len(html) != 1 or html[0].attrs.get("lang") != "en-US":
            error(path, "Expected one <html lang='en-US'>.")
        for tag in ("title", "h1", "main"):
            matches = [el for el in elements if el.tag == tag]
            if len(matches) != 1 or (tag != "main" and not matches[0].text().strip()):
                error(path, f"Expected one nonempty <{tag}>.")
        for name in ("description", "viewport"):
            matches = [el for el in elements if el.tag == "meta" and el.attrs.get("name") == name]
            if len(matches) != 1 or not matches[0].attrs.get("content"):
                error(path, f"Expected one nonempty {name} meta tag.")
        canonical = [el.attrs.get("href") for el in elements if el.tag == "link" and el.attrs.get("rel") == "canonical"]
        expected = ORIGIN + route(path, root)
        if canonical != [expected]:
            error(path, f"Canonical should be {expected!r}; found {canonical!r}.")
        if path.name in {"404.html", "reading-list.html"} and not any(el.tag == "meta" and el.attrs.get("name") == "robots" and "noindex" in (el.attrs.get("content") or "") for el in elements):
            error(path, "Error and device-local pages must have noindex robots metadata.")
        for el in elements:
            for attribute in ("href", "src", "poster", "action"):
                if attribute in el.attrs:
                    check_link(path, el.attrs[attribute], el.line)
            if el.attrs.get("srcset") and not el.attrs["srcset"].startswith("data:"):
                for candidate in el.attrs["srcset"].split(","):
                    if candidate.strip():
                        check_link(path, candidate.strip().split()[0], el.line)
            if el.tag == "meta" and (el.attrs.get("name") == "reading-catalogue" or el.attrs.get("property") == "og:image" or el.attrs.get("name") == "twitter:image"):
                check_link(path, el.attrs.get("content"), el.line)
            for attribute in ("aria-labelledby", "aria-describedby", "aria-controls", "for"):
                for identifier in (el.attrs.get(attribute) or "").split():
                    if identifier not in ids[path]:
                        error(path, f"{attribute} points to missing id {identifier!r}.", el.line)
            if el.tag == "img" and "alt" not in el.attrs:
                error(path, "Image is missing its alt attribute.", el.line)
            if el.tag in {"input", "select", "textarea", "button"} and el.attrs.get("type") != "hidden":
                named = bool(el.attrs.get("aria-label") or el.attrs.get("aria-labelledby"))
                named = named or (el.tag == "button" and bool(el.text().strip()))
                named = named or (el.tag == "input" and el.attrs.get("type") in {"submit", "reset", "button"} and bool(el.attrs.get("value")))
                named = named or any(parent.tag == "label" and parent.text().strip() for parent in el.ancestors())
                named = named or any(label.tag == "label" and label.attrs.get("for") == el.attrs.get("id") and el.attrs.get("id") and label.text().strip() for label in elements)
                if not named:
                    error(path, f"<{el.tag}> lacks an accessible name or label.", el.line)
            if el.tag == "script" and el.attrs.get("type") in {"application/ld+json", "application/json"}:
                try:
                    check_json_urls(path, json.loads(el.text()), el.line)
                    counts["embedded_json"] += 1
                except ValueError as exc:
                    error(path, f"Invalid embedded JSON: {exc}.", el.line)
            elif el.tag == "script" and not el.attrs.get("src") and el.text().strip():
                arguments = ["node", "--check"]
                if el.attrs.get("type") == "module":
                    arguments.append("--input-type=module")
                result = subprocess.run(arguments, input=el.text(), capture_output=True, text=True)
                counts["inline_javascript"] += 1
                if result.returncode:
                    error(path, "Inline JavaScript syntax check failed: " + result.stderr.strip(), el.line)

    for path in files:
        if path.suffix == ".json":
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                check_json_urls(path, data)
                counts["json"] += 1
                if path.name == "search-index.json":
                    if not isinstance(data, list):
                        error(path, "Search index must be an array.")
                    else:
                        for item in data:
                            if not isinstance(item, dict) or not all(isinstance(item.get(key), str) for key in ("title", "kind", "url", "desc")):
                                error(path, "Search entry is missing string title, kind, url, or desc.")
            except (ValueError, OSError) as exc:
                error(path, f"Invalid JSON: {exc}.")
        elif path.suffix in {".xml", ".svg"}:
            try:
                document = ET.parse(path)
                counts["xml"] += 1
                if path.name == "sitemap.xml":
                    for el in document.iter():
                        if el.tag.endswith("}loc"):
                            check_link(path, el.text)
            except ET.ParseError as exc:
                error(path, f"Invalid XML: {exc}.")
        elif path.suffix in {".js", ".mjs", ".cjs"}:
            result = subprocess.run(["node", "--check", str(path)], capture_output=True, text=True)
            counts["javascript"] += 1
            if result.returncode:
                error(path, "JavaScript syntax check failed: " + result.stderr.strip())
        elif path.suffix == ".css":
            for match in re.finditer(r"url\(\s*(['\"]?)(.*?)\1\s*\)", path.read_text(encoding="utf-8")):
                check_link(path, match[2])
    if not pages:
        errors.append("No published HTML pages found.")
    print(f"Checked {counts['pages']} HTML pages, {counts['links']} local links/assets, {counts['embedded_json']} embedded JSON blocks, {counts['json']} JSON files, {counts['xml']} XML/SVG files, {counts['javascript']} JavaScript files, and {counts['inline_javascript']} inline scripts.")
    print(f"Errors: {len(errors)}.")
    for message in errors[:args.max_details]:
        print("ERROR " + message)
    if len(errors) > args.max_details:
        print(f"... {len(errors) - args.max_details} additional errors (use --max-details).")
    return int(bool(errors))


if __name__ == "__main__":
    sys.exit(main())
