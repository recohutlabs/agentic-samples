# Five-contract accuracy check

This is a focused development evaluation of fictional PDFs, with one live trial per contract. It does not establish accuracy on the entire portfolio or real contracts. The sample classifier, extractor and verifier run without expected answers in their prompts. Two cases run concurrently; no reviewer model is used.

`expected.json` contains manually authored, source-checked business-field expectations and page numbers. It is a partial expected JSON specification: long free-text descriptions are not scored as exact strings. `grading.py` handles decimal equivalence, annual/monthly basic salary alternatives and list membership. Missing keys are distinct from explicit null. Before running models, positive and negative controls check every predicate.

## Source interpretations frozen before the run

- FAC-001: pages 5/8 give annual fees already incorporating the amendment; do not add INR 32,000 per store again. INR 95,000 is a consumables cap, not its fixed price. Page 7 gives automatic 12-month renewal and 60-day non-renewal notice. Cover executed status conflicts with blank signatures on page 8: unclear, signing date null.
- FAC-003: pages 5/8 say the annual schedule already includes INR 210,000/420,000 additions. Page 7 requires a new written agreement to continue: manual renewal with no stated period or non-renewal notice. The cover's 120-day notice has no stated purpose. Page 5 payment days have no explicit calendar/business basis.
- FAC-002: page 7 permits a one-year mutually signed extension; the cover's 90-day notice is not a non-renewal rule. Page 8 blank signatures conflict with the cover. Annual pricing and dated route amendment do not authenticate execution.
- PRO-003: pages 2/4 describe a company buying staffing services, not direct employment. Page 3 renewal requires a signed written renewal. Page 4 expressly states whole-term fixed charges of INR 7,560,000; do not repeat it as an additional fee alongside annual rows. INR 950–1450 is a role-based range, not an exact standalone amount. Page 8 synthetic electronic execution markers are explicit fixture execution records, unlike blank signature lines in the facilities PDFs.
- EMP-001: pages 1/3 give proposed start 2026-10-01 and fixed expiry 2027-09-30; execution remains unsigned. Page 4 basic salary is INR 600,000 annually / 50,000 monthly; fixed gross salary and CTC are separate. Target annual CTC is INR 1,500,000 including conditional variable incentive. Both stated basic-salary representations are acceptable if the period matches. Pages 3/7 give 15-calendar-day probation and 60-calendar-day post-probation notices.

## Run

```bash
uv run python evaluation/run.py
```

Each timestamped run retains expected values, PDF and source-code hashes, configured model, stage durations, extracted JSON, verified JSON and a report. Local reports contain fictional contract values; credentials are never saved. A failed stage or remaining checked-field mismatch yields a nonzero exit. A passing score applies only to the selected checks, not every clause or legal validity.

Report changes are evaluated per check: wrong→right is an improvement; right→wrong is a regression. Do not infer verifier benefit from total pass count alone.

## Included results

[baseline-summary.json](baseline-summary.json) records 117/118 checked fields at each stage; [final-summary.json](final-summary.json) records 118/118 after the source-reported execution distinction was corrected. Both are one trial per fixture with the same frozen expected suite and configured `gpt-6-luna`. Neither trial recorded scored verifier corrections or regressions. The full fixture corpus contains 36 PDFs; the focused live evaluation covers five. Raw runtime databases, model outputs and private run logs are excluded from this public package.
