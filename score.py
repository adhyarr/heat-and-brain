"""Heat-risk and access-gap score for the Heat and the Brain project.

Usage: python3 score.py [county_data_expanded.csv | county_data.csv]

Method: each measure is ranked across counties (1 = lowest risk, N = highest).
Group scores are the average rank of their measures. The total is the average
of the three group scores (equal weights). Blank cells are skipped.
"""
import csv
import sys

# Default 5-county measures: measure -> (group, higher_value_means_more_risk)
MEASURES = {
    "days_over_100F": ("Heat", True),
    "pct_age_65_plus": ("Vulnerability", True),
    "pct_no_vehicle": ("Vulnerability", True),
    "stroke_rate": ("Vulnerability", True),
    "neurologists_per_100k": ("Access gap", False),  # fewer = more risk
    "dist_nearest_ER_mi": ("Access gap", True),
}

# Expanded 24-county measures (uses population-weighted tract drive times)
EXPANDED_MEASURES = {
    "days_over_100F": ("Heat", True),
    "pct_age_65_plus": ("Vulnerability", True),
    "pct_no_vehicle": ("Vulnerability", True),
    "stroke_rate": ("Vulnerability", True),
    "neurologists_per_100k": ("Access gap", False),
    "er_drive_min_popw": ("Access gap", True),
    "neuro_hub_drive_min_popw": ("Access gap", True),
}

GROUPS = ["Heat", "Vulnerability", "Access gap"]


def rank(values, higher_is_risk):
    """Average ranks (ties share), 1 = lowest risk. values: {county: float}."""
    items = sorted(values.items(), key=lambda kv: kv[1], reverse=not higher_is_risk)
    ranks, i = {}, 0
    while i < len(items):
        j = i
        while j + 1 < len(items) and items[j + 1][1] == items[i][1]:
            j += 1
        for k in range(i, j + 1):
            ranks[items[k][0]] = (i + j) / 2 + 1
        i = j + 1
    return ranks


def select_measures(rows):
    """Pick expanded or basic measure set based on columns present in the CSV."""
    if rows and "er_drive_min_popw" in rows[0] and "neuro_hub_drive_min_popw" in rows[0]:
        return EXPANDED_MEASURES
    return MEASURES


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else "county_data.csv"
    with open(path, newline="") as f:
        rows = list(csv.DictReader(f))

    measures = select_measures(rows)
    ranks = {}
    for m, (_, risky) in measures.items():
        vals = {}
        for r in rows:
            v = (r.get(m) or "").strip()
            if v:
                vals[r["county"]] = float(v)
        if len(vals) >= 2:
            ranks[m] = rank(vals, risky)
        else:
            print(f"Skipping {m}: need data for at least 2 counties")

    if not ranks:
        sys.exit("No data yet. Fill in county_data.csv first.")

    results = []
    for r in rows:
        c = r["county"]
        group_scores = {}
        for g in GROUPS:
            rs = [ranks[m][c] for m, (gg, _) in measures.items()
                  if gg == g and m in ranks and c in ranks[m]]
            if rs:
                group_scores[g] = sum(rs) / len(rs)
        if group_scores:
            total = sum(group_scores.values()) / len(group_scores)
            results.append((total, c, r["type"], group_scores))

    results.sort(reverse=True)
    print(f"\n{'County':<13}{'Type':<8}" + "".join(f"{g:<15}" for g in GROUPS) + "TOTAL")
    for total, c, t, gs in results:
        print(f"{c:<13}{t:<8}" + "".join(
            f"{gs[g]:<15.2f}" if g in gs else f"{'n/a':<15}" for g in GROUPS) + f"{total:.2f}")
    print(f"\nHighest risk: {results[0][1]}  (higher score = higher risk, max {len(rows)})")
    print("Missing cells are skipped, so compare only rows with similar completeness.")
    print("Association only, not causation. Not medical advice.")


if __name__ == "__main__":
    main()
