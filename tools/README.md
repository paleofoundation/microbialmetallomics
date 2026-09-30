# Site maintenance

The production website is a static Vercel deployment of this repository. `main` deploys to microbialmetallomics.com.

After editing article metadata or adding pages, run:

```sh
python3 tools/build_catalog.py
python3 tools/refresh_site.py
```

The first command updates the 54-page reading catalogue, CSV export, RSS feeds, and JSON Feed from published article metadata. Design labels are explicitly maintained in `DESIGNS`; do not infer evidence strength from a topic or publication format. The catalogue describes this site’s coverage, not a systematic review dataset.

The second command refreshes shared navigation, asset content hashes, search records, RSS discovery, and the sitemap. Vercel caches `/assets` immutably, so rerun this command after changing CSS, JavaScript, or catalogue files.

New article pages also need the existing author, sharing, source-status, reading-list, and citation markup. Keep static catalogue fallback cards in evidence.html, library.html, and topics.html in step with newly added articles. Citation downloads refer to the website page; the primary-source DOI is a separate link.

Directory profiles are rendered in people.html; source records and public-contact provenance are in assets/data/people.json. Use only verified public professional contacts and source-credited portraits.

Email subscriptions are not connected. newsletter.html links to working feeds and says so explicitly. Connect a real mailing provider with confirmation and unsubscribe support before adding a signup form or success message. Contribution briefs remain local until readers send them through the linked professional contact form.
