"""Build report.html (charts, diagrams, links) from county_data.csv.

Usage: python3 build_report.py
Re-run after changing county_data.csv and the report updates itself.
"""
import csv
import html
import json
import os

import score  # reuses MEASURES, GROUPS and rank()

HERE = os.path.dirname(os.path.abspath(__file__))
DOC_URL = "https://docs.google.com/document/d/10kBAO8oS1ExFfkwjbDEZDeizVdjgObwfeow4CkcyShc/edit?usp=drivesdk"

HEAT, VULN, ACCESS = "#e4572e", "#6a4c93", "#1982c4"
GROUP_COLOR = {"Heat": HEAT, "Vulnerability": VULN, "Access gap": ACCESS}

rows = list(csv.DictReader(open(os.path.join(HERE, "county_data.csv"))))
for r in rows:
    for k, v in r.items():
        if k not in ("county", "type", "source_notes"):
            r[k] = float(v) if v.strip() else None

er = json.load(open(os.path.join(HERE, "data", "er_distance_results.json")))
minutes = {c: er[c]["centroid"][1] for c in er}

# ---------- scoring (same method as score.py) ----------
ranks = {}
for m, (_, risky) in score.MEASURES.items():
    vals = {r["county"]: r[m] for r in rows if r[m] is not None}
    ranks[m] = score.rank(vals, risky)

results = []
for r in rows:
    c = r["county"]
    gs = {}
    for g in score.GROUPS:
        rs = [ranks[m][c] for m, (gg, _) in score.MEASURES.items() if gg == g and c in ranks[m]]
        gs[g] = sum(rs) / len(rs)
    results.append({"county": c, "type": r["type"], "groups": gs, "total": sum(gs.values()) / len(gs)})
results.sort(key=lambda x: -x["total"])
by_county = {r["county"]: r for r in rows}
esc = html.escape


# ---------- chart helpers ----------
def bar_chart_heat():
    data = sorted(rows, key=lambda r: -r["days_over_100F"])
    W, rowh, left = 560, 44, 110
    mx = max(r["days_over_100F"] for r in data) * 1.15
    out = [f'<svg viewBox="0 0 {W} {rowh*len(data)+34}" role="img" aria-label="Average days at or above 100F per year">']
    for t in range(0, int(mx) + 1, 5):
        x = left + (W - left - 30) * t / mx
        out.append(f'<line x1="{x:.1f}" y1="0" x2="{x:.1f}" y2="{rowh*len(data)}" stroke="#e6e8ef"/>')
        out.append(f'<text x="{x:.1f}" y="{rowh*len(data)+18}" font-size="11" fill="#8a8fa3" text-anchor="middle">{t}</text>')
    for i, r in enumerate(data):
        y = i * rowh + 8
        w = (W - left - 30) * r["days_over_100F"] / mx
        star = "*" if r["county"] == "Henderson" else ""
        out.append(f'<text x="{left-10}" y="{y+19}" font-size="13" text-anchor="end" fill="#2b2f42">{esc(r["county"])}</text>')
        out.append(f'<rect x="{left}" y="{y}" width="{w:.1f}" height="26" rx="5" fill="{HEAT}" opacity="{1 if r["type"]=="urban" else 0.72}"/>')
        out.append(f'<text x="{left+w+7:.1f}" y="{y+18}" font-size="13" font-weight="600" fill="#2b2f42">{r["days_over_100F"]:.1f}{star}</text>')
    out.append(f'<text x="{left}" y="{rowh*len(data)+32}" font-size="11" fill="#8a8fa3">average days per year at or above 100°F, 2015–2024 (dark = urban)</text>')
    out.append("</svg>")
    return "".join(out)


