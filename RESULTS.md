# Evaluation Results

The 20-question evaluation sheet is prepared, but the live end-to-end Vanna/Gemini run still requires a valid `GOOGLE_API_KEY` in `.env`. In this workspace, database creation and memory seeding can be verified locally without the key; the live NL→SQL evaluation should be executed after the key is configured.

## Score

- Total score: Pending live Gemini-backed run / 20

## Questions

| # | Question | Generated SQL | Correct? | Result summary |
|---|---|---|---|---|
| 1 | How many patients do we have? | Pending live run | Pending | Pending live run |
| 2 | List all doctors and their specializations | Pending live run | Pending | Pending live run |
| 3 | Show me appointments for last month | Pending live run | Pending | Pending live run |
| 4 | Which doctor has the most appointments? | Pending live run | Pending | Pending live run |
| 5 | What is the total revenue? | Pending live run | Pending | Pending live run |
| 6 | Show revenue by doctor | Pending live run | Pending | Pending live run |
| 7 | How many cancelled appointments last quarter? | Pending live run | Pending | Pending live run |
| 8 | Top 5 patients by spending | Pending live run | Pending | Pending live run |
| 9 | Average treatment cost by specialization | Pending live run | Pending | Pending live run |
| 10 | Show monthly appointment count for the past 6 months | Pending live run | Pending | Pending live run |
| 11 | Which city has the most patients? | Pending live run | Pending | Pending live run |
| 12 | List patients who visited more than 3 times | Pending live run | Pending | Pending live run |
| 13 | Show unpaid invoices | Pending live run | Pending | Pending live run |
| 14 | What percentage of appointments are no-shows? | Pending live run | Pending | Pending live run |
| 15 | Show the busiest day of the week for appointments | Pending live run | Pending | Pending live run |
| 16 | Revenue trend by month | Pending live run | Pending | Pending live run |
| 17 | Average appointment duration by doctor | Pending live run | Pending | Pending live run |
| 18 | List patients with overdue invoices | Pending live run | Pending | Pending live run |
| 19 | Compare revenue between departments | Pending live run | Pending | Pending live run |
| 20 | Show patient registration trend by month | Pending live run | Pending | Pending live run |

## Failure Analysis

- Live correctness is pending because the LLM-backed `/chat` flow cannot be exercised honestly without a configured `GOOGLE_API_KEY`.
- Once the key is available, the report should be updated by running all 20 prompts against the FastAPI server and recording the actual generated SQL and outcomes.
- Likely edge cases to watch during the live run:
  - ambiguous financial questions where invoices and treatments could imply different revenue definitions
  - chart generation for narrow result sets
  - average appointment duration, which is inferred from treatment duration because appointments do not have a native duration column
