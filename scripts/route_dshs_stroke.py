"""Route all 1,885 Census tracts to nearest official Texas DSHS Stroke Center:
1) Comprehensive/Advanced (Level I-II) — specialized neuro-interventional / thrombectomy hubs
2) Any Stroke-Designated Center (Level I-III) — acute stroke stabilization & tPA

Output: data/stage_d_stroke.json and updates data/tract_access.csv
"""
import csv, json, math, os, subprocess, time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
UA = "heat-and-brain-student-project/1.0"

counties = json.load(open(os.path.join(DATA, "stage_a_counties.json")))
stroke_data = json.load(open(os.path.join(DATA, "tx_dshs_stroke_centers.json")))["located"]
comp_adv = [f for f in stroke_data if f["level_num"] <= 2]
primary_plus = [f for f in stroke_data if f["level_num"] <= 3]
print("DSHS Level I-II centers:", len(comp_adv), "| Level I-III centers:", len(primary_plus), flush=True)

tracts = list(csv.DictReader(open(os.path.join(DATA, "tracts_selected.csv"))))
for t in tracts:
    t["population"] = int(t["population"]); t["lat"] = float(t["lat"]); t["lon"] = float(t["lon"])
tracts = [t for t in tracts if t["population"] > 0]


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
    chosen = {}
    for i, t in enumerate(tr_chunk):
        chosen[i] = sorted(range(len(facilities)), key=lambda j: hav_km((t["lat"], t["lon"]), facilities[j]["pt"]))[:k]
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
                best = (d / 60.0, dist[i][pos[j]] / 1609.344, facilities[j]["name"], facilities[j]["level"])
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
        time.sleep(0.6)
    return res


r_comp = run(comp_adv, "STROKE_L1_L2")
r_any = run(primary_plus, "STROKE_L1_L3")

agg = {}
for t in tracts:
    key = (t["county_fips"], t["tract"])
    c12, c13 = r_comp[key], r_any[key]
    a = agg.setdefault(t["county_fips"], {"pop": 0, "s12_min": 0, "s12_mi": 0, "s13_min": 0, "s13_mi": 0,
                                           "s12_gt45": 0, "s12_gt60": 0})
    p = t["population"]
    a["pop"] += p
    a["s12_min"] += p * c12[0]; a["s12_mi"] += p * c12[1]
    a["s13_min"] += p * c13[0]; a["s13_mi"] += p * c13[1]
    a["s12_gt45"] += p * (c12[0] > 45)
    a["s12_gt60"] += p * (c12[0] > 60)

out = {}
for fips, a in agg.items():
    P = a["pop"]
    out[fips] = {
        "county": counties[fips]["county"],
        "stroke_l1_l2_min_popw": round(a["s12_min"] / P, 1),
        "stroke_l1_l2_mi_popw": round(a["s12_mi"] / P, 1),
        "pct_pop_stroke_l1_l2_over_45min": round(100 * a["s12_gt45"] / P, 1),
        "pct_pop_stroke_l1_l2_over_60min": round(100 * a["s12_gt60"] / P, 1),
        "stroke_l1_l3_min_popw": round(a["s13_min"] / P, 1),
        "stroke_l1_l3_mi_popw": round(a["s13_mi"] / P, 1),
    }
    print(out[fips], flush=True)

json.dump(out, open(os.path.join(DATA, "stage_d_stroke.json"), "w"), indent=1)
