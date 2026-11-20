# Data notices

- `jobradar.rl`, `data/sample_jobs.json`, all profiles and verdicts: **synthetic**, written for this project.
- `data/real/djinni50.json` and `data/real/djinni_holdout50.json` each contain 50 postings sampled from the **Djinni Recruitment Dataset (English job descriptions)**,
  Hugging Face `lang-uk/recruitment-dataset-job-descriptions-english`, licence **MIT** (dataset card metadata, checked 2026-11-20).
  Only title, company, publication date and a source URL are kept; descriptions are not stored. Skills are extracted by this
  project's own 40-word keyword list, not taken from Djinni. Please cite the dataset paper (Djinni / lang-uk, LREC-COLING 2024) if you reuse it.
  Re-create the original file with `python3 scripts/fetch_djinni_sample.py data/real/djinni50.json`.
  Re-create the held-out draw with `python3 scripts/fetch_djinni_sample.py data/real/djinni_holdout50.json --seed 19 --exclude data/real/djinni50.json`.
