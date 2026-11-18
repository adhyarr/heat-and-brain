"""Parse Texas DSHS Stroke Facilities HTML (/tmp/dshs_stroke2.html) and geocode Level I & II
(Comprehensive & Advanced/Thrombectomy-Capable) stroke centers, reusing existing hospital geocodes.

Output: data/tx_dshs_stroke_centers.json
"""
import difflib, html, json, os, re, subprocess, time, urllib.parse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
UA = "heat-and-brain-student-project/1.0"
CACHE = "/tmp/er_geocache.json"

txt = open("/tmp/dshs_stroke2.html", encoding="utf8", errors="ignore").read()
tables = re.findall(r"<table.*?</table>", txt, re.S | re.I)
LEVELS = [
    (0, "Level I - Comprehensive"),
    (1, "Level II - Advanced"),
    (2, "Level III - Primary"),
    (3, "Level IV - Acute Stroke Ready"),
]

# Existing geocoded CMS hospitals for fast matching
cms_hosp = json.load(open(os.path.join(DATA, "hospitals_geocoded.json")))
by_zip = {}
for h in cms_hosp:
    z = h["addr"].split()[-1][:5]
    by_zip.setdefault(z, []).append(h)

cache = json.load(open(CACHE)) if os.path.exists(CACHE) else {}


def curl(url):
    for i in range(3):
        r = subprocess.run(["curl", "-s", "-f", "-m", "30", "-A", UA, url], capture_output=True)
        if r.returncode == 0 and r.stdout:
            return r.stdout.decode("utf8", "replace")
        time.sleep(2 * (i + 1))
    return None


facilities = []
for tidx, lvl in LEVELS:
    rows = re.findall(r"<tr.*?</tr>", tables[tidx], re.S | re.I)
    hdr = [re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", c))).strip().upper()
           for c in re.findall(r"<t[hd][^>]*>(.*?)</t[hd]>", rows[0], re.S | re.I)]
    for r in rows[1:]:
        cells = [re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", c))).strip()
                 for c in re.findall(r"<t[hd][^>]*>(.*?)</t[hd]>", r, re.S | re.I)]
        if not cells:
            continue
        d = dict(zip(hdr, cells))
        facilities.append({
            "name": d["FACILITY"],
            "level": lvl,
            "level_num": tidx + 1,
            "tsa": d.get("TSA", ""),
            "city": d.get("CITY (TX)", ""),
            "zip": d.get("ZIP", "")[:5],
            "expires": d.get("EXPIRATION DATE", ""),
        })

print("Total DSHS stroke facilities:", len(facilities))

# Geocode Level I & II (56 facilities) + any Level III in/near North & East Texas (TSA C, D, E, F, G, L, M)
target = [f for f in facilities if f["level_num"] <= 2 or f["tsa"] in ("C", "D", "E", "F", "G", "L", "M")]
print("Target to geocode (Level I-II statewide + Level III-IV in North/East/Central TX):", len(target))

matched_cms = 0
geocoded_nom = 0
failed = []
for f in target:
    pt = None
    cands = by_zip.get(f["zip"], [])
    if cands:
        best = max(cands, key=lambda h: difflib.SequenceMatcher(None, f["name"].upper(), h["name"].upper()).ratio())
        score = difflib.SequenceMatcher(None, f["name"].upper(), best["name"].upper()).ratio()
        if score >= 0.45 or len(cands) == 1:
            pt = best["pt"]
            matched_cms += 1
    if pt is None:
        key = f"DSHS|{f['name']}|{f['city']}|{f['zip']}"
        if key in cache:
            pt = cache[key]
        else:
            q = f"{f['name']}, {f['city']}, TX {f['zip']}"
            res = curl("https://nominatim.openstreetmap.org/search?" +
                       urllib.parse.urlencode({"q": q, "format": "json", "limit": 1, "countrycodes": "us"}))
            time.sleep(1.1)
            if res:
                j = json.loads(res)
                if j:
                    pt = [float(j[0]["lat"]), float(j[0]["lon"])]
            if pt is None:
                # fallback to city + zip centroid
                q2 = f"{f['city']}, TX {f['zip']}"
                res2 = curl("https://nominatim.openstreetmap.org/search?" +
                            urllib.parse.urlencode({"q": q2, "format": "json", "limit": 1, "countrycodes": "us"}))
                time.sleep(1.1)
                if res2:
                    j2 = json.loads(res2)
                    if j2:
                        pt = [float(j2[0]["lat"]), float(j2[0]["lon"])]
                        f["approx_zip"] = True
            cache[key] = pt
            json.dump(cache, open(CACHE, "w"))
        if pt:
            geocoded_nom += 1
        else:
            failed.append(f["name"])
    f["pt"] = pt

located = [f for f in target if f["pt"] and 25.5 <= f["pt"][0] <= 36.7 and -106.8 <= f["pt"][1] <= -93.4]
print(f"Located {len(located)} of {len(target)} (CMS matched={matched_cms}, Nominatim={geocoded_nom}, failed={len(failed)})")
if failed:
    print("Failed:", failed)

json.dump({"all_count": len(facilities), "located": located},
          open(os.path.join(DATA, "tx_dshs_stroke_centers.json"), "w"), indent=1)
