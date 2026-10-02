"""Shared presentation for linked researcher identifiers."""
from html import escape


def orcid_link(identifier, name, new_tab=False):
    label = escape(f"View {name}’s ORCID record", quote=True)
    target = ' target="_blank" rel="noopener noreferrer"' if new_tab else ''
    return (f'<a class="orcid-link" href="https://orcid.org/{escape(identifier, quote=True)}"'
            f' aria-label="{label}" title="{label}"{target}>'
            '<img src="/assets/brand/orcid-id.svg" alt="ORCID iD" width="24" height="24"></a>')
