# INT-05 - Internal Flow Catalog & Opportunity Radar

Internal Flow Catalog & Opportunity Radar analyzes Arya's historical flows and
turns them into product opportunities, operational risk priorities, customer
growth recommendations, and reusable marketplace tasks.

**Repository:** https://github.com/sedatbakla/RPA-InternalFlow-OppurtunityRadar

**Target Python version:** 3.13

## Features

- Validates and imports the flow catalog and capability taxonomy CSV files.
- Classifies flow names through keyword-to-capability matching.
- Calculates opportunity, product, business impact, risk, and priority scores.
- Shows portfolio metrics, Top 10 opportunities, and high-risk flows.
- Filters results by department, capability, opportunity score, and risk level.
- Recommends missing capabilities to customers based on existing adoption.
- Exports filtered scored results and marketplace-ready tasks as CSV files.
- Automatically prepares SQLite data when the application starts without a
  ready score table.
- Includes automated unit, pipeline, export, recommendation, and Streamlit
  interaction tests.

## Architecture

```text
CSV -> SQLite -> Classification -> Scoring -> Recommendations -> Dashboard/Export
```

| Component | Responsibility |
|---|---|
| `import_data.py` | Validates CSV inputs and imports flow and taxonomy tables |
| `database.py` | Provides project-local SQLite read and write helpers |
| `classifier.py` | Maps flow names to predicted capabilities |
| `scoring.py` | Calculates dashboard-ready scores and business levels |
| `recommendation.py` | Finds customer-capability gaps and reference flows |
| `export.py` | Builds scored and marketplace CSV outputs |
| `pipeline.py` | Coordinates import, classification, and scoring |
| `app.py` | Renders the Streamlit dashboard and active-filter exports |

The generated database is stored at `db/arya.db`. Database files are ignored by
Git and are rebuilt from the tracked CSV files when required.

## Data Inputs

### `data/flow_catalog_sample.csv`

The project catalog contains 110 flow records with these source columns:

| Column | Meaning |
|---|---|
| `Flow ID` | Unique integer flow identifier |
| `Flow Name` | Flow name used during keyword classification |
| `Customer` | Customer currently using the flow |
| `Department` | Department responsible for the flow |
| `Capability` | Ground-truth capability used to evaluate classification |
| `Run Count` | Monthly execution count |
| `Error Rate` | Error percentage used by risk scoring |
| `Manual Time` | Manual processing time before automation |
| `Transaction Volume` | Monthly transaction volume |

`Customer Count` is not stored in the source CSV. It is derived in memory and
in SQLite as the number of unique customers using each predicted capability.

### `data/task_capability_taxonomy.csv`

The taxonomy contains 40 keyword-to-capability mappings. Classification uses
case-insensitive keyword matching and stores the prediction, matched keyword,
original capability, and ground-truth comparison result.

## Scoring Model

All normalized values use a 0-100 scale.

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

The application reads an existing `flow_scores` table when it is ready. If the
database or score table is missing or incomplete, it automatically imports the
CSV files, classifies the flows, calculates scores, and creates the required
SQLite tables.

To rebuild every pipeline table manually:

```powershell
python pipeline.py
```

## Dashboard

The application provides four main views:

- **Top opportunities:** the ten highest opportunity scores in the active scope.
- **Risk monitoring:** flows with High or Critical risk levels.
- **Customer growth:** capabilities not currently used by each target customer,
  based on the strongest non-Critical reference flow.
- **All flows:** the complete filtered scored portfolio.

Sidebar filters update flow metrics, flow tables, and downloads. Customer growth
uses the complete portfolio as its usage baseline and has a separate customer
selector.

## Exports

- **Scored results:** all currently filtered scored flow columns.
- **Marketplace tasks:** task-oriented columns, customer reach, productization
  score, opportunity score, risk, priority, and marketplace status.

Both exports use Excel-compatible UTF-8 CSV encoding.

## Tests

Run the complete automated test suite from the repository root:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

The suite covers CSV validation, classification, score formulas, automatic
pipeline preparation, recommendations, exports, dashboard filters, empty-result
states, and download availability. Test databases are isolated from
`db/arya.db`.

## Streamlit Community Cloud

Use these settings when creating the application at
https://share.streamlit.io:

| Setting | Value |
|---|---|
| Repository | `sedatbakla/RPA-InternalFlow-OppurtunityRadar` |
| Branch | `sedat` |
| Entrypoint | `app.py` |
| Python | `3.13` |
| Secrets | None required |

**Live application:** Pending

**Demo video:** Pending

## Known Limitations

- Classification is deterministic keyword matching, not a machine learning
  model; the first taxonomy match wins.
- Max normalization makes scores relative to the current dataset.
- Risk uses a direct error-rate formula instead of max normalization.
- SQLite is local to the application instance and is regenerated from CSV when
  unavailable; it is not a shared production database.
- Authentication, authorization, and user-specific portfolios are not included.
- The marketplace export is a project-defined task format, not a certified
  external marketplace API contract.

## Team

| Name | Role | Responsibility |
|---|---|---|
| Merve Mızraklı | Software Engineer | Data processing, classification, and scoring |
| Sedat Bakla | Computer Engineer | Architecture, integration, dashboard, and technical demo |
| Beyza Öztürk | Industrial Engineer | Data design, scoring criteria, test scenarios, and documentation |
