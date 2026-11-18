"""Stage B: pick one NOAA station per county by a fixed rule, then average days >= 100F (2015-2024).

Rule: among stations with a TMAX record covering 2015-2024 that lie within 50 km of the county's
Census internal point, take the nearest one whose 2015-2024 record is at least 95% complete
and where every counted year has at least 90% of its days. Average days >= 100F over counted years.

Run: python3 scripts/expand_stage_b.py   (needs /tmp/ghcnd-stations.txt and /tmp/ghcnd-inventory.txt)
Output: data/stage_b_heat.json, data/noaa_tmax_expanded.csv
"""
import csv, json, math, os, subprocess, time, collections

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
UA = "heat-and-brain-student-project/1.0"
counties = json.load(open(os.path.join(DATA, "stage_a_counties.json")))


def hav_km(a, b):
    R = 6371.0
    p1, p2 = math.radians(a[0]), math.radians(b[0])
    dp, dl = p2 - p1, math.radians(b[1] - a[1])
    x = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * R * math.asin(math.sqrt(x))


names = {}
for line in open("/tmp/ghcnd-stations.txt"):
    names[line[0:11]] = (line[41:71].strip(), line[38:40])
inv = {}
for line in open("/tmp/ghcnd-inventory.txt"):
    if line[31:35] == "TMAX" and line[0:2] == "US" and names.get(line[0:11], ("", ""))[1] == "TX":
        if int(line[36:40]) <= 2015 and int(line[41:45]) >= 2024:
            inv[line[0:11]] = (float(line[12:20]), float(line[21:30]))
print("TX stations with TMAX 2015-2024 coverage:", len(inv))

cands = {}
for fips, c in counties.items():
    pt = (c["lat"], c["lon"])
    near = sorted(((hav_km(pt, ll), sid) for sid, ll in inv.items()), key=lambda x: x[0])
    cands[fips] = [(d, sid) for d, sid in near if d <= 50][:6]
    print(c["county"], [(round(d, 1), sid, names[sid][0]) for d, sid in cands[fips][:3]])
ids = sorted({sid for v in cands.values() for _, sid in v} | {"USW00013960", "USW00053912", "USC00410404", "USW00013926", "USW00053964"})
print("stations to download:", len(ids))

import gzip, io
obs = collections.defaultdict(lambda: collections.defaultdict(int))
hot = collections.defaultdict(lambda: collections.defaultdict(int))
out_rows = []
for k, sid in enumerate(ids):
    path = f"/tmp/ghcn_{sid}.csv.gz"
    if not os.path.exists(path):
        url = f"https://www.ncei.noaa.gov/pub/data/ghcn/daily/by_station/{sid}.csv.gz"
        for attempt in range(4):
            r = subprocess.run(["curl", "-s", "-f", "-m", "120", "-A", UA, "-o", path, url])
            if r.returncode == 0:
                break
            time.sleep(4)
        else:
            raise SystemExit("download failed for " + sid)
    for r in csv.reader(gzip.open(path, "rt")):
        # columns: id, date, element, value (tenths of C), measurement flag, quality flag, source flag, time
        if r[2] != "TMAX" or not ("2015" <= r[1][:4] <= "2024") or r[5] != "":
            continue
        f = round(int(r[3]) / 10 * 9 / 5 + 32)
        y = r[1][:4]
        obs[sid][y] += 1
        if f >= 100:
            hot[sid][y] += 1
        out_rows.append((sid, r[1], f))
    print("read", k + 1, "of", len(ids), sid, flush=True)

with open(os.path.join(DATA, "noaa_tmax_expanded.csv"), "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["STATION", "DATE", "TMAX_F"])
    w.writerows(out_rows)


def stats(sid):
    total = sum(obs[sid].values())
    good_years = [y for y in map(str, range(2015, 2025)) if obs[sid][y] >= 0.90 * (366 if int(y) % 4 == 0 else 365)]
    avg = sum(hot[sid][y] for y in good_years) / len(good_years) if good_years else None
    return total / 3653.0, good_years, avg


result = {}
for fips, c in counties.items():
    chosen = None
    for d, sid in cands[fips]:
        comp, gy, avg = stats(sid)
        if comp >= 0.95 and len(gy) >= 8:
            chosen = {"station": sid, "station_name": names[sid][0], "km_from_county_center": round(d, 1),
                      "completeness": round(comp, 3), "years_counted": len(gy), "avg_days_100F": round(avg, 1)}
            break
    result[fips] = chosen
    print(c["county"], chosen, flush=True)

json.dump(result, open(os.path.join(DATA, "stage_b_heat.json"), "w"), indent=1)
