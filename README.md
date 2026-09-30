# Microbial Metallomics

Public website: https://microbialmetallomics.com

Static HTML/CSS/JavaScript, with extensionless routes enabled by vercel.json.
The journal design originates from the Microbial Metallomics Field Guide Sites project.

Article categories include original research, paper reviews, essays, and Critical Commentary.

Article sharing supports X, LinkedIn, email, clipboard copying with an honest
failure fallback, and the native share sheet where supported.

Newsletter signup uses double opt-in through the server-side newsletter API.

The conceptual homepage illustration is AI-generated, not microscopy data.

## Editorial conventions

Use American English (`en-US`) in authored text and metadata. Preserve official
publication titles, organization names, and URLs as published.

Inline source citations use linked superscripts such as `[1]`, numbered in order
of first appearance. Each citation has an ID `cite-N-occurrence` and points to
`ref-N` in the article's ordered reference list. Each reference links back to
every citing passage. Keep citations in static HTML so they work without
JavaScript and appear in print. Source references are separate from the
"Cite this page" export feature.

After editing content, refresh generated search data and feeds and validate links:

```sh
python3 tools/build_catalog.py
python3 tools/refresh_site.py
python3 tools/check_citations.py
```
