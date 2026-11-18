"""Stage A: choose counties, pull Census / CDC PLACES / HRSA AHRF values and Census tract centroids.

Run:  CENSUS_KEY=your_key python3 scripts/expand_stage_a.py
Outputs: data/stage_a_counties.json, data/tracts_selected.csv
"""
import csv, io, json, os, subprocess, sys, time, zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA = os.path.join(ROOT, "data")
UA = "heat-and-brain-student-project/1.0"
KEY = os.environ.get("CENSUS_KEY", "")

# FIPS -> expected name (checked against Census Gazetteer so a wrong code stops the script)
COUNTIES = {
    "48113": "Dallas", "48439": "Tarrant", "48085": "Collin", "48121": "Denton", "48139": "Ellis",
    "48257": "Kaufman", "48397": "Rockwall", "48251": "Johnson", "48367": "Parker", "48221": "Hood",
    "48497": "Wise", "48349": "Navarro", "48213": "Henderson", "48231": "Hunt", "48467": "Van Zandt",
    "48379": "Rains", "48223": "Hopkins", "48147": "Fannin", "48181": "Grayson", "48097": "Cooke",
    "48161": "Freestone", "48001": "Anderson", "48293": "Limestone", "48217": "Hill", "48143": "Erath",
}


def curl(url, binary=False, retries=4):
    err = None
    for i in range(retries):
        r = subprocess.run(["curl", "-s", "-f", "-m", "90", "-A", UA, url], capture_output=True)
        if r.returncode == 0 and r.stdout:
            return r.stdout if binary else r.stdout.decode("utf8", "replace")
        err = RuntimeError(f"curl exit {r.returncode} for {url[:90]}")
        time.sleep(3 * (i + 1))
    raise err


# 1. Gazetteer centroids + name check
z = zipfile.ZipFile(io.BytesIO(curl("https://www2.census.gov/geo/docs/maps-data/data/gazetteer/2023_Gazetteer/2023_Gaz_counties_national.zip", True)))
name = [n for n in z.namelist() if n.endswith(".txt")][0]
rd = csv.reader(io.StringIO(z.read(name).decode("latin-1")), delimiter="\t")
hdr = [h.strip() for h in next(rd)]
out = {}
for r in rd:
    d = dict(zip(hdr, r))
    if d["GEOID"] in COUNTIES:
        nm = d["NAME"].replace(" County", "").strip()
        assert nm == COUNTIES[d["GEOID"]], (d["GEOID"], nm, COUNTIES[d["GEOID"]])
        out[d["GEOID"]] = {"county": nm, "lat": float(d["INTPTLAT"]), "lon": float(d["INTPTLONG"].strip())}
assert len(out) == len(COUNTIES), "missing counties"
print("gazetteer ok", len(out))

# 2. Census ACS profile (all TX counties, one call), retry because the key activates slowly
url = ("https://api.census.gov/data/2023/acs/acs5/profile?get=NAME,DP05_0024PE,DP04_0058PE"
       "&for=county:*&in=state:48&key=" + KEY)
acs = None
for i in range(8):
    try:
        acs = json.loads(curl(url, retries=1))
        break
    except Exception as e:
        print("census retry", i, e)
        time.sleep(4)
assert acs, "Census API failed"
h = acs[0]
for row in acs[1:]:
    fips = row[h.index("state")] + row[h.index("county")]
    if fips in out:
        out[fips]["pct_age_65_plus"] = float(row[h.index("DP05_0024PE")])
        out[fips]["pct_no_vehicle"] = float(row[h.index("DP04_0058PE")])
print("census ok")

# 3. CDC PLACES stroke (age-adjusted), by county FIPS
import urllib.parse
q = urllib.parse.urlencode({
    "stateabbr": "TX", "measureid": "STROKE", "data_value_type": "Age-adjusted prevalence",
    "$select": "locationid,locationname,data_value,year", "$limit": "400"})
places = json.loads(curl("https://data.cdc.gov/resource/swc5-untb.json?" + q))
for p in places:
    if p["locationid"] in out:
        out[p["locationid"]]["stroke_rate"] = float(p["data_value"])
        out[p["locationid"]]["stroke_year"] = p["year"]
print("places ok", sum(1 for v in out.values() if "stroke_rate" in v))

# 4. HRSA AHRF (local file already downloaded)
ahrf = "/tmp/ahrf/NCHWA-2024-2025+AHRF+COUNTY+CSV/AHRF2025.csv"
for r in csv.DictReader(open(ahrf, encoding="latin-1")):
    if r["fips_st_cnty"] in out:
        out[r["fips_st_cnty"]]["neurologists"] = int(float(r["tot_md_do_neuro_23"]))
        out[r["fips_st_cnty"]]["population"] = int(float(r["popn_23"]))
# all-Texas neurologist counts for hub selection
tx = {}
for r in csv.DictReader(open(ahrf, encoding="latin-1")):
    if r["fips_st"] == "48":
        try:
            tx[r["fips_st_cnty"]] = {"county": r["cnty_name"], "neurologists": int(float(r["tot_md_do_neuro_23"] or 0))}
        except ValueError:
            pass
json.dump(tx, open(os.path.join(DATA, "tx_neurologists_by_county.json"), "w"))
print("ahrf ok")

for fips, v in out.items():
    missing = [k for k in ("pct_age_65_plus", "pct_no_vehicle", "stroke_rate", "neurologists", "population") if k not in v]
    if missing:
        print("MISSING", v["county"], missing)

json.dump(out, open(os.path.join(DATA, "stage_a_counties.json"), "w"), indent=1)

# 5. Census tract population-weighted centroids (2020)
txt = curl("https://www2.census.gov/geo/docs/reference/cenpop2020/tract/CenPop2020_Mean_TR48.txt")
rd = csv.DictReader(io.StringIO(txt.lstrip("\ufeff")))
n = 0
with open(os.path.join(DATA, "tracts_selected.csv"), "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["county_fips", "tract", "population", "lat", "lon"])
    for r in rd:
        fips = "48" + r["COUNTYFP"]
        if fips in COUNTIES:
            w.writerow([fips, r["TRACTCE"], r["POPULATION"], r["LATITUDE"], r["LONGITUDE"]])
            n += 1
print("tracts", n)
