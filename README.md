# Too Hot, Too Far: Extreme Heat and Medical Care Access in Texas

An independent public-health research project mapping where **extreme summer heat** overlaps with **older/vulnerable populations** and **limited access to emergency and medical care** across **24 North and East Texas counties** (4 urban DFW core counties and 20 surrounding rural/exurban counties) and **1,885 Census tracts**.

**Live Site:** https://adhyarr.github.io/heat-and-brain/

---

## How to Navigate

| Page | What's Inside | Link |
|---|---|---|
| **Project Home** | Overview, 5-step data flow, and key findings | [index.html](https://adhyarr.github.io/heat-and-brain/) |
| **Interactive County & Tract Map** | Color 24 counties by risk score, heat days, or drive time; toggle all 1,885 Census tracts, ERs, and neurology hubs | [map.html](https://adhyarr.github.io/heat-and-brain/map.html) |
| **Live Heat-Risk Lookup** | Pick a county + neurological condition to see live National Weather Service forecasts, active heat alerts, and care access | [checker.html](https://adhyarr.github.io/heat-and-brain/checker.html) |
| **24-County Visual Report** | Extreme-heat bar chart, ER vs. neurology-hub scatter plot, stacked risk scores, and full 24-county heatmap | [report_expanded.html](https://adhyarr.github.io/heat-and-brain/report_expanded.html) |
| **Actionable Solutions** | What Texas &amp; federal programs do today, the remaining gap, and how individuals &amp; policy can improve it | [solutions.html](https://adhyarr.github.io/heat-and-brain/solutions.html) |
| **1-Page Resident Heat-Safety Guide** | Printable safety handout covering 6 neurological conditions, CDC medication guidance, 911 signs, and 2-1-1 cooling help | [resident_guide.html](https://adhyarr.github.io/heat-and-brain/resident_guide.html) ([PDF](resident_guide.pdf)) |
| **5-County Pilot Report** | Initial 5-county comparison (Dallas, Navarro, Henderson, Hunt, Wise) | [report.html](https://adhyarr.github.io/heat-and-brain/report.html) |
| **About the Author** | Bio and interests of Adhya Rodda (medicine, neuroscience, philosophy, activism, debate) | [about.html](https://adhyarr.github.io/heat-and-brain/about.html) |
| **Full Research Write-Up** | Editable Google Doc with peer-reviewed background studies, verified condition table, and embedded charts | [Google Doc](https://docs.google.com/document/d/12Vvehx7DZWSoc6yMMl-tF_CJ7IqRWU_9fGOWhPVDKUw/edit?usp=drivesdk) |

---

## What the Project Does

1. **Measures Extreme Heat:** Uses 10 years of NOAA GHCN-Daily station records (2015–2024) to count average days per year reaching ≥100°F.
2. **Measures Population Vulnerability:** Pulls US Census ACS 5-year estimates (2019–2023) for residents age 65+ and households with no vehicle, plus CDC PLACES (2023) age-adjusted stroke prevalence.
3. **Measures Care Access (Population-Weighted):** Routes driving times via OSRM/OpenStreetMap from all **1,885 Census tract population centers** (2020 CenPop) to **327 Texas ER hospitals** (CMS Care Compare) and **152 neurology-hub hospitals** (counties with ≥10 neurologists in HRSA AHRF 2023).
4. **Computes a Transparent Score:** Ranks each county 1–24 on every measure, averages within **Heat**, **Vulnerability**, and **Access gap**, and combines the three groups with equal weights.

### Key Findings
- **Highest Combined Risk:** **Hill County** (19.89 / 24), followed by Erath (16.83), Navarro (16.72), Hood (16.22), and Hunt (14.78).
- **Rural vs. Urban Drive-Time Gap:** Rural residents drive an average of **19.3 min** to the nearest ER (vs. **9.1 min** in the urban core) and **50.7 min** to a neurology hub (vs. **9.1 min** in the urban core).
- **Neurologist Deserts:** **12 of the 20** rural counties have **0 neurologists** on record.

---

## Repository Structure & Reproducibility

```text
├── county_data_expanded.csv      # Final 24-county dataset (7 scoring measures + tract drive metrics)
├── score.py                      # Rank-based scoring script (run: python3 score.py county_data_expanded.csv)
├── build_map.py                  # Generates map.html from county_data_expanded.csv & data/tract_access.csv
├── build_report_expanded.py      # Generates report_expanded.html
├── scripts/
│   ├── expand_stage_a.py         # Census ACS, CDC PLACES, HRSA AHRF, and 2020 tract centroids
│   ├── expand_stage_b.py         # NOAA GHCN-Daily station selection & 100°F day counts
│   ├── expand_stage_c.py         # Texas ER hospital geocoding & neurology-hub tagging
│   ├── expand_stage_d.py         # OSRM tract-level driving times (ER & neurology hub)
│   └── merge_expanded.py         # Merges stages into county_data_expanded.csv
└── data/                         # Intermediate JSON/CSV outputs & GeoJSON county boundaries
```

---

## Disclaimer

*Informational and educational research only — not medical advice. Shows county-level association, not causation. In a medical emergency, call 911.*
