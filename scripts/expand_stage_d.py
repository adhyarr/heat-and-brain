"""Stage D: population-weighted driving time/distance from Census tract population centers
to (1) the nearest ER hospital and (2) the nearest neurology hub, using OSRM on OpenStreetMap.

Tract population centers: Census 2020 CenPop (data/tracts_selected.csv).
Neurology hub = ER hospital in a county with >= HUB_MIN neurologists (HRSA AHRF 2023).
Routing: OSRM public demo server "table" service, batched; straight-line prefilter picks the nearest
few candidates per tract, and the shortest drive among them is used.

Run: python3 scripts/expand_stage_d.py [HUB_MIN]
Output: data/stage_d_access.json, data/tract_access.csv
"""
import csv, json, math, os, subprocess, sys, time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
UA = "heat-and-brain-student-project/1.0"
HUB_MIN = int(sys.argv[1]) if len(sys.argv) > 1 else 10
counties = json.load(open(os.path.join(DATA, "stage_a_counties.json")))
hosp = json.load(open(os.path.join(DATA, "hospitals_geocoded.json")))
tracts = list(csv.DictReader(open(os.path.join(DATA, "tracts_selected.csv"))))
for t in tracts:
    t["population"] = int(t["population"]); t["lat"] = float(t["lat"]); t["lon"] = float(t["lon"])
tracts = [t for t in tracts if t["population"] > 0]
print("tracts with people:", len(tracts), "ER hospitals:", len(hosp), flush=True)


def hav_km(a, b):
    R = 6371.0
    p1, p2 = math.radians(a[0]), math.radians(b[0])
    dp, dl = p2 - p1, math.radians(b[1] - a[1])
    x = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * R * math.asin(math.sqrt(x))


def table(src, dst):
    coords = ";".join(f"{p[1]:.5f},{p[0]:.5f}" for p in src + dst)
    s = ";".join(map(str, range(len(src))))
    d = ";".join(map(str, range(len(src), len(src) + len(dst))))
    url = (f"https://router.project-osrm.org/table/v1/driving/{coords}?sources={s}&destinations={d}"
           "&annotations=duration,distance")
    for attempt in range(5):
        r = subprocess.run(["curl", "-s", "-m", "90", "-A", UA, url], capture_output=True)
        try:
            j = json.loads(r.stdout.decode())
            if j.get("code") == "Ok":
                return j["durations"], j["distances"]
            if j.get("code") in ("TooBig", "InvalidQuery"):
                raise ValueError(j)
        except ValueError:
            raise
        except Exception:
            pass
        time.sleep(3 * (attempt + 1))
    raise RuntimeError("table request failed")


def nearest_drive(tr_chunk, facilities, k):
    """Return per-tract (minutes, miles, facility name) using shortest drive among k nearest by straight line."""
    chosen = {}
    for i, t in enumerate(tr_chunk):
        near = sorted(range(len(facilities)), key=lambda j: hav_km((t["lat"], t["lon"]), facilities[j]["pt"]))[:k]
        chosen[i] = near
    union = sorted({j for v in chosen.values() for j in v})
    dst = [facilities[j]["pt"] for j in union]
    dur, dist = table([(t["lat"], t["lon"]) for t in tr_chunk], dst)
    pos = {j: n for n, j in enumerate(union)}
    out = []
    for i in range(len(tr_chunk)):
        best = None
        for j in chosen[i]:
            d = dur[i][pos[j]]
            if d is None:
                continue
            if best is None or d < best[0]:
                best = (d / 60.0, dist[i][pos[j]] / 1609.344, facilities[j]["name"])
        out.append(best)
    return out


def run(facilities, label):
    res = {}
    CH = 40
    for c0 in range(0, len(tracts), CH):
        chunk = tracts[c0:c0 + CH]
        k = 5
        while True:
            try:
                got = nearest_drive(chunk, facilities, k)
                break
            except ValueError:
                k -= 1
                if k < 1:
                    raise
        for t, g in zip(chunk, got):
            res[(t["county_fips"], t["tract"])] = g
        print(label, min(c0 + CH, len(tracts)), "of", len(tracts), flush=True)
        time.sleep(0.7)
    return res


er = run(hosp, "ER")
hubs = [h for h in hosp if (h.get("county_neurologists") or 0) >= HUB_MIN]
print("hubs:", len(hubs), flush=True)
hb = run(hubs, "HUB")

rows = []
agg = {}
for t in tracts:
    key = (t["county_fips"], t["tract"])
    e, h = er[key], hb[key]
    rows.append([t["county_fips"], t["tract"], t["population"], t["lat"], t["lon"],
                 round(e[0], 2) if e else "", round(e[1], 2) if e else "", e[2] if e else "",
                 round(h[0], 2) if h else "", round(h[1], 2) if h else "", h[2] if h else ""])
    a = agg.setdefault(t["county_fips"], {"pop": 0, "er_min": 0, "er_mi": 0, "hub_min": 0, "hub_mi": 0,
                                           "er_gt15": 0, "hub_gt30": 0, "hub_gt45": 0, "n": 0, "missing": 0})
    if not e or not h:
        a["missing"] += 1
        continue
    p = t["population"]
    a["pop"] += p; a["n"] += 1
    a["er_min"] += p * e[0]; a["er_mi"] += p * e[1]
    a["hub_min"] += p * h[0]; a["hub_mi"] += p * h[1]
    a["er_gt15"] += p * (e[0] > 15)
    a["hub_gt30"] += p * (h[0] > 30)
    a["hub_gt45"] += p * (h[0] > 45)

with open(os.path.join(DATA, "tract_access.csv"), "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["county_fips", "tract", "population", "lat", "lon", "er_min", "er_mi", "er_name",
                "hub_min", "hub_mi", "hub_name"])
    w.writerows(rows)

out = {}
for fips, a in agg.items():
    P = a["pop"]
    out[fips] = {"county": counties[fips]["county"], "tracts_used": a["n"], "tracts_missing": a["missing"],
                 "er_drive_min_popw": round(a["er_min"] / P, 1), "er_drive_mi_popw": round(a["er_mi"] / P, 1),
                 "pct_pop_er_over_15min": round(100 * a["er_gt15"] / P, 1),
                 "neuro_hub_drive_min_popw": round(a["hub_min"] / P, 1),
                 "neuro_hub_drive_mi_popw": round(a["hub_mi"] / P, 1),
                 "pct_pop_hub_over_30min": round(100 * a["hub_gt30"] / P, 1),
                 "pct_pop_hub_over_45min": round(100 * a["hub_gt45"] / P, 1), "hub_min_neurologists": HUB_MIN}
    print(out[fips], flush=True)
json.dump(out, open(os.path.join(DATA, "stage_d_access.json"), "w"), indent=1)
