"""Shared presentation for linked researcher identifiers."""
from html import escape
import json
from pathlib import Path


def site_author(slug):
    people = json.loads((Path(__file__).resolve().parents[1] / 'assets/data/people.json').read_text())
    return next(person for person in people if person['slug'] == slug and person.get('siteAuthor'))


def author_schema(person):
    url = 'https://microbialmetallomics.com/people/' + person['slug']
    return {'@type': 'Person', '@id': url + '#person', 'name': person['name'], 'url': url}


def author_byline(person):
    link = ('<a href="/people/' + escape(person['slug'], quote=True) + '" rel="author">'
            + escape(person['name']) + '</a>')
    return link + (' ' + orcid_link(person['orcid'], person['name']) if person.get('orcid') else '')


def orcid_link(identifier, name, new_tab=False):
    label = escape(f"View {name}’s ORCID record", quote=True)
    target = ' target="_blank" rel="noopener noreferrer"' if new_tab else ''
    return (f'<a class="orcid-link" href="https://orcid.org/{escape(identifier, quote=True)}"'
            f' aria-label="{label}" title="{label}"{target}>'
            '<img src="/assets/brand/orcid-id.svg" alt="ORCID iD" width="24" height="24"></a>')
