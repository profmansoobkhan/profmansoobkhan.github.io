#!/usr/bin/env python3
"""Daily data refresh for profmansoobkhan.github.io.

Runs in GitHub Actions (see .github/workflows/update-data.yml) and writes:

  data/metrics.json       headline numbers + citations per year
  data/publications.json  full publication list with per-paper citation counts
  data/history.json       one point per day, for the growth trend

It also rewrites the numbers baked into the HTML (elements carrying a
data-live="..." attribute, and the meta descriptions) so that search engines,
link previews and visitors without JavaScript see current figures.

Sources
  OpenAlex (author record, per-paper citation counts)  - no key needed
  ORCID public API (the curated list of works)         - no key needed
  Google Scholar                                       - best effort, see below

Google Scholar has no API and blocks automated requests. The script tries, in
order: (1) SerpApi, if a SERPAPI_KEY secret is set; (2) a direct request, which
Google usually refuses from cloud servers; (3) data/scholar_manual.json, a file
you can edit by hand. If all fail, the last known Scholar figures are kept and
shown with their own date.

Python standard library only. Usage:  python3 scripts/update_data.py
"""
import concurrent.futures as cf
import datetime as dt
import html
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

ORCID = "0000-0002-8633-7493"
SCHOLAR_ID = "ynzk598AAAAJ"
CONTACT = "mansoob.khan@ubd.edu.bn"
UA = "profmansoobkhan.github.io updater (mailto:%s)" % CONTACT
BROWSER_UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
OPENALEX_KEY = os.environ.get("OPENALEX_API_KEY", "").strip()
SERPAPI_KEY = os.environ.get("SERPAPI_KEY", "").strip()

# A Scholar snapshot newer than this is used as the headline source.
SCHOLAR_FRESH_DAYS = 14
BOOKS = 6  # authored + edited volumes shown on Books.html


def log(*a):
    print(*a, file=sys.stderr, flush=True)


def get(url, headers=None, tries=3, timeout=30):
    h = {"User-Agent": UA, "Accept": "application/json"}
    h.update(headers or {})
    last = None
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers=h)
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read().decode("utf-8", "replace")
        except urllib.error.HTTPError as e:
            last = e
            if e.code in (400, 401, 403, 404):
                break
        except Exception as e:  # network hiccup: retry
            last = e
        time.sleep(1.5 * (i + 1))
    raise RuntimeError("GET failed: %s (%s)" % (url.split("?")[0], last))


def get_json(url, **kw):
    return json.loads(get(url, **kw))


