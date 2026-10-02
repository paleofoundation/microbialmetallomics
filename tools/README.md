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

Researcher profiles are generated from `assets/data/people.json`; the directory argument and exposure context are in `assets/data/people-context.json`. Run `python3 tools/build_people.py`, then `python3 tools/refresh_site.py`, then `npm run check`. Each profile must explain a concrete contribution, its significance, the next scientific question, and its evidence. Preserve established directory anchors, existing biographies, public-contact provenance, and source-credited portraits. Significance and future directions are editorial synthesis; distinguish them from established study findings. Do not add visible review-date labels.

Email signup uses Resend through the same-origin `/api/newsletter` endpoint. Readers must confirm their email before joining the digest. Newsletter editions are prepared and sent manually; see [Newsletter operations](NEWSLETTER.md) for audience selection, unsubscribe links, quotas, and configuration. RSS feeds remain available without signup. Contribution briefs remain local until readers send them through the linked professional contact form.

## Metals atlas

Edit `assets/data/metal-access.json` for the organizing thesis and compartment explorer, and `assets/data/metals.json` for element profiles and their optional `access` deep dives. Rebuild in this order:

```sh
python3 tools/build_access.py
python3 tools/build_metals.py
python3 tools/refresh_site.py
npm run check
```

`build_access.py` creates Start here, Follow the metal, and the homepage thesis entry point. `build_metals.py` builds individual profiles, the searchable hub, and every homepage element tile. Optional profile access sections appear after exposure and chemical form, with matching contents links and their own stylesheet. Their text, including tables and claim cards, is included in atlas filtering. `refresh_site.py` runs last to update shared navigation, search records, sitemap entries, and asset hashes across all generated pages. If article metadata also changed, run `build_catalog.py` before this sequence.

Each sourced prose field contains text and per-profile 1-based source indices; the generators validate references and emit static superscript citations with return links. Access blocks share the renderers in `access_render.py`. Preserve stable section IDs and distinguish observations, model-specific causal evidence, and proposed connections. Review dates remain in data and machine-readable metadata; do not add visible review-date labels to these pages. Group labels are reading pathways rather than exclusive chemical or safety classifications. Verify each new source and keep study setting and limitations explicit.

## Pillar essay

Edit `assets/data/pillar-essay.json` for the pillar essay, its primary sources, and its FAQs. Rebuild in this order:

```sh
python3 tools/build_pillar.py
python3 tools/build_catalog.py
python3 tools/refresh_site.py
npm run check
```

The pillar generator keeps article metadata, visible FAQs, structured data, citation exports, and manually maintained discovery copy consistent. Preserve the canonical URL and legacy section aliases. Keep study findings distinct from proposed causal connections. The right sidebar holds a collapsed editorial history; publication and modification dates remain in metadata and citations without a visible review-date strip.

## Scientific editorial method

Mechanistic reasoning is a central output of this guide. Explain what a discovery makes possible, including plausible research directions that have not yet been tested. Follow the chain **observation → mechanism → justified hypothesis → discriminating prediction**. Keep measured findings distinct from editorial inference, attribute each source to the step it actually supports, and state material limits next to the inference they affect.

An untested question, an inconclusive result, and evidence against a hypothesis are different states. Absence of a clinical trial is not a reason to dismiss an otherwise grounded research direction. Conversely, a mechanism alone does not establish a treatment effect. End frontier sections with a useful next question, rather than a generic clinical-validation warning. Preserve actual contrary findings and plausible competing explanations.

Researcher profiles must explain explicitly how each person's work advances the field and what it opens for microbiome medicine, biology, or exposure science. Where enzyme chemistry motivates an argument, distinguish enzyme presence, cofactor identity, activity in the relevant setting, and biological contribution. Do not infer nickel dependence from an enzyme-family name alone. Public standards are at `/editorial#mechanisms-and-hypotheses`; the reading method is at `/evidence-guide#from-mechanism-to-hypothesis`.
