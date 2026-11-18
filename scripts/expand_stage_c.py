"""Stage C: geocode Texas hospitals with emergency services (CMS Care Compare list) and define neurology hubs.

Includes Critical Access Hospitals (small rural hospitals), which the first pass left out.
Adds Medical City Decatur by hand (missing from the CMS list).
Output: data/hospitals_geocoded.json
Run: python3 scripts/expand_stage_c.py     (needs /tmp/cms_hosp.json and data/tx_neurologists_by_county.json)
"""
import json, os, subprocess, time, urllib.parse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
UA = "heat-and-brain-student-project/1.0"
CACHE = "/tmp/er_geocache.json"


def curl(url, retries=3):
    for i in range(retries):
        r = subprocess.run(["curl", "-s", "-f", "-m", "40", "-A", UA, url], capture_output=True)
        if r.returncode == 0 and r.stdout:
            return r.stdout.decode("utf8", "replace")
        time.sleep(2 * (i + 1))
    return None


cms = json.load(open("/tmp/cms_hosp.json"))["results"]
bad = ("HEART", "SURGICAL", "SURGERY", "CHILDREN", "LEGENT", "DIAGNOSTICS", "BEHAVIORAL", "ORTHOPED", "REHAB", "PSYCH")
cands = []
for x in cms:
    t = x["hospital_type"]
    if x["emergency_services"] == "Yes" and (t.startswith("Acute Care") or t.startswith("Critical Access")) \
            and not any(b in x["facility_name"].upper() for b in bad):
        cands.append({"name": x["facility_name"], "county": x["countyparish"], "type": t,
                      "addr": f'{x["address"]}, {x["citytown"]}, TX {x["zip_code"]}', "city": x["citytown"]})
cands.append({"name": "MEDICAL CITY DECATUR (added by hand; missing from CMS list)", "county": "WISE",
              "type": "Acute Care Hospitals", "addr": "609 Medical Center Dr, Decatur, TX 76234", "city": "DECATUR"})
print("candidate ER hospitals:", len(cands), flush=True)

cache = json.load(open(CACHE)) if os.path.exists(CACHE) else {}
for i, c in enumerate(cands):
    key = c["addr"]
    pt = None
    if key in cache:
        pt = cache[key]
    else:
        txt = curl("https://geocoding.geo.census.gov/geocoder/locations/onelineaddress?" +
                   urllib.parse.urlencode({"address": c["addr"], "benchmark": "Public_AR_Current", "format": "json"}))
        if txt:
            try:
                m = json.loads(txt)["result"]["addressMatches"]
                if m:
                    pt = [m[0]["coordinates"]["y"], m[0]["coordinates"]["x"]]
            except Exception:
                pass
        if pt is None:
            q = c["name"].title() + ", " + c["addr"].split(", ", 1)[1]
            txt = curl("https://nominatim.openstreetmap.org/search?" +
                       urllib.parse.urlencode({"q": q, "format": "json", "limit": 1, "countrycodes": "us"}))
            time.sleep(1.1)
            if txt:
                try:
                    j = json.loads(txt)
                    if j:
                        pt = [float(j[0]["lat"]), float(j[0]["lon"])]
                        c["geocoder"] = "nominatim"
                except Exception:
                    pass
        cache[key] = pt
        json.dump(cache, open(CACHE, "w"))
        time.sleep(0.15)
    c["pt"] = pt
    if (i + 1) % 25 == 0:
        print("geocoded", i + 1, "of", len(cands), flush=True)

ok = [c for c in cands if c["pt"]]
print("located:", len(ok), "of", len(cands))
print("not located:", [c["name"] for c in cands if not c["pt"]])

# keep only points inside Texas (rough box) to drop bad matches
ok = [c for c in ok if 25.5 <= c["pt"][0] <= 36.7 and -106.8 <= c["pt"][1] <= -93.4]

# neurology hubs: hospitals located in counties with >= 10 neurologists (AHRF 2023)
tx = json.load(open(os.path.join(DATA, "tx_neurologists_by_county.json")))
neuro_by_name = {v["county"].upper().replace(".", ""): v["neurologists"] for v in tx.values()}
for c in ok:
    c["county_neurologists"] = neuro_by_name.get(c["county"].upper().replace(".", ""), None)
json.dump(ok, open(os.path.join(DATA, "hospitals_geocoded.json"), "w"), indent=1)
unmatched = sorted({c["county"] for c in ok if c["county_neurologists"] is None})
print("hospital counties not matched to AHRF names:", unmatched)
print("hubs (>=10 neurologists):", sum(1 for c in ok if (c["county_neurologists"] or 0) >= 10))
