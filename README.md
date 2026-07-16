# INT-05 - Internal Flow Catalog & Opportunity Radar

Internal Flow Catalog & Opportunity Radar analyzes internal automation flows and
turns them into product opportunities, operational risk priorities, department
matches, customer growth recommendations, and reusable marketplace tasks.

**Repository:** https://github.com/sedatbakla/RPA-InternalFlow-OppurtunityRadar

**Target Python version:** 3.13

## Features

- Uses the bundled sample catalog or an uploaded CSV/XLSX flow catalog.
- Processes uploaded files entirely in memory without changing repository data.
- Validates file structure, required values, numeric values, encoding, size, and
  duplicate columns before scoring.
- Classifies flow names through the capability taxonomy.
- Matches predicted capabilities to target departments and flags mismatches.
- Calculates opportunity, productization, business impact, risk, and priority
  scores without changing the original scoring formulas.
- Explains productization and opportunity formulas inside the dashboard.
- Shows summary metrics, department opportunity charts, and risk distribution.
- Provides Top 10 opportunities, risk monitoring, customer growth, and all-flow
  views.
- Filters by source department, capability, department match, opportunity score,
  and risk level.
- Exports active scored results and marketplace-ready tasks as CSV files.
- Automatically prepares SQLite sample data when no ready score table exists.

## Architecture

The sample dataset uses the project-local SQLite pipeline:

```text
Sample CSV -> SQLite -> Classification -> Department Matching -> Scoring
           -> Recommendations -> Dashboard/Export
```

Uploaded datasets use the same business logic without database persistence:

```text
Uploaded CSV/XLSX -> In-memory Validation -> Classification
                  -> Department Matching -> Scoring
                  -> Recommendations -> Dashboard/Export
```

| Component | Responsibility |
|---|---|
| `data_contract.py` | Defines required source columns and capability-to-department rules |
| `dataset_upload.py` | Reads, validates, and secures uploaded CSV/XLSX content |
| `import_data.py` | Validates project CSV files and imports sample data into SQLite |
| `database.py` | Provides project-local SQLite read and write helpers |
| `classifier.py` | Maps flow names to capabilities and capabilities to departments |
| `scoring.py` | Calculates dashboard-ready scores and business levels |
| `recommendation.py` | Finds customer-capability gaps and reference flows |
| `export.py` | Builds scored and marketplace CSV outputs |
| `pipeline.py` | Coordinates persistent and in-memory processing pipelines |
| `app.py` | Manages data source state and renders the Streamlit dashboard |

The generated sample database is stored at `db/arya.db`. Database files are
ignored by Git and rebuilt from the tracked CSV files when required. Uploaded
files are never written to this database or to the repository.

## Setup

Clone the repository and switch to the project directory:

```powershell
git clone https://github.com/sedatbakla/RPA-InternalFlow-OppurtunityRadar.git
cd RPA-InternalFlow-OppurtunityRadar
git switch sedat
```

Create and activate a Python 3.13 virtual environment on Windows:

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Start the dashboard from the repository root:

```powershell
streamlit run app.py
```

To rebuild every sample-data pipeline table manually:

```powershell
python pipeline.py
```

## Data Sources

The sidebar starts with a **Data Source** section.

### Sample dataset

`Sample dataset` is selected by default. The application uses:

- `data/flow_catalog_sample.csv`
- `data/task_capability_taxonomy.csv`

If the database or score table is missing or incomplete, the application
rebuilds it automatically from these tracked files.

### Upload dataset

1. Select `Upload dataset` in the sidebar.
2. Use `Upload flow dataset` to select one CSV or XLSX file.
3. Review the file name, row count, column count, format, and validation status.
4. Use the dashboard normally after validation succeeds.
5. Select `Reset to sample dataset` to clear upload and filter state.

A new uploaded file clears selections that belonged to the previous dataset.
Page reruns reuse validated session data and a content-based cache. The file is
processed from bytes in memory and is never saved by the application.

## Upload Contract

Supported formats:

- UTF-8 or UTF-8 BOM CSV
- Comma-delimited CSV
- Semicolon-delimited CSV
- XLSX, using the first worksheet

Required source columns:

| Column | Type | Meaning |
|---|---|---|
| `Flow ID` | Whole number | Unique flow identifier |
| `Flow Name` | Text | Name used for keyword classification |
| `Customer` | Text | Customer currently using the flow |
| `Department` | Text | Current source department |
| `Capability` | Text | Ground-truth capability for evaluation |
| `Run Count` | Non-negative number | Monthly execution count |
| `Error Rate` | Non-negative number | Error percentage used in risk scoring |
| `Manual Time` | Non-negative number | Manual effort before automation |
| `Transaction Volume` | Non-negative number | Monthly transaction volume |

`Customer Count` must not be added to the source file. It is calculated after
classification as the unique customer count for each predicted capability.

Controlled header normalization removes surrounding whitespace and a BOM,
ignores letter case for known columns, and treats spaces and underscores as
equivalent. Unknown aliases are not guessed. Duplicate columns after
normalization are rejected.

Example CSV:

```csv
Flow ID,Flow Name,Customer,Department,Capability,Run Count,Error Rate,Manual Time,Transaction Volume
1,Invoice Processing,Alpha,Finance,Finance,100,1,30,1000
2,Recruitment Processing,Beta,HR,HR,80,2,20,800
```

Validation failures list the missing or invalid columns and stop scoring. Empty
files, files without data rows, inconsistent CSV rows, duplicate headers,
negative values, invalid numeric values, unreadable workbooks, and unsupported
formats do not render stale dashboard results.

Upload limits:

- Maximum uploaded file size: 10 MB
- Maximum data rows: 100,000
- Maximum expanded XLSX content: 50 MB
- XLSX processing: first worksheet only

