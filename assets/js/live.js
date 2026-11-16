/* Live data layer. Reads the JSON files that the daily GitHub Action refreshes
   (data/metrics.json, data/history.json, data/publications.json) and fills in
   the metric band, the citations chart, the growth strip and the publication
   browser. No dependencies. If a file is missing the static HTML stays as is. */
(function () {
  "use strict";
  var fmt = function (n) { return Number(n).toLocaleString("en-US"); };
  var $ = function (s, r) { return (r || document).querySelector(s); };
  var esc = function (s) {
    return String(s == null ? "" : s).replace(/[&<>"]/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c];
    });
  };
  var MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
  var nice = function (iso) {
    var p = String(iso || "").split("-");
    return p.length < 3 ? iso : Number(p[2]) + " " + MONTHS[Number(p[1]) - 1] + " " + p[0];
  };
  var daysAgo = function (iso) {
    return Math.floor((Date.now() - new Date(iso + "T00:00:00Z").getTime()) / 864e5);
  };
  var getJSON = function (url) {
    return fetch(url, { cache: "no-cache" }).then(function (r) {
      if (!r.ok) throw new Error(url + " " + r.status);
      return r.json();
    });
  };
  var setLive = function (key, text) {
    document.querySelectorAll('[data-live="' + key + '"]').forEach(function (el) { el.textContent = text; });
  };

  /* ------------------------------------------------------- metric band --- */
  function renderBand(m) {
    var p = m.primary;
    setLive("publications", fmt(m.publications));
    setLive("citations", fmt(p.citations));
    setLive("h_index", p.h_index);
    setLive("i10_index", p.i10_index);

    // the other source, shown small under each number
    var other = p.source === "Google Scholar" ? m.openalex : m.scholar;
    var otherName = p.source === "Google Scholar" ? "OpenAlex" : "Google Scholar";
    if (other) {
      setLive("citations_alt", otherName + ": " + fmt(other.citations));
      setLive("h_index_alt", otherName + ": " + other.h_index);
      setLive("i10_index_alt", otherName + ": " + other.i10_index);
    }
    var t = m.publications_by_type || {};
    if (t["Journal article"]) setLive("publications_alt", fmt(t["Journal article"]) + " journal articles");

    var note = $("#livenote");
    if (note) {
      var age = daysAgo(m.updated);
      var html = '<span class="livedot on"></span>Updated automatically every day. Last refresh: <strong>' +
        esc(nice(m.updated)) + "</strong>. Headline figures from " + esc(p.source) +
        "; publication count from ORCID.";
      if (other) {
        html += " " + otherName + " " + (otherName === "Google Scholar" ? "reading of " + esc(nice(other.as_of)) : "today") +
          " is shown beneath each figure. The databases index different sources, so their totals differ.";
      }
      note.innerHTML = html;
      if (age > 3) note.parentNode.classList.add("stale");
    }
  }

  /* -------------------------------------------------- citations chart --- */
  function renderChart(m) {
    var box = $("#cite-chart");
    if (!box || !m.by_year || !m.by_year.length) return;
    var d = m.by_year, thisYear = Number(m.updated.slice(0, 4));
    var W = 720, H = 300, L = 44, R = 8, T = 22, B = 30;
    var max = Math.max.apply(null, d.map(function (x) { return x.citations; }));
    var step = max > 4000 ? 1000 : max > 1600 ? 500 : max > 800 ? 250 : max > 300 ? 100 : 50;
    var top = Math.ceil(max / step) * step;
    var pw = W - L - R, ph = H - T - B, slot = pw / d.length, bw = Math.min(34, slot - 6);
    var y = function (v) { return T + ph - (v / top) * ph; };
    var peak = d.reduce(function (a, b) { return b.citations > a.citations ? b : a; });
    var s = '<svg viewBox="0 0 ' + W + " " + H + '" role="img" aria-label="Bar chart of citations received per year, ' +
      d[0].year + " to " + d[d.length - 1].year + '. Peak ' + fmt(peak.citations) + " in " + peak.year + '.">' +
      '<defs><pattern id="mmk-hatch" width="6" height="6" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">' +
      '<rect width="6" height="6" fill="#0e7c66" opacity=".28"/><rect width="3" height="6" fill="#0e7c66"/></pattern></defs>';
    for (var g = 0; g <= top; g += step) {
      s += '<line class="' + (g ? "grid" : "base") + '" x1="' + L + '" x2="' + (W - R) + '" y1="' + y(g) + '" y2="' + y(g) + '"/>' +
        '<text x="' + (L - 8) + '" y="' + (y(g) + 4) + '" text-anchor="end">' + fmt(g) + "</text>";
    }
    var everyOther = slot < 34;
    d.forEach(function (x, i) {
      var cx = L + slot * i + slot / 2, by = y(x.citations), h = T + ph - by, r = Math.min(4, h, bw / 2);
      var partial = x.year >= thisYear;
      var path = "M" + (cx - bw / 2) + "," + (T + ph) + "V" + (by + r) + "q0," + -r + " " + r + "," + -r +
        "h" + (bw - 2 * r) + "q" + r + ",0 " + r + "," + r + "V" + (T + ph) + "z";
      s += '<g class="col" tabindex="0" data-y="' + x.year + '" data-c="' + x.citations + '" data-p="' + (partial ? 1 : 0) +
        '" data-x="' + cx + '" data-top="' + by + '">' +
        '<path class="bar' + (partial ? " partial" : "") + '" d="' + path + '"/>' +
        '<rect class="hit" x="' + (cx - slot / 2) + '" y="' + T + '" width="' + slot + '" height="' + ph + '"/></g>';
      if (!everyOther || (d.length - 1 - i) % 2 === 0) {
        s += '<text x="' + cx + '" y="' + (H - 10) + '" text-anchor="middle">' + x.year + "</text>";
      }
      if (x === peak) s += '<text class="val" x="' + cx + '" y="' + (by - 6) + '" text-anchor="middle">' + fmt(x.citations) + "</text>";
    });
    s += "</svg>";
    var rows = d.map(function (x) {
      return "<tr><td>" + x.year + (x.year >= thisYear ? " (to date)" : "") + "</td><td>" + fmt(x.citations) + "</td></tr>";
    }).join("");
    box.innerHTML = '<div class="chartbox">' + s + '<div class="tip" role="status"></div></div>' +
      '<p class="chartnote">Hatched bar: ' + thisYear + " so far (year in progress). Source: " + esc(m.by_year_source) +
      ", refreshed " + esc(nice(m.updated)) + ".</p>" +
      '<details class="tableview"><summary>View as table</summary><table><thead><tr><th>Year</th><th>Citations</th></tr></thead><tbody>' +
      rows + "</tbody></table></details>";
    var tip = $(".tip", box), svg = $("svg", box);
    var show = function (g) {
      var k = svg.getBoundingClientRect().width / W;
      tip.innerHTML = "<b>" + fmt(g.dataset.c) + "</b> citations<br>" + g.dataset.y + (g.dataset.p === "1" ? " (to date)" : "");
      tip.style.left = Math.max(60, Math.min(svg.getBoundingClientRect().width - 60, g.dataset.x * k)) + "px";
      tip.style.top = (g.dataset.top * k - 8) + "px";
      tip.classList.add("show");
    };
    box.querySelectorAll(".col").forEach(function (g) {
      g.addEventListener("mouseenter", function () { show(g); });
      g.addEventListener("focus", function () { show(g); });
      g.addEventListener("mouseleave", function () { tip.classList.remove("show"); });
      g.addEventListener("blur", function () { tip.classList.remove("show"); });
    });
  }

  /* ----------------------------------------------------- growth strip --- */
  function renderGrowth(m, hist) {
    var box = $("#growth");
    if (!box) return;
    var key = m.primary.source === "Google Scholar" ? "scholar" : "openalex";
    var pts = (hist.points || []).filter(function (p) { return p[key]; });
    var last = pts[pts.length - 1];
    var cells = [];
    var since = function (days) {
      if (!last) return null;
      var cut = new Date(new Date(last.date + "T00:00:00Z").getTime() - days * 864e5).toISOString().slice(0, 10);
      var base = null;
      pts.forEach(function (p) { if (p.date <= cut) base = p; });
      return base;
    };
    var b30 = since(30), first = pts[0];
    var ref = b30 || (first && first !== last ? first : null);
    if (ref) {
      var dc = last[key].citations - ref[key].citations;
      cells.push("<b>" + (dc >= 0 ? "+" : "") + fmt(dc) + "</b><span>citations since " + esc(nice(ref.date)) + "</span>");
      var dp = last.publications - ref.publications;
      cells.push("<b>" + (dp >= 0 ? "+" : "") + fmt(dp) + "</b><span>publications since " + esc(nice(ref.date)) + "</span>");
    } else {
      var by = m.by_year || [], y = by[by.length - 1];
      if (y) cells.push("<b>" + fmt(y.citations) + "</b><span>citations received in " + y.year + " so far</span>");
      cells.push("<b>" + fmt(m.publications) + "</b><span>works on the ORCID record</span>");
    }
    cells.push("<b>" + (pts.length || 1) + "</b><span>daily reading" + (pts.length === 1 ? "" : "s") +
      " recorded since " + esc(nice(first ? first.date : m.updated)) + "</span>");
    box.innerHTML = cells.map(function (c) { return '<div class="g">' + c + "</div>"; }).join("");
  }

  /* ----------------------------------------------- publication browser --- */
  function authorLine(a) {
    if (!a || !a.length) return "";
    var names = a.length > 8 ? a.slice(0, 7).concat(["… " + a[a.length - 1]]) : a;
    return names.map(function (n) {
      var e = esc(n);
      return /Mansoob Khan/i.test(n) ? "<strong>" + e + "</strong>" : e;
    }).join(", ");
  }
  function pubItem(w) {
    var meta = '<span class="tag">' + esc(w.type) + "</span>";
    if (w.oa) meta += '<span class="tag oa">Open access</span>';
    if (w.citations) meta += '<span class="cit">Cited by ' + fmt(w.citations) + "</span>";
    if (w.url) meta += '<span class="doi"><a href="' + esc(w.url) + '" target="_blank" rel="noopener">' +
      esc(w.doi ? "doi.org/" + w.doi : "Link") + "</a></span>";
    return "<li><strong>" + esc(w.title) + "</strong>" +
      (w.authors && w.authors.length ? '<span class="authors">' + authorLine(w.authors) + "</span>" : "") +
      '<span class="venue">' + (w.venue ? esc(w.venue) + ", " : "") + esc(w.year || "") + "</span>" +
      '<div class="meta">' + meta + "</div></li>";
  }
  function renderPubs(data) {
    var root = $("#pubbrowser");
    if (!root) return;
    var items = data.items || [], PAGE = 25, shown = PAGE;
    var years = [], types = [];
    items.forEach(function (w) {
      if (w.year && years.indexOf(w.year) < 0) years.push(w.year);
      if (types.indexOf(w.type) < 0) types.push(w.type);
    });
    years.sort(function (a, b) { return b - a; });
    root.innerHTML =
      '<div class="pubtools">' +
      '<label class="srconly" for="pq">Search publications</label>' +
      '<input type="search" id="pq" placeholder="Search title, author or journal" autocomplete="off">' +
      '<label class="srconly" for="py">Year</label><select id="py"><option value="">All years</option>' +
      years.map(function (y) { return "<option>" + y + "</option>"; }).join("") + "</select>" +
      '<label class="srconly" for="pt">Type</label><select id="pt"><option value="">All types</option>' +
      types.map(function (t) { return "<option>" + esc(t) + "</option>"; }).join("") + "</select>" +
      '<label class="srconly" for="ps">Sort</label><select id="ps"><option value="new">Newest first</option>' +
      '<option value="cited">Most cited</option><option value="old">Oldest first</option></select></div>' +
      '<p class="pubcount" id="pc" aria-live="polite"></p><ul class="pubs" id="pl"></ul>' +
      '<button class="more" id="pm" type="button">Show more</button>';
    var q = $("#pq"), fy = $("#py"), ft = $("#pt"), so = $("#ps"), list = $("#pl"), count = $("#pc"), more = $("#pm");
    var hay = items.map(function (w) {
      return (w.title + " " + (w.venue || "") + " " + (w.authors || []).join(" ")).toLowerCase();
    });
    function draw() {
      var terms = q.value.toLowerCase().split(/\s+/).filter(Boolean);
      var res = items.filter(function (w, i) {
        if (fy.value && String(w.year) !== fy.value) return false;
        if (ft.value && w.type !== ft.value) return false;
        return terms.every(function (t) { return hay[i].indexOf(t) >= 0; });
      });
      if (so.value === "cited") res = res.slice().sort(function (a, b) { return (b.citations || 0) - (a.citations || 0); });
      if (so.value === "old") res = res.slice().reverse();
      list.innerHTML = res.slice(0, shown).map(pubItem).join("");
      count.textContent = res.length
        ? "Showing " + Math.min(shown, res.length) + " of " + fmt(res.length) +
          (res.length === items.length ? " publications" : " matching publications (" + fmt(items.length) + " in total)")
        : "No publications match. Try a shorter search or clear the filters.";
      more.style.display = res.length > shown ? "" : "none";
    }
    [q, fy, ft, so].forEach(function (el) {
      el.addEventListener(el === q ? "input" : "change", function () { shown = PAGE; draw(); });
    });
    more.addEventListener("click", function () { shown += 50; draw(); });
    draw();

    var topBox = $("#topcited");
    if (topBox) {
      topBox.innerHTML = items.slice().sort(function (a, b) { return (b.citations || 0) - (a.citations || 0); })
        .slice(0, 5).map(pubItem).join("");
    }
    var stamp = $("#pubstamp");
    if (stamp) {
      stamp.innerHTML = fmt(items.length) + " works from his <a href=\"https://orcid.org/0000-0002-8633-7493\" target=\"_blank\" rel=\"noopener\">ORCID record</a>, " +
        "with per-paper citation counts from <a href=\"https://openalex.org/\" target=\"_blank\" rel=\"noopener\">OpenAlex</a>. Refreshed automatically every day; last refresh " +
        esc(nice(data.updated)) + ".";
    }
    var wrap = $("#livewrap");
    if (wrap) wrap.style.display = "";
    var fb = $("#pubfallback");
    if (fb) fb.style.display = "none";
  }

  /* ---------------------------------------------------------------- go --- */
  var needMetrics = $("#livenote") || $("#cite-chart") || $("#growth");
  if (needMetrics) {
    getJSON("data/metrics.json").then(function (m) {
      renderBand(m);
      renderChart(m);
      return getJSON("data/history.json").catch(function () { return { points: [] }; })
        .then(function (h) { renderGrowth(m, h); });
    }).catch(function () { /* keep the static figures */ });
  }
  if ($("#pubbrowser")) {
    getJSON("data/publications.json").then(renderPubs).catch(function () { /* keep the static list */ });
  }
})();
