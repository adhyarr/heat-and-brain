"""Build report_expanded.html (24 counties, population-weighted tract drive times) from county_data_expanded.csv.

Usage: python3 build_report_expanded.py
"""
import collections
import csv
import html
import json
import os

import score

HERE = os.path.dirname(os.path.abspath(__file__))
DOC_URL = "https://docs.google.com/document/d/12Vvehx7DZWSoc6yMMl-tF_CJ7IqRWU_9fGOWhPVDKUw/edit?usp=drivesdk"

HEAT, VULN, ACCESS = "#e4572e", "#6a4c93", "#1982c4"
GROUP_COLOR = {"Heat": HEAT, "Vulnerability": VULN, "Access gap": ACCESS}

rows = list(csv.DictReader(open(os.path.join(HERE, "county_data_expanded.csv"))))
for r in rows:
    for k, v in r.items():
        if k not in ("county_fips", "county", "type", "source_notes"):
            r[k] = float(v) if v.strip() else None

measures = score.select_measures(rows)
ranks = {}
for m, (_, risky) in measures.items():
    vals = {r["county"]: r[m] for r in rows if r[m] is not None}
    ranks[m] = score.rank(vals, risky)

results = []
for r in rows:
    c = r["county"]
    gs = {}
    for g in score.GROUPS:
        rs = [ranks[m][c] for m, (gg, _) in measures.items() if gg == g and c in ranks[m]]
        gs[g] = sum(rs) / len(rs)
    results.append({"county": c, "type": r["type"], "groups": gs, "total": sum(gs.values()) / len(gs)})
results.sort(key=lambda x: -x["total"])
by_county = {r["county"]: r for r in rows}
esc = html.escape
N = len(rows)