## Classification And Department Matching

Flow names are matched case-insensitively against
`data/task_capability_taxonomy.csv`. The first matching keyword supplies the
predicted capability; unmatched names use `Other`.

Known capabilities map to target departments:

| Predicted capability | Matched department |
|---|---|
| Finance | Finance |
| Government Affairs | Government Affairs |
| HR | HR |
| IT | IT |
| Legal | Legal |
| Operations | Operations |
| Planning | Planning |
| Sales | Sales |

Each scored flow contains:

- `Department`: source department from the uploaded or sample catalog
- `Predicted Department`: department matched from predicted capability
- `Department Match`: `Matched`, `Review`, or `Source retained`

`Review` means that the matched department differs from the source department.
`Source retained` is used when a capability has no configured department rule.
Marketplace tasks use the predicted department when it is available.

## Scoring Model

All normalized values use a 0-100 scale and are recalculated for the active
dataset.

| Score | Formula |
|---|---|
| Usage | `Run Count / max(Run Count) * 100` |
| Risk | `min(Error Rate * 10, 100)` |
| Time Saving | `Manual Time / max(Manual Time) * 100` |
| Resell | `Customer Count / max(Customer Count) * 100` |
| Transaction | `Transaction Volume / max(Transaction Volume) * 100` |
| Product | `Usage * 0.60 + Resell * 0.40` |
| Business Impact | `Transaction * 0.60 + Time Saving * 0.40` |
| Criticality | `Transaction * 0.50 + Usage * 0.50` |
| Opportunity | `Usage * 0.30 + Transaction * 0.25 + Product * 0.30 + Time Saving * 0.15 - Risk * 0.20` |
| Priority | `Risk * 0.60 + Criticality * 0.40` |

Score levels:

| Level type | Thresholds |
|---|---|
| Risk | Low `<30`, Medium `30-59.999`, High `60-79.999`, Critical `>=80` |
| Opportunity | Low `<30`, Medium `30-59.999`, High `>=60` |
| Priority | Low `<30`, Medium `30-49.999`, High `50-69.999`, Critical `>=70` |

The same productization and opportunity formulas are shown in the dashboard's
`Scoring methodology` section.

### Marketplace Status Rule

Each exported task receives one of four statuses:
- `Backlog` (default)
- `Candidate` — Opportunity Level is Medium
- `Ready` — Opportunity Level is High
- `Risk Review` — overrides the above when Risk Level is Critical

Note: High-risk (but not Critical) flows are not automatically flagged for review, even at a high opportunity score. See Known Limitations.

## Dashboard

Summary metrics are calculated from the active filtered dataset:

- Visible flows
- Average opportunity
- High opportunities
- Critical risks
- Department match rate

Graphical views show:

- Average opportunity score by matched department
- Flow count by risk level

Dashboard tabs:

- **Top opportunities:** the ten highest opportunity scores in active filters
- **Risk monitoring:** High and Critical risk flows
- **Customer growth:** missing customer capabilities based on the strongest
  non-Critical reference flow
- **All flows:** the complete filtered scored portfolio

All flow tables include source and predicted department fields. Empty filter
results show clear messages and disable both export buttons.

## Exports

Both exports use the same active, filtered, scored DataFrame displayed by the
dashboard.

- **Scored results:** complete calculated flow results
- **Marketplace tasks:** task name/type, matched department, customer reach,
  productization, opportunity, risk, priority, and marketplace status

Sample-data filenames remain:

- `internalflow_scored_results.csv`
- `internalflow_marketplace_tasks.csv`

Uploaded filenames are based on a sanitized source stem, for example:

- `company_flows_scored.csv`
- `company_flows_marketplace_tasks.csv`

CSV downloads use Excel-compatible UTF-8 BOM encoding.

## Tests

Run the complete automated test suite from the repository root:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

The suite covers sample CSV validation, uploaded CSV/XLSX parsing, delimiter and
header normalization, invalid schemas and numeric values, classification,
department matching, score formulas, SQLite pipeline recovery, recommendations,
both exports, dynamic filters, zero-result views, upload replacement, and reset
to the sample dataset. Test databases are isolated from `db/arya.db`.

## Streamlit Community Cloud

Use these deployment settings:

| Setting | Value |
|---|---|
| Repository | `sedatbakla/RPA-InternalFlow-OppurtunityRadar` |
| Branch | `sedat` |
| Entrypoint | `app.py` |
| Python | `3.13` |
| Secrets | None required |

**Live application:** [https://flow-radar.streamlit.app](https://flow-radar.streamlit.app)

**Demo video:** Pending

## Known Limitations

- Classification uses deterministic first-keyword matching, not machine learning.
- Capability-to-department matching uses the explicit project mapping above.
- Max normalization makes scores relative to the active dataset.
- Risk uses a direct error-rate formula instead of max normalization.
- XLSX uploads read only the first worksheet.
- SQLite is local to the application instance and is used only for sample data.
- Authentication, authorization, and user-specific portfolios are not included.
- Marketplace export is a project-defined format, not a certified external API.
- Marketplace status only escalates to "Risk Review" when Risk Level is Critical. A flow with High (but not Critical) risk and a high opportunity score can still be marked "Ready." The team discussed raising this threshold to include High risk but kept the original rule for this submission.
## Team

| Name | Role | Responsibility |
|---|---|---|
| Merve Mızraklı | Software Engineer | Data processing, classification, and scoring |
| Sedat Bakla | Computer Engineer | Architecture, integration, dashboard, and technical demo |
| Beyza Öztürk | Industrial Engineer | Data design, scoring criteria, test scenarios, and documentation |