def load(name, default):
    try:
        with open(os.path.join(DATA, name), encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def save(name, obj):
    os.makedirs(DATA, exist_ok=True)
    with open(os.path.join(DATA, name), "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)
        f.write("\n")


def oa_url(path, **params):
    if OPENALEX_KEY:
        params["api_key"] = OPENALEX_KEY
    params.setdefault("mailto", CONTACT)
    return "https://api.openalex.org/" + path + "?" + urllib.parse.urlencode(params)


# ---------------------------------------------------------------- OpenAlex ---
def fetch_openalex_author():
    a = get_json(oa_url("authors/orcid:" + ORCID))
    s = a.get("summary_stats") or {}
    by_year = [
        {"year": c["year"], "citations": c["cited_by_count"], "works": c["works_count"]}
        for c in a.get("counts_by_year", [])
        if c.get("cited_by_count")
    ]
    by_year.sort(key=lambda c: c["year"])
    return {
        "citations": int(a["cited_by_count"]),
        "h_index": int(s["h_index"]),
        "i10_index": int(s["i10_index"]),
        "indexed_works": int(a["works_count"]),
        "by_year": by_year,
        "as_of": (a.get("updated_date") or "")[:10],
        "url": a.get("id"),
    }


def fetch_openalex_work(doi):
    try:
        w = get_json(oa_url(
            "works/doi:" + urllib.parse.quote(doi, safe="/"),
            select="id,cited_by_count,publication_year,authorships,open_access,primary_location"), tries=2)
    except Exception:
        return None
    authors = [(x.get("author") or {}).get("display_name") or x.get("raw_author_name")
               for x in w.get("authorships", [])]
    src = ((w.get("primary_location") or {}).get("source") or {})
    return {
        "citations": int(w.get("cited_by_count") or 0),
        "authors": [re.sub(r"^(Prof\.?|Dr\.?|Professor)(\s+(Prof\.?|Dr\.?))*\s+", "", x) for x in authors if x],
        "year": w.get("publication_year"),
        "oa": bool((w.get("open_access") or {}).get("is_oa")),
        "venue": src.get("display_name"),
    }


# ------------------------------------------------------------------- ORCID ---
TYPE_LABEL = {
    "journal-article": "Journal article", "book-chapter": "Book chapter",
    "book": "Book", "edited-book": "Book",
    "conference-abstract": "Conference", "conference-paper": "Conference",
}


def fetch_orcid_works():
    d = get_json("https://pub.orcid.org/v3.0/%s/works" % ORCID)
    out, seen = [], set()
    for g in d.get("group", []):
        s = g["work-summary"][0]
        title = (((s.get("title") or {}).get("title") or {}).get("value") or "").strip()
        if not title:
            continue
        doi = None
        for e in ((s.get("external-ids") or {}).get("external-id") or []):
            if e.get("external-id-type") == "doi":
                doi = (e.get("external-id-value") or "").strip().lower()
                doi = re.sub(r"^https?://(dx\.)?doi\.org/", "", doi)
                break
        key = doi or re.sub(r"\W+", "", title.lower())
        if key in seen:
            continue
        seen.add(key)
        pd = s.get("publication-date") or {}
        year = int(pd["year"]["value"]) if pd.get("year") else None
        month = int(pd["month"]["value"]) if pd.get("month") else None
        out.append({
            "title": html.unescape(re.sub(r"<[^>]+>", "", title)),
            "year": year, "month": month,
            "venue": ((s.get("journal-title") or {}).get("value") or "").strip() or None,
            "type": TYPE_LABEL.get(s.get("type"), "Other"),
            "doi": doi,
            "url": ("https://doi.org/" + doi) if doi else ((s.get("url") or {}).get("value")),
            "citations": None, "authors": [], "oa": False,
        })
    return out


# ---------------------------------------------------------- Google Scholar ---
def scholar_from_serpapi():
    if not SERPAPI_KEY:
        return None
    q = urllib.parse.urlencode({"engine": "google_scholar_author",
                                "author_id": SCHOLAR_ID, "hl": "en",
                                "api_key": SERPAPI_KEY})
    d = get_json("https://serpapi.com/search.json?" + q, tries=2, timeout=60)
    row = {}
    for item in (d.get("cited_by") or {}).get("table", []):
        for k, v in item.items():
            row[k] = v.get("all")
    by_year = [{"year": int(g["year"]), "citations": int(g["citations"])}
               for g in (d.get("cited_by") or {}).get("graph", [])]
    return {"citations": int(row["citations"]), "h_index": int(row["h_index"]),
            "i10_index": int(row["i10_index"]), "by_year": by_year, "via": "SerpApi"}


def scholar_direct():
    page = get("https://scholar.google.com/citations?user=%s&hl=en" % SCHOLAR_ID,
               headers={"User-Agent": BROWSER_UA, "Accept": "text/html"}, tries=1)
    cells = re.findall(r'class="gsc_rsb_std">(\d+)<', page)
    if len(cells) < 6:
        raise RuntimeError("Scholar page had no metrics table (blocked)")
    years = re.findall(r'class="gsc_g_t"[^>]*>(\d{4})<', page)
    vals = re.findall(r'class="gsc_g_al">(\d+)<', page)
    by_year = ([{"year": int(y), "citations": int(v)} for y, v in zip(years, vals)]
               if len(years) == len(vals) else [])
    return {"citations": int(cells[0]), "h_index": int(cells[2]),
            "i10_index": int(cells[4]), "by_year": by_year, "via": "Google Scholar"}


def scholar_manual():
    m = load("scholar_manual.json", None)
    if not m or not m.get("as_of"):
        return None
    return {"citations": int(m["citations"]), "h_index": int(m["h_index"]),
            "i10_index": int(m["i10_index"]), "by_year": [], "via": "manual entry",
            "as_of": m["as_of"]}


def fetch_scholar(today, previous):
    """Return the freshest Scholar figures we can get; fall back to the last known."""
    for name, fn in (("SerpApi", scholar_from_serpapi), ("direct", scholar_direct)):
        try:
            s = fn()
            if s:
                s["as_of"] = today
                log("Scholar via %s: %s" % (name, s["citations"]))
                return s
        except Exception as e:
            log("Scholar via %s unavailable: %s" % (name, e))
    manual = None
    try:
        manual = scholar_manual()
    except Exception as e:
        log("scholar_manual.json ignored: %s" % e)
    best = previous
    if manual and (not previous or manual["as_of"] > previous.get("as_of", "")):
        best = manual
    return best


# ------------------------------------------------------------------ guards ---
def plausible(new, old, label):
    """Refuse an obviously broken reading (e.g. a merged or emptied profile)."""
    if not old:
        return True
    if new["citations"] < 0.5 * old["citations"] or new["h_index"] < 0.5 * old["h_index"]:
        log("WARNING: %s reading rejected as implausible: %s vs previous %s"
            % (label, new["citations"], old["citations"]))
        return False
    return True


def days_between(a, b):
    try:
        return (dt.date.fromisoformat(b) - dt.date.fromisoformat(a)).days
    except Exception:
        return 10 ** 6


# ------------------------------------------------------------ bake to HTML ---
def bake_html(m):
    p = m["primary"]
    values = {
        "publications": "{:,}".format(m["publications"]),
        "citations": "{:,}".format(p["citations"]),
        "h_index": str(p["h_index"]),
        "i10_index": str(p["i10_index"]),
    }
    for name in os.listdir(ROOT):
        if not name.endswith(".html"):
            continue
        path = os.path.join(ROOT, name)
        with open(path, encoding="utf-8") as f:
            src = f.read()
        new = src
        for key, val in values.items():
            new = re.sub(r'(data-live="%s"[^>]*>)[^<]*(<)' % key,
                         lambda mo, v=val: mo.group(1) + v + mo.group(2), new)
        new = re.sub(r'[\d,]+ citations, h-index \d+',
                     "%s citations, h-index %s" % (values["citations"], values["h_index"]), new)
        if new != src:
            with open(path, "w", encoding="utf-8") as f:
                f.write(new)
            log("updated numbers in", name)


# -------------------------------------------------------------------- main ---
def main():
    today = dt.datetime.now(dt.timezone.utc).date().isoformat()
    prev = load("metrics.json", {})
    prev_pubs = {p.get("doi") or p["title"]: p
                 for p in load("publications.json", {}).get("items", [])}

    # 1. OpenAlex headline figures (required; keep previous on failure)
    try:
        oa = fetch_openalex_author()
        if not plausible(oa, prev.get("openalex"), "OpenAlex"):
            oa = prev["openalex"]
    except Exception as e:
        log("OpenAlex author fetch failed:", e)
        oa = prev.get("openalex")
        if not oa:
            raise

    # 2. Google Scholar (best effort)
    scholar = fetch_scholar(today, prev.get("scholar"))
    if scholar and prev.get("scholar") and not plausible(scholar, prev["scholar"], "Scholar"):
        scholar = prev["scholar"]

    # 3. Publication list: ORCID, enriched with OpenAlex citation counts
    try:
        works = fetch_orcid_works()
    except Exception as e:
        log("ORCID fetch failed:", e)
        works = list(prev_pubs.values())
    with_doi = [w for w in works if w.get("doi")]
    with cf.ThreadPoolExecutor(6) as ex:
        found = list(ex.map(fetch_openalex_work, [w["doi"] for w in with_doi]))
    matched = 0
    for w, r in zip(with_doi, found):
        old = prev_pubs.get(w["doi"]) or {}
        if r:
            matched += 1
            w["citations"], w["authors"], w["oa"] = r["citations"], r["authors"], r["oa"]
            w["venue"] = w["venue"] or r["venue"]
            w["year"] = w["year"] or r["year"]
        else:  # not in OpenAlex today: keep what we knew
            w["citations"] = old.get("citations")
            w["authors"] = old.get("authors", [])
            w["oa"] = old.get("oa", False)
    works.sort(key=lambda w: (-(w["year"] or 0), -(w["month"] or 0), w["title"]))
    log("works: %d (ORCID), %d with DOI, %d matched in OpenAlex"
        % (len(works), len(with_doi), matched))
    if len(works) < 0.5 * len(prev_pubs):
        raise RuntimeError("publication list shrank implausibly; aborting without writing")

    # 4. Choose the headline source
    use_scholar = bool(scholar) and days_between(scholar["as_of"], today) <= SCHOLAR_FRESH_DAYS
    src = scholar if use_scholar else oa
    primary = {"source": "Google Scholar" if use_scholar else "OpenAlex",
               "citations": src["citations"], "h_index": src["h_index"],
               "i10_index": src["i10_index"],
               "as_of": scholar["as_of"] if use_scholar else today}

    by_type = {}
    for w in works:
        by_type[w["type"]] = by_type.get(w["type"], 0) + 1

    metrics = {
        "updated": today,
        "updated_utc": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%MZ"),
        "primary": primary,
        "publications": len(works),
        "publications_by_type": by_type,
        "books": BOOKS,
        "openalex": dict(oa, checked=today),
        "scholar": scholar,
        "by_year": (scholar.get("by_year") if use_scholar and scholar.get("by_year")
                    else oa["by_year"]),
        "by_year_source": ("Google Scholar" if use_scholar and scholar.get("by_year")
                           else "OpenAlex"),
    }
    save("metrics.json", metrics)
    save("publications.json", {"updated": today, "count": len(works),
                               "citation_source": "OpenAlex", "items": works})

    # 5. History: one point per day
    hist = load("history.json", {"points": []})
    pts = [p for p in hist["points"] if p["date"] != today]
    pts.append({
        "date": today,
        "publications": len(works),
        "openalex": {k: oa[k] for k in ("citations", "h_index", "i10_index")},
        "scholar": ({k: scholar[k] for k in ("citations", "h_index", "i10_index")}
                    if scholar and scholar["as_of"] == today else None),
    })
    pts.sort(key=lambda p: p["date"])
    save("history.json", {"points": pts})

    bake_html(metrics)
    log("done: %s | %s citations, h-index %s, i10 %s (%s) | %d publications"
        % (today, primary["citations"], primary["h_index"], primary["i10_index"],
           primary["source"], len(works)))


if __name__ == "__main__":
    main()
