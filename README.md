# Microbial Metallomics

This repository is the source for [microbialmetallomics.com](https://microbialmetallomics.com). The site is an independent field guide to microbial metallomics: how microbes use, store, sense, and compete for metals, and how that connects to the microbiome and disease. It is a plain static site of HTML, CSS, and JavaScript, served by Vercel with clean URLs.

The original source folder was not available. This copy was rebuilt from the live site on 28 Sep 2026. Each page is stored as HTML so clean URLs serve the same paths. The homepage is `index.html`. A path such as `/blog/nickel-gut-microbiome-disease` is the file `blog/nickel-gut-microbiome-disease.html`. The HTML is the bytes the live site returned on that date.

## Add a blog post

Copy an existing page in `blog/` (for example `blog/nickel-gut-microbiome-disease.html`) and edit the copy. Then add the new post in these places:

- `blog.html`, which is the `/blog` page. Copy an existing `post-card` link into the post list and point it at the new path.
- `sitemap.xml`. Copy a blog `<url>` block and set `loc` to `https://microbialmetallomics.com/blog/your-slug`.
- The homepage lists, if the new post should appear there. The homepage does not list every post. It links selected essays in the directory and in the thesis feature. Add a link in those lists only when the new post belongs there.

Also add a matching object to `search-index.json` (the on-site search loads this file), a section in `llms.txt`, and an `<item>` in `blog/rss.xml`, so search, the LLM index, and the feed include the new post.

## Deploy

Pushes to `main` will deploy once this repo is connected to the existing Vercel project. Connect the repo in the Vercel project settings. This repository does not change that project, the domain, or DNS.

`vercel.json` sets `cleanUrls` to true and `trailingSlash` to false. Every response sends `Access-Control-Allow-Origin: *`. Files under `/assets/` use `Cache-Control: public, max-age=31536000, immutable`. Those values match the live responses. Vercel adds the HTTPS redirect and the strict transport security header itself. `https://microbialmetallomics.com` and `https://www.microbialmetallomics.com` both return the site with status 200, so this config does not redirect one host to the other.

## Check the mirror

```bash
node tools/verify-mirror.mjs
```

The script serves this repo locally with the same clean URL rules, fetches every URL in `sitemap.xml` from the local server and from the live site, and fails if any status code or HTML body differs.
