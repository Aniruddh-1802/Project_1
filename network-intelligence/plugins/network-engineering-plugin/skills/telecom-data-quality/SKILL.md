---
name: telecom-data-quality
description: Use when reviewing schema changes, new transformations or new data sources in this project for quality risks.
---
# Telecom Data Quality Review (C8 skill)

Check every change against the project's known silent failures:
1. **Grain** — could this reintroduce duplicates on (grid_id, timestamp) after
   the country-code aggregation? (CLAUDE.md rules 1–2; tests/test_grain.py)
2. **Leakage** — could a feature see data after feature_timestamp? (ML2 rule;
   tests/test_ml.py::test_no_leakage)
3. **Geography** — does it join milano-grid.geojson? Must use
   properties.cellId, never the 0-based feature index (the RE4 trap).
4. **Terminology** — do any new field names, labels or strings imply counts,
   MB or congestion? (CLAUDE.md rules 3–4)
5. **AS_OF** — does it use wall-clock time where the AS_OF convention applies?
6. **Raw immutability** — does anything write under data/raw/?
Report findings in the C15 six-category format.
