"""Build checker.html — Live NWS Heat-Risk & Care-Access Lookup Tool for 24 North & East Texas counties.

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

html_out = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Live Heat-Risk &amp; Care-Access Lookup — North &amp; East Texas</title>
<style>
*{{box-sizing:border-box}}
body{{margin:0;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;background:#f4f5fa;color:#2b2f42;line-height:1.5}}
header{{background:linear-gradient(135deg,#2b2f42 0%,#6a4c93 55%,#e4572e 120%);color:#fff;padding:28px 24px 36px}}
.wrap{{max-width:980px;margin:0 auto;padding:0 20px}} header .wrap{{padding:0;display:flex;justify-content:space-between;align-items:flex-end;flex-wrap:wrap;gap:12px}}
h1{{margin:0 0 4px;font-size:26px}} header p{{margin:0;opacity:.92;font-size:14px;max-width:650px}}
.nav a{{color:#fff;text-decoration:none;background:rgba(255,255,255,.18);padding:7px 13px;border-radius:8px;font-size:13px;margin-left:6px;display:inline-block}}
.controls{{background:#fff;border-radius:14px;padding:20px;box-shadow:0 6px 22px rgba(43,47,66,.09);margin:-20px auto 20px;display:grid;grid-template-columns:1fr 1fr auto;gap:14px;align-items:end}}
label.lbl{{display:block;font-size:11.5px;font-weight:700;text-transform:uppercase;color:#6b7088;letter-spacing:.4px;margin-bottom:6px}}
select,button{{width:100%;padding:10px 12px;border-radius:9px;border:1px solid #cfd4e4;font-size:14.5px;background:#fff;color:#2b2f42}}
button{{background:#6a4c93;color:#fff;border:none;font-weight:600;cursor:pointer;padding:10px 20px}}
button:hover{{background:#573b7d}}
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
@media(max-width:780px){{.controls,.grid{{grid-template-columns:1fr}}}}
</style>
</head>
<body>
<header><div class="wrap">
  <div>
    <h1>Live Heat-Risk &amp; Care-Access Lookup</h1>
    <p>Combines live National Weather Service forecasts and alerts with each county's 24-county baseline risk and stroke-center drive times.</p>
  </div>
  <div class="nav">
    <a href="index.html">Home</a>
    <a href="map.html">Map</a>
    <a href="report_expanded.html">24-County Report</a>
  </div>
</div></header>

<div class="wrap">
  <div class="controls">
    <div>
      <label class="lbl" for="county">1. Select Texas County</label>
      <select id="county"></select>
    </div>
    <div>
      <label class="lbl" for="cond">2. Select Neurological Condition</label>
      <select id="cond">
        <option value="epilepsy">Epilepsy / Seizures</option>
        <option value="ms">Multiple Sclerosis (MS)</option>
        <option value="migraine">Migraine</option>
        <option value="stroke">Stroke / High Blood Pressure</option>
        <option value="dementia">Dementia / Memory Loss</option>
        <option value="parkinsons">Parkinson's Disease</option>
      </select>
    </div>
    <div><button id="go">Check Today's Risk</button></div>
  </div>

  <div class="grid">
    <div class="card">
      <h2>Live National Weather Service Forecast</h2>
      <div id="wx"><p class="src">Loading live forecast from api.weather.gov...</p></div>
    </div>
    <div class="card">
      <h2>County Care-Access &amp; Vulnerability Baseline</h2>
      <div id="access"></div>
    </div>
  </div>

  <div class="card" style="margin-bottom:18px">
    <h2 id="cond-title">Condition-Specific Heat Guidance</h2>
    <div id="guidance"></div>
  </div>

  <footer>Live weather from National Weather Service (api.weather.gov). County metrics from NOAA, US Census ACS, CDC PLACES, HRSA AHRF, CMS, and Texas DSHS. <b>Informational only — not medical advice. In an emergency, call 911.</b></footer>
</div>

<script>
const COUNTIES = {json.dumps(rows)};
const GUIDANCE = {{
  epilepsy: {{
    title: "Epilepsy & Seizures — Heat Guidance",
    tips: [
      "Heat, dehydration, and electrolyte shifts can lower seizure thresholds.",
      "Stay in air conditioning during peak afternoon heat and drink water regularly.",
      "Store anti-seizure medications in a cool, dry place—high heat can degrade effectiveness.",
      "Use extra caution around open water or swimming pools."
    ],
    source: "Epilepsy Society UK (epilepsysociety.org.uk/how-stay-cool-heat); CDC Heat & Medications"
  }},
  ms: {{
    title: "Multiple Sclerosis (MS) — Heat Guidance",
    tips: [
      "Even small rises in body temperature can trigger Uhthoff's phenomenon (temporary worsening of fatigue, vision, or weakness).",
      "Symptoms usually ease once cooled and do not indicate a true relapse—contact your doctor if new symptoms persist after cooling.",
      "Use cooling vests, chilled neck wraps, cold drinks, or cool showers, and schedule outdoor errands early or late."
    ],
    source: "National Multiple Sclerosis Society (nationalmssociety.org)"
  }},
  migraine: {{
    title: "Migraine — Heat Guidance",
    tips: [
      "High heat and humidity speed up fluid loss; dehydration is a primary migraine trigger.",
      "Hydrate proactively with water or electrolytes and limit alcohol or excess caffeine.",
      "Wear polarized sunglasses outdoors to reduce bright glare and avoid midday peak heat."
    ],
    source: "American Migraine Foundation (americanmigrainefoundation.org/resource-library/weather-and-migraine/)"
  }},
  stroke: {{
    title: "Stroke & High Blood Pressure — Heat Guidance",
    tips: [
      "Extreme heat forces the heart to pump harder while vasodilation and dehydration alter blood pressure and blood thickness.",
      "Avoid outdoor exertion between noon and 3 p.m. and review diuretics or blood-pressure drugs with your clinician.",
      "Call 911 immediately for confusion, slurred speech, facial drooping, arm weakness, fainting, or body temp >104°F."
    ],
    source: "American Heart Association / ASA; CDC Heat & Medications"
  }},
  dementia: {{
    title: "Dementia & Memory Loss — Heat Guidance",
    tips: [
      "Cognitive changes can mask thirst or overheating; offer cool water and water-rich foods (fruit, soups) throughout the day.",
      "Keep indoor spaces air-conditioned (fans alone are not enough above the 90s) and check on older relatives twice daily.",
      "Wandering outdoors during heat waves is dangerous—secure exits and keep medical ID on hand."
    ],
    source: "Alzheimer's Association (alz.org/help-support/caregiving/safety/wandering); CDC Older Adults"
  }},
  parkinsons: {{
    title: "Parkinson's Disease — Heat Guidance",
    tips: [
      "Autonomic changes and anticholinergic medications can impair sweating and blood pressure regulation, raising overheating and dizziness risk.",
      "Never stop prescribed medications on your own—ask your doctor or pharmacist for a summer heat-medication plan.",
      "Consider telehealth appointments during extreme-heat advisories if your neurology clinic is far away."
    ],
    source: "Michael J. Fox Foundation (michaeljfox.org); CDC Heat & Medications"
  }}
}};

const sel = document.getElementById("county");
COUNTIES.forEach(c => {{
  const opt = document.createElement("option");
  opt.value = c.county;
  opt.textContent = `${{c.county}} County (${{c.type}}) — Score ${{c.score_total}}/24`;
  if (c.county === "Hill") opt.selected = true;
  sel.appendChild(opt);
}});

function heatBand(tempF, hasAlert) {{
  if (hasAlert || tempF >= 100) return ["high", "High Heat Risk (≥100°F or Active Advisory)"];
  if (tempF >= 90) return ["mod", "Moderate Heat Caution (90–99°F)"];
  return ["low", "Lower Heat Risk (<90°F)"];
}}

function renderStatic() {{
  const c = COUNTIES.find(x => x.county === sel.value);
  const g = GUIDANCE[document.getElementById("cond").value];
  document.getElementById("access").innerHTML = `
    <div class="kv">
      <span>24-County Risk Score</span><b>${{c.score_total}} / 24 (${{c.type}})</b>
      <span>Historical ≥100°F days/yr</span><b>${{c.days_over_100F}} days</b>
      <span>Residents age 65+</span><b>${{c.pct_age_65_plus}}%</b>
      <span>No-vehicle households</span><b>${{c.pct_no_vehicle}}%</b>
      <span>Neurologists on record</span><b>${{Math.round(c.neurologists)}} (${{c.neurologists_per_100k}}/100k)</b>
      <span>Pop-weighted ER drive</span><b>${{c.er_drive_min_popw}} min (${{c.er_drive_mi_popw}} mi)</b>
      <span>Pop-weighted DSHS L1–L2 Stroke</span><b>${{c.stroke_l1_l2_min_popw}} min (${{c.stroke_l1_l2_mi_popw}} mi)</b>
      <span>Pop-weighted DSHS L1–L3 Stroke</span><b>${{c.stroke_l1_l3_min_popw}} min</b>
    </div>
    <p class="src">Need a cooling center or transit help in ${{c.county}} County? Dial <b>2-1-1</b> (Texas Health and Human Services).</p>`;

  document.getElementById("cond-title").textContent = g.title;
  document.getElementById("guidance").innerHTML = `
    <ul class="tip-list">${{g.tips.map(t => `<li>${{t}}</li>`).join("")}}</ul>
    <p class="src">Source: ${{g.source}}</p>`;
}}

async function loadWeather() {{
  const c = COUNTIES.find(x => x.county === sel.value);
  const wxEl = document.getElementById("wx");
  wxEl.innerHTML = `<p class="src">Fetching live NWS forecast for ${{c.county}} County (${{c.lat}}, ${{c.lon}})...</p>`;
  try {{
    const [ptRes, alRes] = await Promise.all([
      fetch(`https://api.weather.gov/points/${{c.lat}},${{c.lon}}`),
      fetch(`https://api.weather.gov/alerts/active?point=${{c.lat}},${{c.lon}}`)
    ]);
    const pt = await ptRes.json();
    const al = await alRes.json();
    const fcRes = await fetch(pt.properties.forecast);
    const fc = await fcRes.json();
    const periods = fc.properties.periods || [];
    const daytime = periods.find(p => p.isDaytime) || periods[0];
    const nextPeriods = periods.slice(0, 4);
    const heatAlerts = (al.features || []).filter(f => /heat|excessive/i.test(f.properties.event || ""));
    const [cls, label] = heatBand(daytime ? daytime.temperature : 0, heatAlerts.length > 0);
    wxEl.innerHTML = `
      <span class="pill ${{cls}}">${{label}}</span>
      <div class="temp-row">
        <div class="temp-big">${{daytime ? daytime.temperature + "°" + daytime.temperatureUnit : "N/A"}}</div>
        <div><b>${{daytime ? daytime.name : "Forecast"}}</b><br><span style="font-size:13px;color:#5b6075">${{daytime ? daytime.shortForecast : ""}}</span></div>
      </div>
      ${{heatAlerts.length
        ? `<div class="alert-box"><b>Active NWS Alert:</b> ${{heatAlerts.map(a => a.properties.headline || a.properties.event).join("<br>")}}</div>`
        : `<div class="ok-box">No active NWS heat advisories or warnings for ${{c.county}} County right now.</div>`}}
      <div class="kv" style="margin-top:10px">
        ${{nextPeriods.map(p => `<span>${{p.name}}</span><b>${{p.temperature}}°${{p.temperatureUnit}} · ${{p.shortForecast}}</b>`).join("")}}
      </div>`;
  }} catch (err) {{
    wxEl.innerHTML = `<div class="alert-box">Could not reach live NWS API (api.weather.gov). Check your internet connection or try again.</div>`;
  }}
}}

function refreshAll() {{ renderStatic(); loadWeather(); }}
document.getElementById("go").addEventListener("click", refreshAll);
sel.addEventListener("change", refreshAll);
document.getElementById("cond").addEventListener("change", renderStatic);
refreshAll();
</script>
</body>
</html>
"""

open(os.path.join(HERE, "checker.html"), "w").write(html_out)
print("wrote checker.html")
