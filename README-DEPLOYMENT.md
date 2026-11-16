# Prof. Mohammad Mansoob Khan — website (v3, self-updating)

A static GitHub Pages site whose figures refresh themselves once a day.

## How the daily update works

`.github/workflows/update-data.yml` runs every day at 21:17 UTC (05:17 in Brunei). It runs
`scripts/update_data.py`, which:

1. reads citations, h-index, i10-index and citations-per-year from **OpenAlex**;
2. reads the full list of works from the **ORCID** record, and looks up each paper's citation count in OpenAlex;
3. tries to read **Google Scholar** (see below);
4. writes `data/metrics.json`, `data/publications.json` and appends one point to `data/history.json`;
5. rewrites the numbers inside the HTML so search engines and link previews show current figures;
6. commits the change, which republishes the site.

The pages load those JSON files through `assets/js/live.js`. If a source is down on a given day, the
previous values are kept; nothing is ever blanked.

## One-time setup (after uploading these files)

1. **Settings → Actions → General → Workflow permissions → "Read and write permissions" → Save.**
2. **Actions tab → "Update research metrics" → Run workflow** to do the first run by hand.
   After that it runs by itself every day.

## Google Scholar

Google Scholar has no API and refuses automated requests from cloud servers, so by default the big
numbers come from OpenAlex and the last Scholar reading is shown beneath them with its date.
Two ways to keep the Scholar figures current:

- **Automatic (recommended):** create a free account at serpapi.com (250 searches a month; this uses
  about 30), then add the key under **Settings → Secrets and variables → Actions → New repository
  secret**, named `SERPAPI_KEY`. Once a Scholar reading is less than 14 days old it becomes the
  headline source automatically.
- **Manual:** edit `data/scholar_manual.json` (three numbers and a date) whenever you like.

## Files

```
index.html, research.html, Papers.html, Books.html, Awards.html, 404.html
assets/js/live.js, assets/css/live.css      live-data layer
data/metrics.json                           headline figures (written by the Action)
data/publications.json                      all works + citation counts (written by the Action)
data/history.json                           one reading per day (written by the Action)
data/scholar_manual.json                    optional manual Scholar figures (edited by you)
scripts/update_data.py                      the updater (Python standard library only)
.github/workflows/update-data.yml           the daily schedule
```

To correct the publication list, edit the ORCID record; the site follows it the next day.
