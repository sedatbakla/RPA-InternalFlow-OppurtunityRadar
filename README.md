# INT-05 — Internal Flow Catalog & Opportunity Radar

A system that analyzes Arya's internal bot/flow history and turns it into new sales opportunities, maintenance priorities, and a catalog of reusable tasks.

**Deadline:** July 17 (Friday)
**Team:** [Merve Mızraklı] (Software Engineer) · [Sedat Bakla] (Computer Engineer) · [Beyza Öztürk] (Industrial Engineer)

---

## 1. What Problem Does This Solve?

Arya has a history of internal bots and flows, but this data is not organized. This project turns raw flow data into a scored, ranked list, so the team can quickly see:
- Which flows are **good opportunities** to turn into products
- Which flows are **risky** and need attention
- Which flows could be **sold to more customers**

---

## 2. System Overview

```
CSV files → SQLite database → Classification → Scoring → Dashboard
```

| Layer | Tool | Owner |
|---|---|---|
| Data storage | SQLite (`arya.db`) | [Merve] |
| Classification (keyword matching) | Python / pandas | [Merve] |
| Scoring | Python / pandas | [Merve] |
| Dashboard | Streamlit | [Sedat] |

---

## 3. Data Files

### `data/flow_catalog_sample.csv` (110 rows)
Sample flow records.

| Column | Meaning |
|---|---|
| Flow ID | Unique record number |
| Flow Name | Name of the bot/flow (used for classification) |
| Customer | Which customer uses it (`Internal` = used inside the company) |
| Department | Team that owns the flow |
| Capability | Business category (ground truth, used to test the classifier) |
| Run Count | How many times it runs per month |
| Error Rate | Error percentage |
| Manual Time | Minutes it used to take manually, before automation |
| Transaction Volume | Monthly transaction count |
| Customer Count | Number of different customers using this Capability |

### `data/task_capability_taxonomy.csv`
A keyword dictionary. If a keyword (e.g. "Invoice") appears in the Flow Name, the flow is classified under the matching Capability (e.g. "Finance").

### Demo files
`flow_catalog_demo.csv` (10 rows) and `task_capability_taxonomy_demo.csv` — small versions for quick testing and presentations.

---

## 4. How Classification Works

`classifier.py` checks each Flow Name against the keyword list in the taxonomy file. The first matching keyword decides the Capability. If no keyword matches, the flow is labeled `"Other"`.

The result is saved in a separate table called `flow_classification`.

> **Known issue:** The scoring step currently does not read from `flow_classification`. It uses the Capability column that already exists in the original CSV file. This works for testing (because we already know the "correct" answer), but in a real production case with new, unlabeled flows, this connection needs to be built. See Section 8.

---

## 5. How Scoring Works

Each flow gets several scores, all on a 0–100 scale (except where noted):

| Score | Formula | Meaning |
|---|---|---|
| Usage Score | Run Count ÷ max(Run Count) × 100 | How often the flow is used |
| Risk Score | Error Rate × 10 (capped at 100) | How risky/error-prone the flow is |
| Time Saving Score | Manual Time ÷ max(Manual Time) × 100 | How much manual work it saves |
| Resell Score | Customer Count ÷ max(Customer Count) × 100 | How reusable/sellable it is |
| Transaction (normalized) | Transaction Volume ÷ max(Transaction Volume) × 100 | Business volume, scaled |
| Product Score | Usage × 0.6 + Resell × 0.4 | How ready the flow is to become a product |
| Business Impact | Transaction × 0.6 + Time Saving × 0.4 | Overall business value |
| Criticality Score | Transaction × 0.5 + Usage × 0.5 | How important the flow is to watch |

**Final score:**
```
Opportunity Score = (Usage × 0.30) + (Transaction × 0.25) + (Product × 0.30) + (Time Saving × 0.15) − (Risk × 0.20)
```

The first four weights add up to 100%. Risk is subtracted separately, as a penalty — a flow that is very risky (many errors) should score lower, even if it looks good on the other metrics.

**Note on normalization:** most scores use "divide by the maximum value" (not min-max). Risk Score uses a different method (multiply by 10, then cap at 100). This means all scores are 0–100, but they are not all calculated the same way.

---

## 6. Setup and Run Order

Because the database file (`arya.db`) is not stored in GitHub (see `.gitignore`), you must build it yourself the first time:

```bash
# 1) Clone the repo
git clone [repo-link]
cd [project-folder]

# 2) Install requirements
pip install -r requirements.txt

# 3) Run these in order:
python import_csv.py     # creates arya.db and loads the CSV data
python classifier.py     # classifies flows, saves to flow_classification table
python scoring.py        # calculates scores, saves to flow_scores table

# 4) Start the dashboard
streamlit run dashboard.py
```

**You must run the scripts in this exact order** the first time, or later scripts will fail with a "no such table" error.

---

## 7. Required Features — Status

- [x] CSV import
- [x] Keyword-based classification
- [x] Scoring (multiple metrics + final Opportunity Score)
- [ ] Dashboard connected to real data *(currently shows sample/placeholder data only)*
- [ ] Top 10 opportunities view
- [ ] Risky flows view
- [ ] Customer expansion suggestions
- [ ] Export to marketplace format
- [ ] Connect classifier output to scoring (currently scoring uses the original CSV's Capability column, not the classifier's prediction)

---

## 8. Known Issues

1. **Dashboard not connected yet.** `dashboard.py` still uses sample data (`Project A`, `Project B`...) instead of reading from the `flow_scores` table.
2. **Classifier and scoring are not linked.** The classifier writes its prediction to `flow_classification`, but scoring still reads the Capability column from the raw `flows` table. This should be connected before the system is used on new, unlabeled data.
3. **Mixed normalization methods.** Most scores use max-normalization; Risk Score uses a different formula. This is documented above but could be made consistent in a future version.

---

## 9. Test Scenarios

### Basic checks
| # | Test | Expected result |
|---|---|---|
| T1 | Import `flow_catalog_sample.csv` | All 110 rows load without errors |
| T2 | Classify a flow named "Invoice Processing" | Should return Capability = "Finance" |
| T3 | Run scoring on all 110 rows | Every row gets an Opportunity Score, none are empty |

### Business logic checks
| # | Test | Why it matters |
|---|---|---|
| T4 | Compare two flows with the same Capability, one used by 10 customers and one used by 1 | The one with 10 customers should score higher on Resell Score |
| T5 | A flow with high Run Count and high Error Rate | Should appear near the top of the "risky flows" list once the dashboard is connected |

---

## 10. Team

| Name | Role | Responsibility |
|---|---|---|
| [Merve Mızraklı] | Software Engineer | Data processing, classification, scoring code |
| [Sedat Bakla] | Computer Engineer | Dashboard, system architecture, integration |
| [Beyza Öztürk] | Industrial Engineer | Data design, scoring logic, documentation |

---

## 11. Demo

*(demo video link goes here)*