def bubble_chart():
    W, H, L, B, T, R = 560, 360, 56, 46, 18, 20
    xs = [r["neurologists_per_100k"] for r in rows]
    ys = [minutes[r["county"]] for r in rows]
    xmin, xmax, ymax = -1.2, max(xs) * 1.12, max(ys) * 1.2
    px = lambda v: L + (W - L - R) * (v - xmin) / (xmax - xmin)
    py = lambda v: H - B - (H - B - T) * v / ymax
    out = [f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="Neurologists per 100,000 versus drive time to ER">']
    for t in range(0, int(xmax) + 1, 2):
        out.append(f'<line x1="{px(t):.1f}" y1="{T}" x2="{px(t):.1f}" y2="{H-B}" stroke="#eef0f6"/>')
        out.append(f'<text x="{px(t):.1f}" y="{H-B+16}" font-size="11" fill="#8a8fa3" text-anchor="middle">{t}</text>')
    for t in range(0, int(ymax) + 1, 5):
        out.append(f'<line x1="{L}" y1="{py(t):.1f}" x2="{W-R}" y2="{py(t):.1f}" stroke="#eef0f6"/>')
        out.append(f'<text x="{L-8}" y="{py(t)+4:.1f}" font-size="11" fill="#8a8fa3" text-anchor="end">{t}</text>')
    out.append(f'<text x="{(L+W-R)/2}" y="{H-8}" font-size="12" fill="#5b6075" text-anchor="middle">Neurologists per 100,000 people (more = better access)</text>')
    out.append(f'<text transform="translate(14 {(T+H-B)/2}) rotate(-90)" font-size="12" fill="#5b6075" text-anchor="middle">Drive time to nearest ER (min)</text>')
    # shaded "danger" corner: few neurologists AND long drive
    out.append(f'<rect x="{L}" y="{T}" width="{px(3.2)-L:.1f}" height="{py(8)-T:.1f}" fill="{ACCESS}" opacity="0.07"/>')
    out.append(f'<text x="{L+8}" y="{T+16}" font-size="11" fill="{ACCESS}">low neuro access + long drive</text>')
    for r in rows:
        c = r["county"]
        x, y = px(r["neurologists_per_100k"]), py(minutes[c])
        rad = 6 + r["pct_age_65_plus"] * 0.9
        col = VULN if r["type"] == "urban" else HEAT
        out.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{rad:.1f}" fill="{col}" opacity="0.55" stroke="{col}" stroke-width="1.5"/>')
        dx = 0
        out.append(f'<text x="{x+rad+5:.1f}" y="{y+4:.1f}" font-size="12" fill="#2b2f42">{esc(c)}</text>')
    out.append("</svg>")
    return "".join(out)


def stacked_chart():
    W, rowh, left = 560, 46, 100
    mx = 5.0
    out = [f'<svg viewBox="0 0 {W} {rowh*len(results)+56}" role="img" aria-label="Risk score by county">']
    for t in range(0, 6):
        x = left + (W - left - 50) * t / mx
        out.append(f'<line x1="{x:.1f}" y1="0" x2="{x:.1f}" y2="{rowh*len(results)}" stroke="#e6e8ef"/>')
        out.append(f'<text x="{x:.1f}" y="{rowh*len(results)+16}" font-size="11" fill="#8a8fa3" text-anchor="middle">{t}</text>')
    for i, r in enumerate(results):
        y = i * rowh + 8
        x = left
        out.append(f'<text x="{left-10}" y="{y+19}" font-size="13" text-anchor="end" fill="#2b2f42">{esc(r["county"])}</text>')
        for g in score.GROUPS:
            w = (W - left - 50) * (r["groups"][g] / 3) / mx
            out.append(f'<rect x="{x:.1f}" y="{y}" width="{w:.1f}" height="28" fill="{GROUP_COLOR[g]}"><title>{g}: {r["groups"][g]:.2f}</title></rect>')
            x += w
        out.append(f'<text x="{x+7:.1f}" y="{y+19}" font-size="13" font-weight="700" fill="#2b2f42">{r["total"]:.2f}</text>')
    ly = rowh * len(results) + 40
    lx = left
    for g in score.GROUPS:
        out.append(f'<rect x="{lx}" y="{ly-10}" width="12" height="12" rx="2" fill="{GROUP_COLOR[g]}"/><text x="{lx+18}" y="{ly}" font-size="12" fill="#5b6075">{g}</text>')
        lx += 130
    out.append("</svg>")
    return "".join(out)


def lerp(c1, c2, t):
    a = [int(c1[i:i + 2], 16) for i in (1, 3, 5)]
    b = [int(c2[i:i + 2], 16) for i in (1, 3, 5)]
    return "#" + "".join(f"{round(a[i]+(b[i]-a[i])*t):02x}" for i in range(3))


def heat_color(rank, n):
    t = (rank - 1) / max(n - 1, 1)
    if t < 0.5:
        return lerp("#bfe3c0", "#fbe3a1", t * 2)
    return lerp("#fbe3a1", "#e8694a", (t - 0.5) * 2)


LABELS = {
    "days_over_100F": "Days ≥100°F", "pct_age_65_plus": "% age 65+", "pct_no_vehicle": "% no vehicle",
    "stroke_rate": "Stroke rate %", "neurologists_per_100k": "Neurologists /100k", "dist_nearest_ER_mi": "ER distance (mi)",
}


def heatmap():
    n = len(rows)
    order = [r["county"] for r in results]
    h = ['<table class="hm"><tr><th>County</th>']
    for m in score.MEASURES:
        h.append(f'<th style="border-bottom:3px solid {GROUP_COLOR[score.MEASURES[m][0]]}">{LABELS[m]}</th>')
    h.append("<th>Total</th></tr>")
    for res in results:
        c = res["county"]
        h.append(f'<tr><td class="cn">{esc(c)}<span>{esc(res["type"])}</span></td>')
        for m in score.MEASURES:
            v = by_county[c][m]
            h.append(f'<td style="background:{heat_color(ranks[m][c], n)}">{v:g}</td>')
        h.append(f'<td class="tot">{res["total"]:.2f}</td></tr>')
    h.append("</table>")
    return "".join(h)


def flow_diagram():
    boxes = [
        (20, 20, "NOAA", "daily highs", "data/noaa_daily_tmax_2015_2024.csv", HEAT),
        (20, 80, "Census ACS", "age 65+, no vehicle", "county_data.csv", VULN),
        (20, 140, "CDC PLACES", "stroke rate", "county_data.csv", VULN),
        (20, 200, "HRSA AHRF", "neurologists", "county_data.csv", ACCESS),
        (20, 260, "CMS + OpenStreetMap", "ER distance", "scripts/er_distance.py", ACCESS),
    ]
    out = ['<svg viewBox="0 0 900 330" role="img" aria-label="Project data flow">',
           '<defs><marker id="ar" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto"><path d="M0,0 L8,4 L0,8 z" fill="#8a8fa3"/></marker></defs>']
    for x, y, t1, t2, href, col in boxes:
        out.append(f'<a href="{href}"><rect x="{x}" y="{y}" width="200" height="48" rx="9" fill="#fff" stroke="{col}" stroke-width="2"/>'
                   f'<text x="{x+12}" y="{y+21}" font-size="13" font-weight="700" fill="#2b2f42">{t1}</text>'
                   f'<text x="{x+12}" y="{y+38}" font-size="11" fill="#6b7088">{t2}</text></a>')
        out.append(f'<path d="M{x+200},{y+24} C 270,{y+24} 270,165 310,165" fill="none" stroke="#b9bdd0" stroke-width="1.6" marker-end="url(#ar)"/>')
    node = lambda x, y, w, t1, t2, href, col: (
        f'<a href="{href}"><rect x="{x}" y="{y}" width="{w}" height="62" rx="10" fill="{col}"/>'
        f'<text x="{x+14}" y="{y+27}" font-size="14" font-weight="700" fill="#fff">{t1}</text>'
        f'<text x="{x+14}" y="{y+46}" font-size="11" fill="#fff" opacity="0.9">{t2}</text></a>')
    out.append(node(310, 134, 190, "county_data.csv", "5 counties, 6 measures", "county_data.csv", "#2b2f42"))
    out.append('<path d="M500,165 L540,165" stroke="#8a8fa3" stroke-width="2" marker-end="url(#ar)"/>')
    out.append(node(540, 134, 150, "score.py", "rank, group, average", "score.py", "#2b2f42"))
    out.append('<path d="M690,165 L725,165" stroke="#8a8fa3" stroke-width="2" marker-end="url(#ar)"/>')
    out.append(node(725, 94, 160, "report.html", "this page", "report.html", HEAT))
    out.append(node(725, 174, 160, "Google Doc", "write-up", DOC_URL, ACCESS))
    out.append('<path d="M690,165 C 710,165 710,125 725,125" fill="none" stroke="#8a8fa3" stroke-width="2" marker-end="url(#ar)"/>')
    out.append('<path d="M690,165 C 710,165 710,205 725,205" fill="none" stroke="#8a8fa3" stroke-width="2" marker-end="url(#ar)"/>')
    out.append("</svg>")
    return "".join(out)


top = results[0]
wise = by_county["Wise"]
links = [
    ("county_data.csv", "county_data.csv", "The data: one row per county, with sources in the last column"),
    ("score.py", "score.py", "Scoring script (rank, group, average)"),
    ("build_report.py", "build_report.py", "Rebuilds this report from the CSV"),
    ("DATA_CHECKLIST.md", "DATA_CHECKLIST.md", "Where each number comes from and how to find it"),
    ("PROJECT_NOTES.md", "PROJECT_NOTES.md", "Project goals, timeline and ideas"),
    ("data/noaa_daily_tmax_2015_2024.csv", "NOAA daily highs", "Raw daily maximum temperatures, five stations"),
    ("data/er_distance_results.json", "ER distance results", "Nearest ER, miles and minutes"),
    ("scripts/er_distance.py", "er_distance.py", "How ER distance was computed"),
    ("heat_and_brain_v4.html", "Written draft (HTML)", "Full write-up: summary, tables, robustness check, limitations (text only; charts are in the Google Doc)"),
    (DOC_URL, "Google Doc", "Editable version of the write-up"),
]

page = f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Heat and the Brain</title>
<style>
*{{box-sizing:border-box}} body{{margin:0;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;background:#f4f5fa;color:#2b2f42;line-height:1.5}}
header{{background:linear-gradient(135deg,#2b2f42 0%,#6a4c93 55%,#e4572e 120%);color:#fff;padding:54px 24px 64px}}
.wrap{{max-width:1120px;margin:0 auto;padding:0 20px}} header .wrap{{padding:0}}
h1{{margin:0 0 8px;font-size:38px;letter-spacing:-.5px}} header p{{margin:0;max-width:760px;opacity:.92;font-size:17px}}
.tag{{display:inline-block;background:rgba(255,255,255,.16);padding:4px 12px;border-radius:99px;font-size:12px;margin-bottom:14px;letter-spacing:.5px}}
.kpis{{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin:-34px auto 8px}}
.kpi{{background:#fff;border-radius:14px;padding:18px 20px;box-shadow:0 6px 22px rgba(43,47,66,.09)}}
.kpi b{{display:block;font-size:30px;line-height:1.1}} .kpi span{{font-size:12.5px;color:#6b7088}}
section{{margin:34px 0}} h2{{font-size:22px;margin:0 0 4px}} .sub{{color:#6b7088;margin:0 0 16px;font-size:14.5px}}
.grid{{display:grid;grid-template-columns:1fr 1fr;gap:18px}}
.card{{background:#fff;border-radius:14px;padding:22px;box-shadow:0 4px 16px rgba(43,47,66,.07)}}
.card h3{{margin:0 0 2px;font-size:16px}} .card p.note{{margin:8px 0 0;font-size:13px;color:#6b7088}}
svg{{width:100%;height:auto;display:block}} svg a{{cursor:pointer}}
table.hm{{width:100%;border-collapse:separate;border-spacing:3px;font-size:14px}}
table.hm th{{font-size:12px;text-align:center;color:#5b6075;padding:6px 4px;font-weight:600}}
table.hm td{{text-align:center;padding:12px 4px;border-radius:7px;font-weight:600}}
table.hm td.cn{{text-align:left;background:none;font-weight:700}} td.cn span{{display:block;font-size:11px;color:#8a8fa3;font-weight:400}}
td.tot{{background:#2b2f42;color:#fff;font-size:15px}}
.legend{{display:flex;gap:14px;font-size:12px;color:#6b7088;margin-top:10px;align-items:center}}
.grad{{height:10px;width:160px;border-radius:5px;background:linear-gradient(90deg,#bfe3c0,#fbe3a1,#e8694a)}}
.find li{{margin:8px 0}} .links{{display:grid;grid-template-columns:1fr 1fr;gap:10px}}
.links a{{display:block;background:#fff;border-radius:11px;padding:13px 16px;text-decoration:none;color:#2b2f42;box-shadow:0 2px 10px rgba(43,47,66,.06);border-left:4px solid #6a4c93}}
.links a:hover{{box-shadow:0 5px 18px rgba(43,47,66,.14)}} .links b{{display:block;font-size:14.5px}} .links span{{font-size:12.5px;color:#6b7088}}
.warn{{background:#fff7ea;border-left:4px solid #e8a33d;padding:14px 18px;border-radius:10px;font-size:14px}}
footer{{color:#8a8fa3;font-size:12.5px;padding:10px 0 50px}}
@media(max-width:820px){{.kpis{{grid-template-columns:1fr 1fr}}.grid,.links{{grid-template-columns:1fr}}h1{{font-size:28px}}}}
</style></head><body>
<header><div class="wrap">
<div class="tag">NORTH &amp; EAST TEXAS · 5-COUNTY PILOT RESULTS</div>
<h1>Heat and the Brain</h1>
<p>Which rural counties near Dallas combine extreme heat with limited access to neurological and emergency care? Five counties, six public-data measures, one transparent score.</p>
</div></header>

<div class="wrap">
<div class="kpis">
<div class="kpi"><b>{esc(top['county'])}</b><span>highest preliminary risk score ({top['total']:.2f} of 5)</span></div>
<div class="kpi"><b>{by_county['Dallas']['days_over_100F']:.0f} days</b><span>average ≥100°F per year in Dallas, the most of the five</span></div>
<div class="kpi"><b>{sum(1 for r in rows if r['neurologists_per_100k']==0)} of 4</b><span>rural counties have no neurologists on record</span></div>
<div class="kpi"><b>{wise['dist_nearest_ER_mi']:.1f} mi</b><span>Wise County, the longest drive to an ER ({minutes['Wise']:.0f} min)</span></div>
</div>

<section><h2>How it fits together</h2><p class="sub">Click any box to open the file. Everything rebuilds from the CSV.</p>
<div class="card">{flow_diagram()}</div></section>

<section><h2>Heat and access</h2><p class="sub">Dallas is hottest but has the best care. The rural counties are cooler but have far fewer neurologists.</p>
<div class="grid">
<div class="card"><h3>Extreme heat days</h3>{bar_chart_heat()}<p class="note">*Henderson's weather station has missing days, so its number is probably too low. Source: NOAA GHCN-Daily.</p></div>
<div class="card"><h3>Neurologist access vs. ER drive time</h3>{bubble_chart()}<p class="note">Bubble size = % of residents age 65+. Dark purple = Dallas (urban). Neurologists: HRSA 2023. Drive time: OpenStreetMap routing.</p></div>
</div></section>

<section><h2>Risk score</h2><p class="sub">Each measure is ranked 1 (lowest risk) to 5 (highest), averaged within three groups, then averaged with equal weights.</p>
<div class="grid">
<div class="card"><h3>Total score by county</h3>{stacked_chart()}<p class="note">Each bar adds one third of each group's score. Hover a segment for its value.</p></div>
<div class="card"><h3>Every measure at a glance</h3>{heatmap()}
<div class="legend"><span>lower risk</span><div class="grad"></div><span>higher risk</span></div>
<p class="note">Cell numbers are the real values. Colors show the county's rank on that measure. Colored underlines match the groups: <span style="color:{HEAT}">Heat</span>, <span style="color:{VULN}">Vulnerability</span>, <span style="color:{ACCESS}">Access gap</span>.</p></div>
</div></section>

<section><h2>What the data suggests</h2>
<div class="card find"><ul>
<li><b>{esc(top['county'])}</b> ranks highest: no neurologists on record, the highest stroke rate (3.7%), and moderate-to-high heat.</li>
<li><b>Wise</b> has the longest drive to an ER ({wise['dist_nearest_ER_mi']:.1f} miles, about {minutes['Wise']:.0f} minutes) and the second-most heat days among rural counties.</li>
<li><b>Henderson</b> has the oldest population (22.4% age 65+) but the fewest heat days.</li>
<li><b>Dallas</b> is the hottest county but has the shortest drive to an ER and 10 neurologists per 100,000.</li>
<li>All ER drives are short (2–7 miles), so neurologist access separates the counties more than ER distance does.</li>
</ul>
<div class="warn"><b>Read with care.</b> This shows association, not causation. Rural neurologist counts are tiny (0–2), one weather station stands in for each county, ER distance is measured from the county center, and equal weights are a choice. Full limitations are in the written draft.</div>
</div></section>

<section><h2>Files and sources</h2><p class="sub">Everything used in this report.</p>
<div class="links">
{''.join(f'<a href="{h}"><b>{esc(t)}</b><span>{esc(d)}</span></a>' for h, t, d in links)}
</div></section>

<footer>Data: NOAA NCEI · US Census ACS 2019–2023 · CDC PLACES 2023 · HRSA AHRF 2024–2025 · CMS Care Compare · OpenStreetMap. Informational only, not medical advice. In an emergency, call 911.</footer>
</div></body></html>"""

open(os.path.join(HERE, "report.html"), "w").write(page)
print("wrote report.html")
