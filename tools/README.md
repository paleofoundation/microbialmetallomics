# Site maintenance

The production website serves static pages and a newsletter API through Vercel from this repository. `main` deploys to microbialmetallomics.com.

Run `npm run check` before publishing. This performs whole-site local integrity checks, the numbered-citation checks, and mocked newsletter API tests without sending email. `npm run lint` checks all published HTML for metadata, duplicate IDs and attributes, local links, fragments, assets, accessibility ID references, embedded JSON, JSON files, XML/SVG, and JavaScript syntax. It makes no network requests. It does not replace a browser accessibility review, scientific source review, or checking external links; those need separate verification.

After editing article metadata or adding pages, run:

```sh
python3 tools/build_catalog.py
python3 tools/refresh_site.py
```

The first command updates the 54-page reading catalog, CSV export, RSS feeds, and JSON Feed from published article metadata. Design labels are explicitly maintained in `DESIGNS`; do not infer evidence strength from a topic or publication format. The catalog describes this site’s coverage, not a systematic review dataset.

The second command refreshes shared navigation, asset content hashes, search records, RSS discovery, and the sitemap. Vercel caches `/assets` immutably, so rerun this command after changing CSS, JavaScript, or catalog files.

New article pages also need the existing author, sharing, source-status, reading-list, and citation markup. Keep static catalog fallback cards in evidence.html, library.html, and topics.html in step with newly added articles. Citation downloads refer to the website page; the primary-source DOI is a separate link.

Directory profiles are rendered in people.html; source records and public-contact provenance are in assets/data/people.json. Use only verified public professional contacts and source-credited portraits.

Email signup uses Resend through the same-origin `/api/newsletter` endpoint. Readers must confirm their email before joining the digest. Newsletter editions are prepared and sent manually; see [Newsletter operations](NEWSLETTER.md) for audience selection, unsubscribe links, quotas, and configuration. RSS feeds remain available without signup. Contribution briefs remain local until readers send them through the linked professional contact form.

## Metals atlas

Edit `assets/data/metals.json`, then run `python3 tools/build_metals.py` before `python3 tools/refresh_site.py`. Each prose field contains text and per-profile 1-based source indices; the generator validates them and emits static superscript citations with return links. It builds individual profiles, the searchable hub, and every homepage tile. Group labels are reading pathways rather than exclusive chemical or safety classifications. Verify each new source and keep study setting and limitations explicit.
