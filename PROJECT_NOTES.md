# Passion Project Notes (saved 2026-11-17)

## Who / Goal
- 10th grader (daughter), interests: medicine, activism, **neuroscience**.
- Independent **passion / research project** to build a strong college profile (not for a specific competition).
- She is **shy**: prefer data-only work, email over calls, written/poster/recorded formats.
- Wants something **unique and not done before** (uniqueness = new combination, local angle, or a new tool/score).

## Chosen direction
**Heat and the Brain:** map heat exposure against rural clinic/EMS access for people with neurological conditions (epilepsy, migraine, MS, stroke, dementia, Parkinson's) in rural counties near Dallas.

Research question: In rural counties near Dallas, which areas combine high heat exposure with low access to neurological and emergency care, and which patient groups are most at risk?

Comparison counties (to confirm): Navarro, Henderson, Hunt, Rains, Wise, Hood vs Dallas or Tarrant.

## Data sources (verify links)
- Heat: NOAA, CDC Heat and Health Tracker, NASA/Landsat
- Population: US Census ACS (age 65+, income, no vehicle, insurance)
- Health: CDC PLACES, CDC WONDER
- Providers/clinics: HRSA, Texas DSHS
- EMS stations: county sites, Texas DSHS
- Cooling centers: county/city sites

## Method
1. Fill county spreadsheet (county_data_template.csv).
2. Rank each measure, combine into a heat-risk and access-gap score (explain weights).
3. Map in QGIS or Google My Maps.
4. Case studies on the 1-2 highest-risk counties.
5. Recommendations: cooling centers, EMS coverage, telehealth, medication-safety info. Informational only, not medical advice.

## Timeline (about 10 weeks)
- Wk 1-2: sources, final question
- Wk 3-5: collect data
- Wk 6-7: score and map
- Wk 8-9: write-up and one-page resident guide
- Wk 10: mentor/teacher review

## Other ideas considered
- Stroke care access (distance to stroke-certified hospital), including WHO/World Bank comparison
- Language and stroke warning signs (bilingual FAST guide)
- Neurologist deserts, dementia/aging access, mental health access
- Concussion awareness for student athletes, brain-health explainers
- Rural clinic finder site (informational), OpenNeuro/EEG data practice

## Files in this folder
- heat_and_brain.docx / .html: project document with blank comparison tables (A: counties vs temperature, B: patient groups, C: conditions vs heat)
- county_data_template.csv: data template (no real data yet)

## Setup state (laptop)
- Installed: VS Code, Node, Python 3.12, uv, gh, Kotlin, Gradle, OpenJDK 21 and 27, IntelliJ IDEA (uninstall pending: `brew uninstall --cask intellij-idea`).
- MCP: `~/.gemini/config/mcp_config.json` has `google-workspace` (workspace-mcp via uvx, Docs/Sheets/Drive). Untested. Needs agy restart, then browser sign-in as test user.
- Todo: rotate OAuth secret (optional), download Antigravity app, `gh auth login`, Gmail as Chrome app.

## Next steps
1. Restart agy, confirm MCP server shows up and sign in.
2. Upload docx as a Google Doc and CSV as a Google Sheet (via MCP or drive.google.com).
3. Confirm HOSA event name/rules.
4. Search for existing studies on heat + neurological care access in Texas to check originality.
5. Start collecting real data for 4-6 counties.
