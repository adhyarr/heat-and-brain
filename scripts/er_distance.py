import csv, io, json, math, time, urllib.parse, urllib.request, zipfile

UA = {"User-Agent": "heat-and-brain-student-project/1.0"}


def get(url, binary=False, retries=3):
    import subprocess
    err = None
    for i in range(retries):
        r = subprocess.run(["curl", "-s", "-f", "-m", "40", "-A", UA["User-Agent"], url], capture_output=True)
        if r.returncode == 0 and r.stdout:
            return r.stdout if binary else r.stdout.decode("utf8")
        err = RuntimeError(f"curl exit {r.returncode}")
        time.sleep(2 * (i + 1))
    raise err


def hav(a, b):
    R = 3958.8
    p1, p2 = math.radians(a[0]), math.radians(b[0])
    dp, dl = p2 - p1, math.radians(b[1] - a[1])
    x = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * R * math.asin(math.sqrt(x))


# 1. county centroids (Census Gazetteer)
z = zipfile.ZipFile(io.BytesIO(get("https://www2.census.gov/geo/docs/maps-data/data/gazetteer/2023_Gazetteer/2023_Gaz_counties_national.zip", binary=True)))
name = [n for n in z.namelist() if n.endswith(".txt")][0]
rows = csv.reader(io.StringIO(z.read(name).decode("latin-1")), delimiter="\t")
hdr = [h.strip() for h in next(rows)]
cent = {}
for r in rows:
    d = dict(zip(hdr, r))
    if d["GEOID"] in ("48113", "48349", "48213", "48231", "48497"):
        cent[d["GEOID"]] = (float(d["INTPTLAT"]), float(d["INTPTLONG"].strip()))
print("centroids", cent)

origins = {
    "Dallas": {"centroid": cent["48113"], "town": ("Dallas downtown", (32.7767, -96.7970))},
    "Navarro": {"centroid": cent["48349"], "town": ("Corsicana", (32.0954, -96.4689))},
    "Henderson": {"centroid": cent["48213"], "town": ("Athens", (32.2049, -95.8555))},
    "Hunt": {"centroid": cent["48231"], "town": ("Greenville", (33.1384, -96.1108))},
    "Wise": {"centroid": cent["48497"], "town": ("Decatur", (33.2343, -97.5861))},
}

# 2. candidate ERs from CMS
cms = json.load(open("/tmp/cms_hosp.json"))["results"]
near = {"DALLAS", "COLLIN", "DENTON", "ELLIS", "KAUFMAN", "ROCKWALL", "PARKER", "NAVARRO", "HENDERSON", "HUNT", "WISE",
        "ANDERSON", "LIMESTONE", "FREESTONE", "HOPKINS", "FANNIN", "JACK", "COOKE", "MONTAGUE", "VAN ZANDT", "HILL",
        "JOHNSON", "TARRANT", "SMITH", "CHEROKEE", "DELTA", "RAINS", "HOOD"}
bad = ("HEART", "SURGICAL", "SURGERY", "CHILDREN", "LEGENT", "DIAGNOSTICS", "BEHAVIORAL", "ORTHOPED", "REHAB")
cands = []
for x in cms:
    if x["countyparish"] in near and x["emergency_services"] == "Yes" and "Acute Care" in x["hospital_type"] \
            and not any(b in x["facility_name"].upper() for b in bad):
        cands.append({"name": x["facility_name"], "addr": f'{x["address"]}, {x["citytown"]}, TX {x["zip_code"]}'})
cands.append({"name": "MEDICAL CITY DECATUR (added from medicalcityhealthcare.com; missing from CMS list)",
              "addr": "609 Medical Center Dr, Decatur, TX 76234"})
print("candidates", len(cands))

# 3. geocode (Census geocoder, Nominatim fallback), cached
import os
CACHE = "/tmp/er_geocache.json"
cache = json.load(open(CACHE)) if os.path.exists(CACHE) else {}
for c in cands:
    key = c["addr"]
    if key in cache:
        c["pt"] = tuple(cache[key]) if cache[key] else None
        continue
    pt = None
    try:
        url = ("https://geocoding.geo.census.gov/geocoder/locations/onelineaddress?" +
               urllib.parse.urlencode({"address": c["addr"], "benchmark": "Public_AR_Current", "format": "json"}))
        m = json.loads(get(url))["result"]["addressMatches"]
        if m:
            pt = (m[0]["coordinates"]["y"], m[0]["coordinates"]["x"])
    except Exception as e:
        print("census geocode error", c["name"], e)
    if pt is None:
        try:
            q = c["name"].title() + ", " + c["addr"].split(", ", 1)[1]
            url = "https://nominatim.openstreetmap.org/search?" + urllib.parse.urlencode({"q": q, "format": "json", "limit": 1, "countrycodes": "us"})
            j = json.loads(get(url))
            if j:
                pt = (float(j[0]["lat"]), float(j[0]["lon"]))
                print("nominatim ok", c["name"], pt)
            time.sleep(1.1)
        except Exception as e:
            print("nominatim error", c["name"], e)
    cache[key] = list(pt) if pt else None
    c["pt"] = pt
    json.dump(cache, open(CACHE, "w"))
    time.sleep(0.2)
ok = [c for c in cands if c["pt"]]
print("geocoded", len(ok), "of", len(cands))
print("still failed:", [c["name"] for c in cands if not c["pt"]], flush=True)


# 4. route to nearest 4 by straight line
def route(a, b):
    url = f"https://router.project-osrm.org/route/v1/driving/{a[1]},{a[0]};{b[1]},{b[0]}?overview=false"
    j = json.loads(get(url))
    r = j["routes"][0]
    return r["distance"] / 1609.344, r["duration"] / 60


out = {}
for county, o in origins.items():
    out[county] = {}
    for label, pt in (("centroid", o["centroid"]), (o["town"][0], o["town"][1])):
        near4 = sorted(ok, key=lambda c: hav(pt, c["pt"]))[:4]
        best = None
        for c in near4:
            try:
                mi, mn = route(pt, c["pt"])
            except Exception as e:
                print('route error', c['name'], repr(e), flush=True)
                continue
            time.sleep(0.5)
            if best is None or mi < best[0]:
                best = (mi, mn, c["name"], c["addr"])
        out[county][label] = best
        print(county, label, pt, "->", best)

json.dump(out, open("/tmp/er_distance_results.json", "w"), indent=1)
