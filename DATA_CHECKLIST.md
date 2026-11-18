# Data Checklist (fill county_data.csv)

Counties: Dallas (urban), Navarro, Henderson, Hunt, Wise (rural).
Rules: real numbers only, same year for every county, write source + year in `source_notes`. Leave blank if not found.

| Column | Why it matters | Source | Steps |
|---|---|---|---|
| days_over_100F | Heat exposure | CDC Heat and Health Tracker (ephtracking.cdc.gov) or NOAA Climate Data Online (ncei.noaa.gov/cdo-web) | Count days with max temp >= 100F per year over 5-10 years, then average. |
| pct_age_65_plus | Older adults are more sensitive to heat | data.census.gov, ACS 5-year, profile DP05 | Read "65 years and over" percent. |
| pct_no_vehicle | Harder to reach care or cooling in a heat emergency | data.census.gov, table B25044 | No-vehicle households (owner + renter) / total households x 100. |
| stroke_rate | Brain-health burden (stand-in for neurological conditions) | CDC PLACES (cdc.gov/places), county level | Already filled: 2023 release, age-adjusted % of adults. |
| neurologists_per_100k | Access to brain care | HRSA AHRF (data.hrsa.gov) or Texas Medical Board lookup | Neurologists / county population x 100,000. |
| dist_nearest_ER_mi | Access to emergency care | Google Maps | Directions from the county's main town to the nearest ER, in miles. |

Then run: `python3 score.py county_data.csv`

Score groups: Heat (days over 100F), Vulnerability (age 65+, no vehicle), Access gap (neurologists, ER distance).
