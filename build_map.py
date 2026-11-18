"""Build map.html: interactive 24-county + 1,885-tract Leaflet map from county_data_expanded.csv.

Usage: python3 build_map.py
"""
import csv
import json
import os

import score

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")

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

county_props = {}
for r in rows:
    c = r["county"]
    gs = {}
    for g in score.GROUPS:
        rs = [ranks[m][c] for m, (gg, _) in measures.items() if gg == g and c in ranks[m]]
        gs[g] = round(sum(rs) / len(rs), 2)
    r["score_heat"] = gs["Heat"]
    r["score_vuln"] = gs["Vulnerability"]
    r["score_access"] = gs["Access gap"]
    r["score_total"] = round(sum(gs.values()) / len(gs), 2)
    county_props[r["county_fips"]] = r

gj = json.load(open(os.path.join(DATA, "counties_24.geojson")))
for f in gj["features"]:
    f["properties"] = county_props[f["id"]]

# Compact tract list: [fips, pop, lat, lon, er_min, hub_min, er_name, hub_name]
tracts = []
for t in csv.DictReader(open(os.path.join(DATA, "tract_access.csv"))):
    if t["county_fips"] in county_props and t["er_min"]:
        tracts.append([
            t["county_fips"], int(t["population"]),
            round(float(t["lat"]), 4), round(float(t["lon"]), 4),
            round(float(t["er_min"]), 1), round(float(t["hub_min"]), 1),
            t["er_name"], t["hub_name"],
        ])

# Official Texas DSHS Stroke Centers (Level I-II) + CMS ERs in or near the 24-county bounding box
dshs_l1_l2 = []
for s in json.load(open(os.path.join(DATA, "tx_dshs_stroke_centers.json")))["located"]:
    if s["level_num"] <= 2:
        lat, lon = s["pt"]
        if 31.3 <= lat <= 34.2 and -98.6 <= lon <= -94.8:
            dshs_l1_l2.append({"name": s["name"], "county": f"{s['city']} ({s['level']})", "lat": round(lat, 4), "lon": round(lon, 4), "hub": True, "neuro": s["level"]})

hosp = []
for h in json.load(open(os.path.join(DATA, "hospitals_geocoded.json"))):
    lat, lon = h["pt"]
    if 31.3 <= lat <= 34.0 and -98.6 <= lon <= -94.9:
        hosp.append({
            "name": h["name"], "county": h["county"] + " County", "lat": round(lat, 4), "lon": round(lon, 4),
            "hub": False, "neuro": 0,
        })
hosp.extend(dshs_l1_l2)

