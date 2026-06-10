# Prof. Mohammad Mansoob Khan — Website v2 (redesigned)

A polished, fully self-contained academic site. **Every icon is real and embedded inside the HTML** (official ORCID, Google Scholar, Scopus, ResearchGate and Web of Science brand glyphs as inline SVG), and the **photo + all book covers are embedded as data URIs** — so there are *no separate icon/image files that can ever 404*. The only external file is `assets/img/MMK.png` (used for the social-share preview and favicon), and it's already on your server.

## Files
```
index.html       Home — hero, live metrics band, about, highlights, affiliations
research.html    Research areas, signature themes, grants
Papers.html      Profile cards (real logos) + LIVE latest publications + most-cited + recent
Books.html       Six books with embedded covers + DOIs
Awards.html      Honours, recent keynotes, editorial & community service
404.html         Friendly redirect page
sitemap.xml, robots.txt, .nojekyll
assets/img/MMK.png   (social-preview + favicon only)
```

## What's better than v1
- Real, accurate brand logos (no more letter-badges or broken images) — embedded inline, impossible to break.
- Refined editorial design: serif display headings, navy/teal/gold palette, asymmetric hero, metric band.
- More content: dedicated Research page, richer About, most-cited papers, keynotes, service.
- Live cross-check of citations/h-index via OpenAlex; live auto-updating "Latest publications" feed.
- Mobile-tested, console-clean on every page, full SEO + schema.org Person JSON-LD.

## Deploy (replace what's on GitHub)
1. On your repo, **Add file → Upload files**.
2. Unzip this folder and drag in **everything inside it** (the 5 HTML files, `404.html`, `sitemap.xml`, `robots.txt`, `.nojekyll`, and the `assets` folder). Same filenames overwrite the old ones; `research.html` is new.
3. **Commit changes** → wait ~1 min → open the site and press **Ctrl+F5**.

Because the icons and images are baked into the HTML, even if a drag-and-drop misses a file, the pages still render perfectly. The only file that matters is `assets/img/MMK.png`, which is already live.

## After deploying
- Google Search Console → submit `sitemap.xml`, request indexing (makes him findable worldwide).
- Add the site URL to his Google Scholar, ORCID, ResearchGate, LinkedIn and UBD profiles.

Metrics shown: Google Scholar (10 Jun 2026) — 19,723 citations, h-index 71, i10-index 181 — with a live OpenAlex cross-check that updates on every visit.