def bar_chart_heat():
    data = sorted(rows, key=lambda r: -r["days_over_100F"])
    W, rowh, left = 580, 26, 110
    mx = max(r["days_over_100F"] for r in data) * 1.15
    H = rowh * len(data) + 34
    out = [f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="Average days at or above 100F per year">']
    for t in range(0, int(mx) + 1, 5):
        x = left + (W - left - 35) * t / mx
        out.append(f'<line x1="{x:.1f}" y1="0" x2="{x:.1f}" y2="{rowh*len(data)}" stroke="#e6e8ef"/>')
        out.append(f'<text x="{x:.1f}" y="{rowh*len(data)+16}" font-size="10.5" fill="#8a8fa3" text-anchor="middle">{t}</text>')
    for i, r in enumerate(data):
        y = i * rowh + 4
        w = (W - left - 35) * r["days_over_100F"] / mx
        col = VULN if r["type"] == "urban" else HEAT
        out.append(f'<text x="{left-8}" y="{y+14}" font-size="11.5" text-anchor="end" fill="#2b2f42">{esc(r["county"])}</text>')
        out.append(f'<rect x="{left}" y="{y}" width="{w:.1f}" height="17" rx="4" fill="{col}" opacity="0.82"/>')
        out.append(f'<text x="{left+w+6:.1f}" y="{y+13}" font-size="11" font-weight="600" fill="#2b2f42">{r["days_over_100F"]:.1f}</text>')
    out.append(f'<text x="{left}" y="{H-4}" font-size="10.5" fill="#8a8fa3">avg days ≥100°F/yr (2015–2024; purple = urban core)</text></svg>')
    return "".join(out)


def scatter_access():
    W, H, L, B, T, R = 580, 420, 56, 46, 20, 24
    xs = [r["er_drive_min_popw"] for r in rows]
    ys = [r["stroke_l1_l2_min_popw"] for r in rows]
    xmax, ymax = max(xs) * 1.12, max(ys) * 1.12
    px = lambda v: L + (W - L - R) * v / xmax
    py = lambda v: H - B - (H - B - T) * v / ymax
    out = [f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="Population-weighted ER vs DSHS Stroke Center drive time">']
    for t in range(0, int(xmax) + 1, 10):
        out.append(f'<line x1="{px(t):.1f}" y1="{T}" x2="{px(t):.1f}" y2="{H-B}" stroke="#eef0f6"/>')
        out.append(f'<text x="{px(t):.1f}" y="{H-B+16}" font-size="11" fill="#8a8fa3" text-anchor="middle">{t}</text>')
    for t in range(0, int(ymax) + 1, 20):
        out.append(f'<line x1="{L}" y1="{py(t):.1f}" x2="{W-R}" y2="{py(t):.1f}" stroke="#eef0f6"/>')
        out.append(f'<text x="{L-8}" y="{py(t)+4:.1f}" font-size="11" fill="#8a8fa3" text-anchor="end">{t}</text>')
    out.append(f'<text x="{(L+W-R)/2}" y="{H-8}" font-size="11.5" fill="#5b6075" text-anchor="middle">Pop-weighted drive to nearest ER (min)</text>')
    out.append(f'<text transform="translate(14 {(T+H-B)/2}) rotate(-90)" font-size="11.5" fill="#5b6075" text-anchor="middle">Pop-weighted drive to DSHS Level I–II Stroke Center (min)</text>')
    # highlight >15 min ER and >45 min stroke center
    out.append(f'<rect x="{px(15):.1f}" y="{T}" width="{W-R-px(15):.1f}" height="{py(45)-T:.1f}" fill="{ACCESS}" opacity="0.07"/>')
    out.append(f'<text x="{W-R-6}" y="{T+14}" font-size="10.5" fill="{ACCESS}" text-anchor="end">&gt;15m ER + &gt;45m Level I–II Stroke Center</text>')
    for r in rows:
        x, y = px(r["er_drive_min_popw"]), py(r["stroke_l1_l2_min_popw"])
        rad = 4 + r["pct_age_65_plus"] * 0.45
        col = VULN if r["type"] == "urban" else HEAT
        out.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{rad:.1f}" fill="{col}" opacity="0.58" stroke="{col}" stroke-width="1.3"><title>{esc(r["county"])}: ER {r["er_drive_min_popw"]}m, Stroke L1-L2 {r["stroke_l1_l2_min_popw"]}m</title></circle>')
        if r["county"] in ("Hill", "Erath", "Freestone", "Van Zandt", "Rains", "Navarro", "Hood", "Dallas", "Wise", "Henderson", "Hopkins", "Cooke"):
            out.append(f'<text x="{x+rad+4:.1f}" y="{y+3:.1f}" font-size="10.5" fill="#2b2f42">{esc(r["county"])}</text>')
    out.append("</svg>")
    return "".join(out)


def stacked_chart():
    W, rowh, left = 580, 26, 110
    mx = float(N)
    H = rowh * len(results) + 46
    out = [f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="Total score by county">']
    for t in range(0, N + 1, 4):
        x = left + (W - left - 50) * t / mx
        out.append(f'<line x1="{x:.1f}" y1="0" x2="{x:.1f}" y2="{rowh*len(results)}" stroke="#e6e8ef"/>')
        out.append(f'<text x="{x:.1f}" y="{rowh*len(results)+15}" font-size="10.5" fill="#8a8fa3" text-anchor="middle">{t}</text>')
    for i, r in enumerate(results):
        y = i * rowh + 4
        x = left
        out.append(f'<text x="{left-8}" y="{y+14}" font-size="11.5" text-anchor="end" fill="#2b2f42">{esc(r["county"])}</text>')
        for g in score.GROUPS:
            w = (W - left - 50) * (r["groups"][g] / 3) / mx
            out.append(f'<rect x="{x:.1f}" y="{y}" width="{w:.1f}" height="17" fill="{GROUP_COLOR[g]}"><title>{g}: {r["groups"][g]:.2f}</title></rect>')
            x += w
        out.append(f'<text x="{x+6:.1f}" y="{y+14}" font-size="11" font-weight="700" fill="#2b2f42">{r["total"]:.2f}</text>')
    ly = rowh * len(results) + 34
    lx = left
    for g in score.GROUPS:
        out.append(f'<rect x="{lx}" y="{ly-9}" width="11" height="11" rx="2" fill="{GROUP_COLOR[g]}"/><text x="{lx+16}" y="{ly}" font-size="11.5" fill="#5b6075">{g}</text>')
        lx += 120
    out.append("</svg>")
    return "".join(out)


def lerp(c1, c2, t):
    a = [int(c1[i:i + 2], 16) for i in (1, 3, 5)]
    b = [int(c2[i:i + 2], 16) for i in (1, 3, 5)]
    return "#" + "".join(f"{round(a[i]+(b[i]-a[i])*t):02x}" for i in range(3))


def heat_color(rk):
    t = (rk - 1) / max(N - 1, 1)
    if t < 0.5:
        return lerp("#bfe3c0", "#fbe3a1", t * 2)
    return lerp("#fbe3a1", "#e8694a", (t - 0.5) * 2)


LABELS = {
    "days_over_100F": "Days ≥100°F",
    "pct_age_65_plus": "% 65+",
    "pct_no_vehicle": "% no veh",
    "stroke_rate": "Stroke %",
    "neurologists_per_100k": "Neuro /100k",
    "er_drive_min_popw": "ER min (pop-w)",
    "stroke_l1_l2_min_popw": "DSHS Stroke L1-L2 min",
}


def heatmap():
    h = ['<table class="hm"><tr><th>County</th>']
    for m in measures:
        h.append(f'<th style="border-bottom:3px solid {GROUP_COLOR[measures[m][0]]}">{LABELS[m]}</th>')
    h.append("<th>Total</th></tr>")
    for res in results:
        c = res["county"]
        h.append(f'<tr><td class="cn">{esc(c)}<span>{esc(res["type"])}</span></td>')
        for m in measures:
            v = by_county[c][m]
            h.append(f'<td style="background:{heat_color(ranks[m][c])}">{v:g}</td>')
        h.append(f'<td class="tot">{res["total"]:.2f}</td></tr>')
    h.append("</table>")
    return "".join(h)


def trend_chart():
    b_heat = json.load(open(os.path.join(HERE, "data", "stage_b_heat.json")))
    a_cnty = json.load(open(os.path.join(HERE, "data", "stage_a_counties.json")))
    st_to_c = {}
    for fips, info in b_heat.items():
        if info:
            st_to_c.setdefault(info["station"], []).append(a_cnty[fips]["county"])
    obs = collections.defaultdict(lambda: collections.defaultdict(int))
    hot = collections.defaultdict(lambda: collections.defaultdict(int))
    for r in csv.DictReader(open(os.path.join(HERE, "data", "noaa_tmax_expanded.csv"))):
        sid = r["STATION"]
        if sid not in st_to_c:
            continue
        y = r["DATE"][:4]
        obs[sid][y] += 1
        if float(r["TMAX_F"]) >= 100:
            hot[sid][y] += 1
    years = [str(y) for y in range(2015, 2025)]
    by_y = {y: [] for y in years}
    series = {}
    for fips, info in b_heat.items():
        if not info:
            continue
        sid, c = info["station"], a_cnty[fips]["county"]
        vals = []
        for y in years:
            req = 0.90 * (366 if int(y) % 4 == 0 else 365)
            if obs[sid][y] >= req:
                vals.append(hot[sid][y])
                by_y[y].append(hot[sid][y])
            else:
                vals.append(None)
        if c in ("Hood", "Hill", "Dallas"):
            series[c] = vals
    series["24-County Avg"] = [round(sum(by_y[y]) / len(by_y[y]), 1) for y in years]

    W, H, L, B, T, R = 980, 290, 48, 36, 20, 140
    ymax = 70
    px = lambda i: L + (W - L - R) * i / (len(years) - 1)
    py = lambda v: H - B - (H - B - T) * v / ymax
    out = [f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="10-year extreme heat trend 2015 to 2024">']
    for t in range(0, ymax + 1, 15):
        out.append(f'<line x1="{L}" y1="{py(t):.1f}" x2="{W-R}" y2="{py(t):.1f}" stroke="#eef0f6"/>')
        out.append(f'<text x="{L-8}" y="{py(t)+4:.1f}" font-size="11" fill="#8a8fa3" text-anchor="end">{t}</text>')
    for i, y in enumerate(years):
        out.append(f'<text x="{px(i):.1f}" y="{H-12}" font-size="11" fill="#5b6075" text-anchor="middle">{y}</text>')

    styles = [
        ("Hood", "#e4572e", "2.2", ""),
        ("Hill", "#f29e4c", "2.2", ""),
        ("Dallas", "#6a4c93", "2.2", "5,3"),
        ("24-County Avg", "#2b2f42", "3.2", ""),
    ]
    for idx, (label, col, sw, dash) in enumerate(styles):
        pts = [(px(i), py(v)) for i, v in enumerate(series[label]) if v is not None]
        d = "M " + " L ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
        da = f' stroke-dasharray="{dash}"' if dash else ""
        out.append(f'<path d="{d}" fill="none" stroke="{col}" stroke-width="{sw}"{da}/>')
        for x, y in pts:
            out.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3.2" fill="{col}"/>')
        ly = T + 18 + idx * 24
        out.append(f'<line x1="{W-R+16}" y1="{ly}" x2="{W-R+36}" y2="{ly}" stroke="{col}" stroke-width="{sw}"{da}/>')
        out.append(f'<text x="{W-R+42}" y="{ly+4}" font-size="12" font-weight="600" fill="#2b2f42">{label}</text>')
    out.append(f'<text transform="translate(14 {(T+H-B)/2}) rotate(-90)" font-size="11" fill="#5b6075" text-anchor="middle">Days ≥100°F</text></svg>')
    return "".join(out)


top = results[0]
rural_rows = [r for r in rows if r["type"] == "rural"]
urban_rows = [r for r in rows if r["type"] == "urban"]
avg_rural_er = sum(r["er_drive_min_popw"] for r in rural_rows) / len(rural_rows)
avg_urban_er = sum(r["er_drive_min_popw"] for r in urban_rows) / len(urban_rows)
avg_rural_hub = sum(r["stroke_l1_l2_min_popw"] for r in rural_rows) / len(rural_rows)
avg_urban_hub = sum(r["stroke_l1_l2_min_popw"] for r in urban_rows) / len(urban_rows)

links = [
    ("map.html", "Interactive Map (24 counties + 1,885 tracts)", "Explore risk scores, drive times, and hospital hubs"),
    ("county_data_expanded.csv", "county_data_expanded.csv", "24 counties, 7 scoring measures + tract drive-time metrics"),
    ("data/tract_access.csv", "data/tract_access.csv", "All 1,885 Census tracts with ER & neurology-hub drive times"),
    ("score.py", "score.py", "Scoring script (auto-detects expanded vs 5-county CSV)"),
    ("build_report_expanded.py", "build_report_expanded.py", "Rebuilds this 24-county report"),
    ("report.html", "report.html", "Original 5-county pilot report"),
    (DOC_URL, "Google Doc", "Editable write-up with charts"),
]

page = f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Too Hot, Too Far: 24-County Expanded Analysis</title>
<style>
*{{box-sizing:border-box}} body{{margin:0;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;background:#f4f5fa;color:#2b2f42;line-height:1.5}}
header{{background:linear-gradient(135deg,#2b2f42 0%,#6a4c93 55%,#e4572e 120%);color:#fff;padding:44px 24px 58px}}
.wrap{{max-width:1160px;margin:0 auto;padding:0 20px}} header .wrap{{padding:0;display:flex;justify-content:space-between;align-items:flex-end;flex-wrap:wrap;gap:14px}}
.nav{{display:flex;gap:8px;flex-wrap:wrap;align-items:center}}
.nav a{{color:#fff;text-decoration:none;background:rgba(255,255,255,.18);padding:7px 13px;border-radius:8px;font-size:13px;display:inline-block}}
h1{{margin:0 0 8px;font-size:34px;letter-spacing:-.5px}} header p{{margin:0;max-width:780px;opacity:.92;font-size:16px}}
.tag{{display:inline-block;background:rgba(255,255,255,.16);padding:4px 12px;border-radius:99px;font-size:12px;margin-bottom:12px;letter-spacing:.5px}}
.kpis{{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin:-30px auto 8px}}
.kpi{{background:#fff;border-radius:14px;padding:16px 18px;box-shadow:0 6px 22px rgba(43,47,66,.09)}}
.kpi b{{display:block;font-size:27px;line-height:1.15}} .kpi span{{font-size:12.5px;color:#6b7088}}
section{{margin:30px 0}} h2{{font-size:21px;margin:0 0 4px}} .sub{{color:#6b7088;margin:0 0 14px;font-size:14px}}
.grid{{display:grid;grid-template-columns:1fr 1fr;gap:18px}}
.card{{background:#fff;border-radius:14px;padding:20px;box-shadow:0 4px 16px rgba(43,47,66,.07)}}
.card h3{{margin:0 0 6px;font-size:15.5px}} .card p.note{{margin:8px 0 0;font-size:12.5px;color:#6b7088}}
svg{{width:100%;height:auto;display:block}}
table.hm{{width:100%;border-collapse:separate;border-spacing:2.5px;font-size:12.5px}}
table.hm th{{font-size:11px;text-align:center;color:#5b6075;padding:5px 3px;font-weight:600}}
table.hm td{{text-align:center;padding:7px 4px;border-radius:5px;font-weight:600}}
table.hm td.cn{{text-align:left;background:none;font-weight:700}} td.cn span{{display:inline-block;margin-left:6px;font-size:10.5px;color:#8a8fa3;font-weight:400}}
td.tot{{background:#2b2f42;color:#fff;font-size:13px}}
.legend{{display:flex;gap:14px;font-size:12px;color:#6b7088;margin-top:10px;align-items:center}}
.grad{{height:10px;width:160px;border-radius:5px;background:linear-gradient(90deg,#bfe3c0,#fbe3a1,#e8694a)}}
.links{{display:grid;grid-template-columns:1fr 1fr;gap:10px}}
.links a{{display:block;background:#fff;border-radius:11px;padding:13px 16px;text-decoration:none;color:#2b2f42;box-shadow:0 2px 10px rgba(43,47,66,.06);border-left:4px solid #6a4c93}}
.links b{{display:block;font-size:14px}} .links span{{font-size:12px;color:#6b7088}}
.warn{{background:#fff7ea;border-left:4px solid #e8a33d;padding:14px 18px;border-radius:10px;font-size:13.5px;margin-top:14px}}
footer{{color:#8a8fa3;font-size:12px;padding:10px 0 40px}}
@media(max-width:860px){{.kpis{{grid-template-columns:1fr 1fr}}.grid,.links{{grid-template-columns:1fr}}}}
</style></head><body>
<header><div class="wrap">
<div>
<div class="tag">NORTH &amp; EAST TEXAS · 24-COUNTY EXPANDED ANALYSIS</div>
<h1>Too Hot, Too Far: North &amp; East Texas</h1>
<p>24 counties (4 urban DFW core + 20 surrounding rural/exurban counties), 1,885 Census tracts, and population-weighted driving times to emergency rooms and neurology hubs.</p>
</div>
<div class="nav">
<a href="index.html">Home</a>
<a href="map.html">Map</a>
<a href="checker.html">Live Risk Tool</a>
<a href="solutions.html">Solutions</a>
</div>
</div></header>

<div class="wrap">
<div class="kpis">
<div class="kpi"><b>{esc(top['county'])}</b><span>highest risk score ({top['total']:.2f} of {N})</span></div>
<div class="kpi"><b>{avg_rural_er:.1f} vs {avg_urban_er:.1f} min</b><span>avg pop-weighted ER drive (rural vs urban core)</span></div>
<div class="kpi"><b>{avg_rural_hub:.1f} vs {avg_urban_hub:.1f} min</b><span>avg pop-weighted drive to DSHS Level I–II Stroke Center</span></div>
<div class="kpi"><b>12 of 20</b><span>rural counties have 0 neurologists on record</span></div>
</div>

<section><h2>Heat and population-weighted access</h2>
<p class="sub">Tract-level routing measures where residents actually live, rather than a single county center point.</p>
<div class="grid">
<div class="card"><h3>Extreme heat days (2015–2024)</h3>{bar_chart_heat()}<p class="note">Nearest NOAA station within 50 km with ≥95% completeness. Limestone was excluded (no qualifying station).</p></div>
<div class="card"><h3>ER drive vs. DSHS Level I–II Stroke Center drive</h3>{scatter_access()}<p class="note">Bubble size = % age 65+. Official Texas DSHS Comprehensive &amp; Advanced Stroke Centers; all 4 urban core counties sit near 13–24 min.</p></div>
</div></section>

<section><h2>Combined risk score (1 to {N})</h2>
<p class="sub">Equal weights across Heat, Vulnerability (% 65+, % no vehicle, stroke rate), and Access gap (neurologists/100k, pop-weighted ER drive, pop-weighted DSHS Level I–II Stroke Center drive).</p>
<div class="grid">
<div class="card"><h3>Total score by county</h3>{stacked_chart()}<p class="note">Hill County leads across all three groups (20.0 Heat, 20.0 Vulnerability, 19.7 Access gap).</p></div>
<div class="card"><h3>All 24 counties at a glance</h3>{heatmap()}
<div class="legend"><span>lower risk</span><div class="grad"></div><span>higher risk</span></div></div>
</div>
<div class="warn"><b>Method notes.</b> Association only, not causation. One weather station represents each county; Limestone was excluded because its nearest stations lacked 95% 10-year coverage. Stroke centers use the official Texas DSHS Comprehensive (Level I) and Advanced (Level II) Stroke Facilities list.</div>
</section>

<section><h2>10-year heat trend (2015–2024)</h2>
<p class="sub">Extreme-heat days surged across all 24 counties in 2022 (39.3-day average) and 2023 (43.1-day average), nearly four times the 2015–2016 baseline.</p>
<div class="card">{trend_chart()}<p class="note">Only years with ≥90% daily station observations are plotted (Hood 2024 omitted for missing days). In 2023, Hood reached 62 days and Hill reached 55 days ≥100°F.</p></div>
</section>

<section><h2>Spotlight: highest-risk rural case studies</h2>
<p class="sub">Three rural counties illustrate distinct heat-and-access gaps.</p>
<div class="grid" style="grid-template-columns:repeat(3,1fr)">
<div class="card"><h3>Hill County (#1 overall · 19.89/24)</h3><p class="note" style="color:#2b2f42;margin-top:6px">High risk across every dimension: <b>19.4 days ≥100°F/yr</b> (55 in 2023), <b>20.3% age 65+</b>, <b>6.2% no vehicle</b>, and <b>0 neurologists</b>. Most residents use Hill Regional Hospital in Hillsboro (avg ER drive 22.3 min), but <b>100% live &gt;60 min</b> from a DSHS Level I–II stroke center (avg 80.9 min).</p></div>
<div class="card"><h3>Hood County (#4 overall · 15.78/24)</h3><p class="note" style="color:#2b2f42;margin-top:6px">Both the <b>hottest</b> (34.2 days ≥100°F/yr; 62 in 2023) and <b>oldest</b> (25.4% age 65+) county in the study. While Lake Granbury Medical Center (Level III Primary Stroke) is 19.7 min away on average, residents average <b>55.7 min</b> to a Level I–II comprehensive/advanced stroke center.</p></div>
<div class="card"><h3>Van Zandt County (#8 overall · 14.00/24)</h3><p class="note" style="color:#2b2f42;margin-top:6px">Longest emergency drive in the study: <b>42.3 min (28.0 mi)</b> average to the nearest ER, with <b>100% of residents &gt;15 min</b> away. With no in-county CMS ER hospital, tracts route out-of-county to Kaufman, Quitman, or Athens, plus <b>0 neurologists</b> and 20.2% age 65+.</p></div>
</div></section>

<section><h2>Project files</h2>
<div class="links">{''.join(f'<a href="{h}"><b>{esc(t)}</b><span>{esc(d)}</span></a>' for h, t, d in links)}</div>
</section>

<footer>Data: NOAA NCEI · US Census ACS 2019–2023 &amp; CenPop2020 · CDC PLACES 2023 · HRSA AHRF 2024–2025 · CMS Care Compare · OpenStreetMap/OSRM. Informational only, not medical advice.</footer>
</div></body></html>"""

open(os.path.join(HERE, "report_expanded.html"), "w").write(page)
print("wrote report_expanded.html")