html_out = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Too Hot, Too Far: Interactive County &amp; Tract Map</title>
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<style>
*{{box-sizing:border-box}} body{{margin:0;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;color:#2b2f42;background:#f4f5fa;display:flex;flex-direction:column;height:100vh}}
header{{background:linear-gradient(135deg,#2b2f42 0%,#6a4c93 60%,#e4572e 120%);color:#fff;padding:12px 20px;display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:10px}}
header h1{{margin:0;font-size:19px}} header p{{margin:2px 0 0;font-size:12.5px;opacity:.9}}
.nav a{{color:#fff;text-decoration:none;background:rgba(255,255,255,.18);padding:6px 12px;border-radius:8px;font-size:12.5px;margin-left:6px}}
.main{{display:flex;flex:1;min-height:0}}
#map{{flex:1;min-height:420px;background:#e8ecf4}}
.side{{width:350px;background:#fff;border-left:1px solid #e2e5f0;padding:16px;overflow-y:auto;display:flex;flex-direction:column;gap:14px}}
.lbl{{font-size:11.5px;font-weight:700;text-transform:uppercase;color:#6b7088;letter-spacing:.4px;margin-bottom:6px}}
select{{width:100%;padding:8px 10px;border-radius:8px;border:1px solid #cfd4e4;font-size:14px;background:#fff;color:#2b2f42}}
.checks label{{display:flex;align-items:center;gap:8px;font-size:13.5px;margin:6px 0;cursor:pointer}}
.leg-bar{{height:12px;border-radius:6px;background:linear-gradient(90deg,#bfe3c0,#fbe3a1,#e8694a);margin:6px 0 4px}}
.leg-nums{{display:flex;justify-content:space-between;font-size:11.5px;color:#6b7088}}
.panel{{background:#f7f8fc;border-radius:10px;padding:14px;border:1px solid #e6e9f2}}
.panel h2{{margin:0 0 2px;font-size:18px}} .badge{{display:inline-block;font-size:11px;padding:2px 8px;border-radius:99px;background:#e8eaf6;color:#3f51b5;margin-bottom:8px}}
.badge.rural{{background:#fdecea;color:#c0392b}}
.kv{{display:grid;grid-template-columns:1fr auto;gap:5px 10px;font-size:13px;margin-top:8px}}
.kv span{{color:#6b7088}} .kv b{{text-align:right}}
.note{{font-size:11.5px;color:#6b7088;line-height:1.45;margin-top:8px}}
@media(max-width:850px){{.main{{flex-direction:column}}.side{{width:100%;height:44vh;border-left:none;border-top:1px solid #e2e5f0}}}}
</style>
</head>
<body>
<header>
  <div>
    <h1>Too Hot, Too Far: 24-County &amp; Tract Map</h1>
    <p>North &amp; East Texas · 24 counties · 1,885 Census tracts · Population-weighted ER &amp; neurology-hub drive times</p>
  </div>
  <div class="nav">
    <a href="report_expanded.html">24-County Report</a>
    <a href="report.html">5-County Pilot</a>
  </div>
</header>
<div class="main">
  <div id="map"></div>
  <div class="side">
    <div>
      <div class="lbl">Color counties by</div>
      <select id="metric">
        <option value="score_total">Combined Risk Score (1–24)</option>
        <option value="days_over_100F">Extreme Heat Days (≥100°F / yr)</option>
        <option value="stroke_l1_l2_min_popw">DSHS Level I–II Stroke Center Drive (min, pop-w)</option>
        <option value="stroke_l1_l3_min_popw">DSHS Level I–III Stroke Center Drive (min, pop-w)</option>
        <option value="er_drive_min_popw">Nearest ER Drive Time (min, pop-weighted)</option>
        <option value="pct_age_65_plus">% Residents Age 65+</option>
        <option value="pct_no_vehicle">% Households with No Vehicle</option>
        <option value="neurologists_per_100k">Neurologists per 100,000</option>
      </select>
      <div class="leg-bar"></div>
      <div class="leg-nums"><span id="lmin">Low</span><span id="lmid"></span><span id="lmax">High</span></div>
    </div>
    <div class="checks">
      <div class="lbl">Map layers</div>
      <label><input type="checkbox" id="chk-tracts"> Show 1,885 Census tracts (colored by neuro hub drive)</label>
      <label><input type="checkbox" id="chk-hosp" checked> Show ER hospitals &amp; DSHS Level I–II Stroke Centers (blue = stroke center)</label>
    </div>
    <div class="panel" id="info">
      <div class="lbl">County details</div>
      <p class="note">Click any county on the map to inspect its scores, heat days, demographics, and driving times.</p>
    </div>
  </div>
</div>

<script>
const GEO = {json.dumps(gj)};
const TRACTS = {json.dumps(tracts)};
const HOSP = {json.dumps(hosp)};

const METRICS = {{
  score_total: {{label: "Risk Score", unit: " / 24", inv: false}},
  days_over_100F: {{label: "Days ≥100°F", unit: " days/yr", inv: false}},
  stroke_l1_l2_min_popw: {{label: "DSHS L1–L2 Stroke Drive", unit: " min", inv: false}},
  stroke_l1_l3_min_popw: {{label: "DSHS L1–L3 Stroke Drive", unit: " min", inv: false}},
  er_drive_min_popw: {{label: "ER Drive", unit: " min", inv: false}},
  pct_age_65_plus: {{label: "Age 65+", unit: "%", inv: false}},
  pct_no_vehicle: {{label: "No Vehicle", unit: "%", inv: false}},
  neurologists_per_100k: {{label: "Neurologists /100k", unit: "", inv: true}}
}};

const map = L.map("map").setView([32.65, -96.65], 8);
L.tileLayer("https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Light_Gray_Base/MapServer/tile/{{z}}/{{y}}/{{x}}", {{
  attribution: "Tiles &copy; Esri", maxZoom: 16
}}).addTo(map);
L.tileLayer("https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Light_Gray_Reference/MapServer/tile/{{z}}/{{y}}/{{x}}", {{
  maxZoom: 16, pane: "overlayPane"
}}).addTo(map);

function lerp(c1, c2, t) {{
  const a = [1,3,5].map(i => parseInt(c1.slice(i,i+2),16));
  const b = [1,3,5].map(i => parseInt(c2.slice(i,i+2),16));
  return "#" + [0,1,2].map(i => Math.round(a[i] + (b[i]-a[i])*t).toString(16).padStart(2,"0")).join("");
}}
function colorScale(t) {{
  t = Math.max(0, Math.min(1, t));
  return t < 0.5 ? lerp("#bfe3c0", "#fbe3a1", t*2) : lerp("#fbe3a1", "#e8694a", (t-0.5)*2);
}}

let curMetric = "score_total";
let geoLayer;

function getRange(m) {{
  const vals = GEO.features.map(f => f.properties[m]);
  return [Math.min(...vals), Math.max(...vals)];
}}

function styleFeature(f) {{
  const m = curMetric, [mn, mx] = getRange(m);
  let t = (f.properties[m] - mn) / Math.max(mx - mn, 1e-6);
  if (METRICS[m].inv) t = 1 - t;
  return {{fillColor: colorScale(t), weight: 1.8, color: "#ffffff", fillOpacity: 0.72}};
}}

function showInfo(p) {{
  document.getElementById("info").innerHTML = `
    <h2>${{p.county}} County</h2>
    <span class="badge ${{p.type}}">${{p.type}} · pop ${{Math.round(p.population).toLocaleString()}}</span>
    <div class="kv">
      <span>Combined Risk Score</span><b>${{p.score_total}} / 24</b>
      <span>Heat / Vuln / Access</span><b>${{p.score_heat}} / ${{p.score_vuln}} / ${{p.score_access}}</b>
      <span>Days ≥100°F (2015–24)</span><b>${{p.days_over_100F}} / yr</b>
      <span>Age 65+</span><b>${{p.pct_age_65_plus}}%</b>
      <span>No-vehicle households</span><b>${{p.pct_no_vehicle}}%</b>
      <span>Stroke rate</span><b>${{p.stroke_rate}}%</b>
      <span>Neurologists (HRSA 2023)</span><b>${{Math.round(p.neurologists)}} (${{p.neurologists_per_100k}}/100k)</b>
      <span>ER drive (pop-weighted)</span><b>${{p.er_drive_min_popw}} min (${{p.er_drive_mi_popw}} mi)</b>
      <span>Pop >15 min from ER</span><b>${{p.pct_pop_er_over_15min}}%</b>
      <span>DSHS Stroke L1–L2 drive</span><b>${{p.stroke_l1_l2_min_popw}} min (${{p.stroke_l1_l2_mi_popw}} mi)</b>
      <span>Pop &gt;60 min from L1–L2</span><b>${{p.pct_pop_stroke_l1_l2_over_60min}}%</b>
      <span>DSHS Stroke L1–L3 drive</span><b>${{p.stroke_l1_l3_min_popw}} min</b>
    </div>
    <div class="note">${{p.source_notes}}</div>`;
}}

function updateLayer() {{
  if (geoLayer) map.removeLayer(geoLayer);
  const [mn, mx] = getRange(curMetric), u = METRICS[curMetric].unit;
  document.getElementById("lmin").textContent = (METRICS[curMetric].inv ? mx : mn) + u + " (lower risk)";
  document.getElementById("lmax").textContent = (METRICS[curMetric].inv ? mn : mx) + u + " (higher risk)";
  geoLayer = L.geoJSON(GEO, {{
    style: styleFeature,
    onEachFeature: (f, lyr) => {{
      const p = f.properties;
      lyr.bindTooltip(`<b>${{p.county}}</b>: ${{p[curMetric]}}${{u}}`);
      lyr.on("click", () => showInfo(p));
      lyr.on("mouseover", () => lyr.setStyle({{weight: 3, color: "#2b2f42"}}));
      lyr.on("mouseout", () => geoLayer.resetStyle(lyr));
    }}
  }}).addTo(map);
}}

const tractLayer = L.layerGroup();
TRACTS.forEach(([fips, pop, lat, lon, er_m, hub_m, er_n, hub_n]) => {{
  const c = colorScale(Math.min(hub_m / 90, 1));
  L.circleMarker([lat, lon], {{
    radius: Math.max(2.5, Math.min(7, Math.sqrt(pop) / 22)),
    color: "#2b2f42", weight: 0.4, fillColor: c, fillOpacity: 0.85
  }}).bindTooltip(`Tract pop ${{pop.toLocaleString()}}<br>ER: ${{er_m}} min (${{er_n}})<br>Neuro hub: ${{hub_m}} min (${{hub_n}})`)
    .addTo(tractLayer);
}});

const hospLayer = L.layerGroup();
HOSP.forEach(h => {{
  L.circleMarker([h.lat, h.lon], {{
    radius: h.hub ? 5.5 : 4,
    color: "#fff", weight: 1.5,
    fillColor: h.hub ? "#1982c4" : "#2b2f42", fillOpacity: 0.92
  }}).bindTooltip(`<b>${{h.name}}</b><br>${{h.county}} (${{h.hub ? "TX DSHS Stroke Center" : "Local ER"}})`)
    .addTo(hospLayer);
}});
hospLayer.addTo(map);

document.getElementById("metric").addEventListener("change", e => {{ curMetric = e.target.value; updateLayer(); }});
document.getElementById("chk-tracts").addEventListener("change", e => e.target.checked ? tractLayer.addTo(map) : map.removeLayer(tractLayer));
document.getElementById("chk-hosp").addEventListener("change", e => e.target.checked ? hospLayer.addTo(map) : map.removeLayer(hospLayer));

updateLayer();
// Show highest-risk county (Hill) by default
const hill = GEO.features.find(f => f.properties.county === "Hill");
if (hill) showInfo(hill.properties);
</script>
</body>
</html>
"""

open(os.path.join(HERE, "map.html"), "w").write(html_out)
print("wrote map.html")
