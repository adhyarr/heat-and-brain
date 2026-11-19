"""Build checker.html: Live NWS Heat-Risk & Care-Access Lookup using current location (GPS or City/ZIP) or county preset.

Usage: python3 build_checker.py
"""
import csv
import json
import os

import score

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")

rows = list(csv.DictReader(open(os.path.join(HERE, "county_data_expanded.csv"))))
coords = json.load(open(os.path.join(DATA, "stage_a_counties.json")))

for r in rows:
    for k in r:
        if k not in ("county_fips", "county", "type", "source_notes"):
            r[k] = float(r[k])
    c = coords[r["county_fips"]]
    r["lat"] = round(c["lat"], 4)
    r["lon"] = round(c["lon"], 4)

measures = score.select_measures(rows)
ranks = {m: score.rank({r["county"]: r[m] for r in rows}, risky) for m, (_, risky) in measures.items()}
for r in rows:
    c = r["county"]
    gs = {g: sum(ranks[m][c] for m, (gg, _) in measures.items() if gg == g) / sum(1 for _, (gg, _) in measures.items() if gg == g) for g in score.GROUPS}
    r["score_total"] = round(sum(gs.values()) / len(gs), 2)

rows.sort(key=lambda r: r["county"])

# Compact hospital lists for live distance/drive calculation from user's exact location
ers = [
    [h["name"], h["county"], round(h["pt"][0], 4), round(h["pt"][1], 4)]
    for h in json.load(open(os.path.join(DATA, "hospitals_geocoded.json")))
]
stroke_l12 = [
    [s["name"], s["city"], s["level"], round(s["pt"][0], 4), round(s["pt"][1], 4)]
    for s in json.load(open(os.path.join(DATA, "tx_dshs_stroke_centers.json")))["located"]
    if s["level_num"] <= 2
]

