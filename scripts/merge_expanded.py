"""Merge Stage A (Census, CDC PLACES, HRSA), Stage B (NOAA heat), and Stage D (tract-weighted access)
into county_data_expanded.csv for all counties with complete data.
"""
import csv, json, os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")

a = json.load(open(os.path.join(DATA, "stage_a_counties.json")))
b = json.load(open(os.path.join(DATA, "stage_b_heat.json")))
d = json.load(open(os.path.join(DATA, "stage_d_access.json")))

URBAN_CORE = {"Dallas", "Tarrant", "Collin", "Denton"}  # DFW 4 core counties (>900k pop)

cols = [
    "county_fips", "county", "type", "population",
    "days_over_100F", "pct_age_65_plus", "pct_no_vehicle", "stroke_rate",
    "neurologists", "neurologists_per_100k",
    "er_drive_min_popw", "er_drive_mi_popw", "pct_pop_er_over_15min",
    "neuro_hub_drive_min_popw", "neuro_hub_drive_mi_popw", "pct_pop_hub_over_30min", "pct_pop_hub_over_45min",
    "source_notes",
]

rows = []
skipped = []
for fips, ca in sorted(a.items(), key=lambda kv: kv[1]["county"]):
    hb = b.get(fips)
    ad = d.get(fips)
    if not hb or not ad:
        skipped.append((ca["county"], bool(hb), bool(ad)))
        continue
    pop = ca["population"]
    neuro_rate = round(100000.0 * ca["neurologists"] / pop, 1)
    ctype = "urban" if ca["county"] in URBAN_CORE else "rural"
    notes = (
        f"heat: NOAA {hb['station']} ({hb['station_name']}, {hb['km_from_county_center']} km from center, "
        f"{hb['completeness']*100:.1f}% complete, {hb['years_counted']} yrs); "
        f"65+ & no-vehicle: Census ACS 2019-2023; stroke: CDC PLACES {ca['stroke_year']}; "
        f"neuro: HRSA AHRF 2023 ({ca['neurologists']} / {pop}); "
        f"drive: OSRM tract pop-weighted ({ad['tracts_used']} tracts, hub>=10 neuro)"
    )
    rows.append([
        fips, ca["county"], ctype, pop,
        hb["avg_days_100F"], ca["pct_age_65_plus"], ca["pct_no_vehicle"], ca["stroke_rate"],
        ca["neurologists"], neuro_rate,
        ad["er_drive_min_popw"], ad["er_drive_mi_popw"], ad["pct_pop_er_over_15min"],
        ad["neuro_hub_drive_min_popw"], ad["neuro_hub_drive_mi_popw"], ad["pct_pop_hub_over_30min"], ad["pct_pop_hub_over_45min"],
        notes,
    ])

out_path = os.path.join(ROOT, "county_data_expanded.csv")
with open(out_path, "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(cols)
    w.writerows(rows)

print(f"wrote {out_path} with {len(rows)} counties; skipped={skipped}")