html_out = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Too Hot, Too Far: Live Heat-Risk &amp; Care-Access Lookup</title>
<style>
*{{box-sizing:border-box}}
body{{margin:0;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;background:#f4f5fa;color:#2b2f42;line-height:1.5}}
header{{background:linear-gradient(135deg,#2b2f42 0%,#6a4c93 55%,#e4572e 120%);color:#fff;padding:28px 24px 36px}}
.wrap{{max-width:1000px;margin:0 auto;padding:0 20px}} header .wrap{{padding:0;display:flex;justify-content:space-between;align-items:flex-end;flex-wrap:wrap;gap:12px}}
h1{{margin:0 0 4px;font-size:26px}} header p{{margin:0;opacity:.92;font-size:14px;max-width:650px}}
.nav a{{color:#fff;text-decoration:none;background:rgba(255,255,255,.18);padding:7px 13px;border-radius:8px;font-size:13px;margin-left:6px;display:inline-block}}
.controls{{background:#fff;border-radius:14px;padding:20px;box-shadow:0 6px 22px rgba(43,47,66,.09);margin:-20px auto 20px;display:flex;flex-direction:column;gap:12px}}
.row{{display:grid;grid-template-columns:1.2fr 1fr 1fr;gap:12px;align-items:end}}
.loc-bar{{display:flex;gap:8px;flex-wrap:wrap;align-items:center}}
label.lbl{{display:block;font-size:11.5px;font-weight:700;text-transform:uppercase;color:#6b7088;letter-spacing:.4px;margin-bottom:5px}}
select,input,button{{padding:9px 12px;border-radius:9px;border:1px solid #cfd4e4;font-size:14px;background:#fff;color:#2b2f42}}
select,input{{width:100%}}
button{{background:#6a4c93;color:#fff;border:none;font-weight:600;cursor:pointer;white-space:nowrap}}
button:hover{{background:#573b7d}}
button.gps{{background:#e4572e}} button.gps:hover{{background:#c9451f}}
.loc-status{{font-size:12.5px;color:#5b6075}}
.grid{{display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-bottom:18px}}
.card{{background:#fff;border-radius:14px;padding:20px;box-shadow:0 4px 16px rgba(43,47,66,.07)}}
.card h2{{margin:0 0 8px;font-size:17px}}
.temp-row{{display:flex;align-items:center;gap:14px;margin:10px 0}}
.temp-big{{font-size:40px;font-weight:800;line-height:1;color:#2b2f42}}
.pill{{display:inline-block;padding:4px 11px;border-radius:99px;font-size:12px;font-weight:700}}
.pill.low{{background:#e1f3e4;color:#236b32}} .pill.mod{{background:#fff4d6;color:#946200}} .pill.high{{background:#fdecea;color:#b82518}}
.kv{{display:grid;grid-template-columns:1fr auto;gap:6px 12px;font-size:13.5px;margin-top:8px}}
.kv span{{color:#6b7088}} .kv b{{text-align:right}}
.alert-box{{background:#fdecea;border-left:4px solid #d93829;padding:11px 14px;border-radius:8px;font-size:13px;margin-top:10px}}
.ok-box{{background:#eef7f0;border-left:4px solid #2e8540;padding:10px 14px;border-radius:8px;font-size:13px;margin-top:10px}}
.tip-list{{margin:8px 0 0 18px;padding:0;font-size:13.5px}} .tip-list li{{margin:5px 0}}
.src{{font-size:12px;color:#6b7088;margin-top:10px}}
footer{{color:#8a8fa3;font-size:12px;padding:6px 0 36px}}
@media(max-width:820px){{.row,.grid{{grid-template-columns:1fr}}}}
</style>
</head>
<body>
<header><div class="wrap">
  <div>
    <h1>Live Heat-Risk &amp; Care-Access Lookup</h1>
    <p>Uses your present location (or any US city/ZIP) for live National Weather Service forecasts and calculates driving time to the nearest ER and Texas DSHS stroke center.</p>
  </div>
  <div class="nav">
    <a href="index.html">Home</a>
    <a href="map.html">Map</a>
    <a href="report_expanded.html">24-County Report</a>
    <a href="solutions.html">Solutions</a>
  </div>
</div></header>

<div class="wrap">
  <div class="controls">
    <div class="row">
      <div>
        <label class="lbl">1. Present Location or US City / ZIP</label>
        <div class="loc-bar">
          <button id="use-gps" class="gps" type="button">Use My Location</button>
          <input id="place" type="text" placeholder="Or enter City, State or ZIP (e.g. Hillsboro, TX)" style="flex:1;min-width:160px">
          <button id="find-place" type="button">Go</button>
        </div>
      </div>
      <div>
        <label class="lbl" for="county">Or Jump to Study County</label>
        <select id="county"></select>
      </div>
      <div>
        <label class="lbl" for="cond">2. Neurological Condition</label>
        <select id="cond">
          <option value="epilepsy">Epilepsy / Seizures</option>
          <option value="ms">Multiple Sclerosis (MS)</option>
          <option value="migraine">Migraine</option>
          <option value="stroke">Stroke / High Blood Pressure</option>
          <option value="dementia">Dementia / Memory Loss</option>
          <option value="parkinsons">Parkinson's Disease</option>
        </select>
      </div>
    </div>
    <div id="loc-status" class="loc-status">Tip: Click <b>Use My Location</b> for live weather and nearest-hospital drive times from where you are right now.</div>
  </div>

  <div class="grid">
    <div class="card">
      <h2>Live National Weather Service Forecast</h2>
      <div id="wx"><p class="src">Waiting for location...</p></div>
    </div>
    <div class="card">
      <h2>Nearest Care &amp; County Baseline</h2>
      <div id="access"></div>
    </div>
  </div>

  <div class="card" style="margin-bottom:18px">
    <h2 id="cond-title">Condition-Specific Heat Guidance</h2>
    <div id="guidance"></div>
  </div>

  <footer>Live weather from National Weather Service (api.weather.gov). Texas ERs from CMS Care Compare; stroke centers from Texas DSHS; road routing via OSRM/OpenStreetMap. <b>Informational only, not medical advice. In an emergency, call 911.</b></footer>
</div>

<script>
const COUNTIES = {json.dumps(rows)};
const ERS = {json.dumps(ers)};
const STROKE_L12 = {json.dumps(stroke_l12)};
const GUIDANCE = {{
  epilepsy: {{
    title: "Epilepsy and Seizures: Heat Guidance",
    tips: [
      "Heat, dehydration, and electrolyte shifts can lower seizure thresholds.",
      "Stay in air conditioning during peak afternoon heat and drink water regularly.",
      "Store anti-seizure medications in a cool, dry place; high heat can degrade effectiveness.",
      "Use extra caution around open water or swimming pools."
    ],
    source: "Epilepsy Society UK (epilepsysociety.org.uk/how-stay-cool-heat); CDC Heat & Medications"
  }},
  ms: {{
    title: "Multiple Sclerosis (MS): Heat Guidance",
    tips: [
      "Even small rises in body temperature can trigger Uhthoff's phenomenon (temporary worsening of fatigue, vision, or weakness).",
      "Symptoms usually ease once cooled and do not indicate a true relapse; contact your doctor if new symptoms persist after cooling.",
      "Use cooling vests, chilled neck wraps, cold drinks, or cool showers, and schedule outdoor errands early or late."
    ],
    source: "National Multiple Sclerosis Society (nationalmssociety.org)"
  }},
  migraine: {{
    title: "Migraine: Heat Guidance",
    tips: [
      "High heat and humidity speed up fluid loss; dehydration is a primary migraine trigger.",
      "Hydrate proactively with water or electrolytes and limit alcohol or excess caffeine.",
      "Wear polarized sunglasses outdoors to reduce bright glare and avoid midday peak heat."
    ],
    source: "American Migraine Foundation (americanmigrainefoundation.org/resource-library/weather-and-migraine/)"
  }},
  stroke: {{
    title: "Stroke and High Blood Pressure: Heat Guidance",
    tips: [
      "Extreme heat forces the heart to pump harder while vasodilation and dehydration alter blood pressure and blood thickness.",
      "Avoid outdoor exertion between noon and 3 p.m. and review diuretics or blood-pressure drugs with your clinician.",
      "Call 911 immediately for confusion, slurred speech, facial drooping, arm weakness, fainting, or body temp >104°F."
    ],
    source: "American Heart Association / ASA; CDC Heat & Medications"
  }},
  dementia: {{
    title: "Dementia and Memory Loss: Heat Guidance",
    tips: [
      "Cognitive changes can mask thirst or overheating; offer cool water and water-rich foods (fruit, soups) throughout the day.",
      "Keep indoor spaces air-conditioned (fans alone are not enough above the 90s) and check on older relatives twice daily.",
      "Wandering outdoors during heat waves is dangerous; secure exits and keep medical ID on hand."
    ],
    source: "Alzheimer's Association (alz.org/help-support/caregiving/safety/wandering); CDC Older Adults"
  }},
  parkinsons: {{
    title: "Parkinson's Disease: Heat Guidance",
    tips: [
      "Autonomic changes and anticholinergic medications can impair sweating and blood pressure regulation, raising overheating and dizziness risk.",
      "Never stop prescribed medications on your own; ask your doctor or pharmacist for a summer heat-medication plan.",
      "Consider telehealth appointments during extreme-heat advisories if your clinic is far away."
    ],
    source: "Michael J. Fox Foundation (michaeljfox.org); CDC Heat & Medications"
  }}
}};

let curLat = 32.0484, curLon = -96.4769, curLabel = "Navarro County";
const sel = document.getElementById("county");
COUNTIES.forEach(c => {{
  const opt = document.createElement("option");
  opt.value = c.county;
  opt.textContent = `${{c.county}} County (${{c.type}})`;
  if (c.county === "Hill") opt.selected = true;
  sel.appendChild(opt);
}});

function havKm(aLat, aLon, bLat, bLon) {{
  const R = 6371, rad = d => d * Math.PI / 180;
  const dp = rad(bLat - aLat), dl = rad(bLon - aLon);
  const x = Math.sin(dp/2)**2 + Math.cos(rad(aLat))*Math.cos(rad(bLat))*Math.sin(dl/2)**2;
  return 2 * R * Math.asin(Math.sqrt(x));
}}

function heatBand(tempF, hasAlert) {{
  if (hasAlert || tempF >= 100) return ["high", "High Heat Risk (≥100°F or Active Advisory)"];
  if (tempF >= 90) return ["mod", "Moderate Heat Caution (90 to 99°F)"];
  return ["low", "Lower Heat Risk (<90°F)"];
}}

function renderGuidance() {{
  const g = GUIDANCE[document.getElementById("cond").value];
  document.getElementById("cond-title").textContent = g.title;
  document.getElementById("guidance").innerHTML = `
    <ul class="tip-list">${{g.tips.map(t => `<li>${{t}}</li>`).join("")}}</ul>
    <p class="src">Source: ${{g.source}}</p>`;
}}

async function routeDrive(lat1, lon1, lat2, lon2) {{
  try {{
    const r = await fetch(`https://router.project-osrm.org/route/v1/driving/${{lon1}},${{lat1}};${{lon2}},${{lat2}}?overview=false`);
    const j = await r.json();
    if (j.code === "Ok" && j.routes.length) {{
      return `${{Math.round(j.routes[0].duration / 60)}} min (${{(j.routes[0].distance / 1609.344).toFixed(1)}} mi)`;
    }}
  }} catch (e) {{}}
  const mi = havKm(lat1, lon1, lat2, lon2) * 0.621371;
  return `~${{mi.toFixed(1)}} mi straight-line`;
}}

async function updateForCoords(lat, lon, label, matchedCountyName) {{
  curLat = lat; curLon = lon; curLabel = label;
  document.getElementById("loc-status").innerHTML = `Showing live results for <b>${{label}}</b> (${{lat.toFixed(3)}}, ${{lon.toFixed(3)}}).`;

  // 1. Live NWS Forecast & Alerts
  const wxEl = document.getElementById("wx");
  wxEl.innerHTML = `<p class="src">Fetching live NWS forecast for ${{label}}...</p>`;
  fetch(`https://api.weather.gov/points/${{lat.toFixed(4)}},${{lon.toFixed(4)}}`)
    .then(r => r.json())
    .then(async pt => {{
      const [fc, al] = await Promise.all([
        fetch(pt.properties.forecast).then(r => r.json()),
        fetch(`https://api.weather.gov/alerts/active?point=${{lat.toFixed(4)}},${{lon.toFixed(4)}}`).then(r => r.json())
      ]);
      const periods = fc.properties.periods || [];
      const daytime = periods.find(p => p.isDaytime) || periods[0];
      const nextPeriods = periods.slice(0, 4);
      const heatAlerts = (al.features || []).filter(f => /heat|excessive/i.test(f.properties.event || ""));
      const [cls, bandLabel] = heatBand(daytime ? daytime.temperature : 0, heatAlerts.length > 0);
      const city = pt.properties.relativeLocation?.properties?.city;
      const st = pt.properties.relativeLocation?.properties?.state;
      const locNote = city && st ? ` (${{city}}, ${{st}})` : "";
      wxEl.innerHTML = `
        <span class="pill ${{cls}}">${{bandLabel}}</span>
        <div class="temp-row">
          <div class="temp-big">${{daytime ? daytime.temperature + "°" + daytime.temperatureUnit : "N/A"}}</div>
          <div><b>${{daytime ? daytime.name : "Forecast"}}${{locNote}}</b><br><span style="font-size:13px;color:#5b6075">${{daytime ? daytime.shortForecast : ""}}</span></div>
        </div>
        ${{heatAlerts.length
          ? `<div class="alert-box"><b>Active NWS Alert:</b> ${{heatAlerts.map(a => a.properties.headline || a.properties.event).join("<br>")}}</div>`
          : `<div class="ok-box">No active NWS heat advisories or warnings at this location right now.</div>`}}
        <div class="kv" style="margin-top:10px">
          ${{nextPeriods.map(p => `<span>${{p.name}}</span><b>${{p.temperature}}°${{p.temperatureUnit}} · ${{p.shortForecast}}</b>`).join("")}}
        </div>`;
    }})
    .catch(() => {{
      wxEl.innerHTML = `<div class="alert-box">Could not load live NWS forecast (api.weather.gov covers US locations).</div>`;
    }});

  // 2. Nearest Texas ER & DSHS Stroke Center + County Baseline (if in study area)
  const nearER = ERS.map(e => ({{e, d: havKm(lat, lon, e[2], e[3])}})).sort((a,b) => a.d - b.d)[0];
  const nearSt = STROKE_L12.map(s => ({{s, d: havKm(lat, lon, s[3], s[4])}})).sort((a,b) => a.d - b.d)[0];
  const nearStudy = COUNTIES.map(c => ({{c, d: havKm(lat, lon, c.lat, c.lon)}})).sort((a,b) => a.d - b.d)[0];
  const studyC = matchedCountyName
    ? COUNTIES.find(c => c.county === matchedCountyName)
    : (nearStudy.d <= 55 ? nearStudy.c : null);

  const accEl = document.getElementById("access");
  accEl.innerHTML = `<p class="src">Calculating driving time to nearest Texas ER and DSHS stroke center...</p>`;
  const inTXRange = nearER.d < 160;
  let erDrive = "Outside Texas dataset", stDrive = "Outside Texas dataset";
  if (inTXRange) {{
    [erDrive, stDrive] = await Promise.all([
      routeDrive(lat, lon, nearER.e[2], nearER.e[3]),
      routeDrive(lat, lon, nearSt.s[3], nearSt.s[4])
    ]);
  }}

  let html = `<div class="kv">`;
  if (inTXRange) {{
    html += `
      <span>Nearest Texas ER</span><b>${{nearER.e[0]}}</b>
      <span>Drive to nearest ER</span><b>${{erDrive}}</b>
      <span>Nearest DSHS L1/L2 Stroke Center</span><b>${{nearSt.s[0]}}</b>
      <span>Drive to Stroke Center</span><b>${{stDrive}}</b>`;
  }} else {{
    html += `<span>Nearest ER / Stroke routing</span><b>Available for Texas locations</b>`;
  }}
  if (studyC) {{
    html += `
      <span>Study County Baseline</span><b>${{studyC.county}} (${{studyC.score_total}} / 24, ${{studyC.type}})</b>
      <span>Historical &ge;100°F days/yr</span><b>${{studyC.days_over_100F}} days</b>
      <span>Residents age 65+ / No vehicle</span><b>${{studyC.pct_age_65_plus}}% / ${{studyC.pct_no_vehicle}}%</b>
      <span>Neurologists on record</span><b>${{Math.round(studyC.neurologists)}} (${{studyC.neurologists_per_100k}}/100k)</b>`;
  }}
  html += `</div><p class="src">Need a cooling center or ride? Dial <b>2-1-1</b> (or local 211) for open cooling centers and transit assistance.</p>`;
  accEl.innerHTML = html;
}}

document.getElementById("use-gps").addEventListener("click", () => {{
  if (!navigator.geolocation) {{
    document.getElementById("loc-status").textContent = "Geolocation is not supported by this browser. Enter a City/ZIP or pick a county.";
    return;
  }}
  document.getElementById("loc-status").textContent = "Requesting browser location permission...";
  navigator.geolocation.getCurrentPosition(
    pos => updateForCoords(pos.coords.latitude, pos.coords.longitude, "Your Current Location", null),
    () => {{ document.getElementById("loc-status").textContent = "Location permission declined. Enter a City/ZIP or pick a county below."; }},
    {{enableHighAccuracy: true, timeout: 10000}}
  );
}});

document.getElementById("find-place").addEventListener("click", async () => {{
  const q = document.getElementById("place").value.trim();
  if (!q) return;
  document.getElementById("loc-status").textContent = `Looking up "${{q}}"...`;
  try {{
    const r = await fetch("https://nominatim.openstreetmap.org/search?" + new URLSearchParams({{q, format: "json", limit: 1, countrycodes: "us"}}));
    const j = await r.json();
    if (!j.length) {{
      document.getElementById("loc-status").textContent = `Could not find "${{q}}" in the US. Try "City, TX" or a 5-digit ZIP.`;
      return;
    }}
    updateForCoords(parseFloat(j[0].lat), parseFloat(j[0].lon), j[0].display_name.split(",").slice(0,2).join(","), null);
  }} catch (e) {{
    document.getElementById("loc-status").textContent = "Lookup failed. Please check your internet connection.";
  }}
}});

sel.addEventListener("change", () => {{
  const c = COUNTIES.find(x => x.county === sel.value);
  updateForCoords(c.lat, c.lon, `${{c.county}} County center`, c.county);
}});
document.getElementById("cond").addEventListener("change", renderGuidance);

renderGuidance();
// Try GPS automatically on load if already granted, else default to Hill County
const hill = COUNTIES.find(x => x.county === "Hill");
if (navigator.permissions && navigator.permissions.query) {{
  navigator.permissions.query({{name: "geolocation"}}).then(p => {{
    if (p.state === "granted") {{
      navigator.geolocation.getCurrentPosition(
        pos => updateForCoords(pos.coords.latitude, pos.coords.longitude, "Your Current Location", null),
        () => updateForCoords(hill.lat, hill.lon, "Hill County center", "Hill")
      );
    }} else {{
      updateForCoords(hill.lat, hill.lon, "Hill County center", "Hill");
    }}
  }}).catch(() => updateForCoords(hill.lat, hill.lon, "Hill County center", "Hill"));
}} else {{
  updateForCoords(hill.lat, hill.lon, "Hill County center", "Hill");
}}
</script>
</body>
</html>
"""

open(os.path.join(HERE, "checker.html"), "w").write(html_out)
print("wrote checker.html")
