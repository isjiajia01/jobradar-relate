# jobradar-relate

Explainable job recommendations on a [Relate](https://relatedb.ai) graph.
Entry for the *Relate by Neo4j Hackathon* (theme: Context, Connected).

This is a synthetic prototype inspired by Jobradar, a daily LLM job digest I built and run myself (Jobindex, Jobnet, LinkedIn -> filters -> LLM scoring -> email). This repo adds a **Relate memory layer** in front of the LLM scoring step. Everything here uses **synthetic example data only**; the original Jobradar repo is private and nothing from it is included. SQLite stays the store for dedup, status and history in Jobradar; Relate is the relationship memory.

## How I use Relate, and why
Before the LLM scores a job, four graph queries collect facts about it. The LLM (or a deterministic fallback) sees only those facts and returns a score plus one sentence, together with the graph path used. LLM replies are validated: only `score` and `explanation` are kept, and any job id or number in the explanation must appear in the graph facts, otherwise the fallback runs. (This is a heuristic check, not a proof of faithfulness.)

Problems this addresses:
1. LLM scoring was a black box on one JD with no relationships.
2. The same job appears on Jobindex / Jobnet / LinkedIn; SQLite dedup alone cannot show they are related. Relate stores `SIMILAR_TO` edges.
3. No memory of what I liked or dismissed. Relate stores `LIKED` / `DISMISSED` edges.
4. Recommendations could not explain themselves. Each result carries a path.

## Mode: single file
`./jobradar.rl` is one persistent Relate file, opened in-process (no server, no signup).

**Why this mode:** one file per agent/user, easy to back up, submit and inspect. Judges can open the committed file directly (see below). Not `:memory:`, so the data survives and is inspectable.

## What the graph models
Nodes: `Job {id,title,url,source,posted_date}`, `Company {name}`, `Skill {name}`, `Location {name}`, `User {id}` (one synthetic profile, `me`).

Edges: `(Job)-[:AT]->(Company)`, `(Company)-[:POSTED]->(Job)`, `(Job)-[:REQUIRES]->(Skill)`, `(Job)-[:IN]->(Location)`, `(Job)-[:SIMILAR_TO {score}]->(Job)`, `(User)-[:LIKED|DISMISSED]->(Job)`, `(Skill)-[:RELATED_TO]->(Skill)`, plus `(User)-[:HAS_SKILL]->(Skill)` (added to compute skill overlap).

The four queries (`jobradar_relate/facts.py`):
1. Required skills and overlap with my profile.
2. Liked/dismissed jobs that are similar to this one at the same company.
3. `SIMILAR_TO` links to jobs already seen: `likely_duplicate` (score >= 0.8, different source), `similar_seen`, or `new`.
4. One explanation path, e.g. `Data Engineer@Nordlys Analytics -REQUIRES-> Airflow, Python, SQL; User -HAS_SKILL-> Python, SQL; User -LIKED-> 1 similar job at same company; -SIMILAR_TO-> j01 (jobindex, 0.8) => likely_duplicate`.

## Judge quick start (no API key)
```bash
curl -sSfL https://relatedb.ai/install.sh | bash   # optional: only needed for the CLI queries below
make demo      # creates .venv (relate-db==1.2.0), ranks all 10 jobs from jobradar.rl, writes docs/demo.html
```
`make demo` reads a temporary copy of `jobradar.rl` (the shipped file is never modified). It prints a ranking and writes `docs/demo.html` with, per job: the itemised score, the graph path (`User -LIKED-> j01 -SIMILAR_TO(0.7)-> j03`), and the SIMILAR_TO links. It also replays one feedback change in a temp copy: flip `j05` from DISMISSED to LIKED: `j05` moves 25 -> 60 (my own verdict) and its repost `j06` moves 30 -> 55 (the evidence path through `j05` changed); no other job moves. Duplicates are capped at 60 so a repost never outranks a new job.

## Evaluation
`make eval` compares the graph scorer with a context-free baseline (skill overlap only) on 6 author-labelled synthetic pairs (`eval/pairs.json`, results in `eval/results.md`): graph 6/6, baseline 4/6 (1 loss, 2 ties). This is a small fixture-specific check that the graph signals (own verdicts, reposts, similar-job feedback, related skills) change rankings in the intended direction; it is not evidence of general ranking quality.

Scoring uses six graph queries: required skills and overlap, `RELATED_TO` skills I lack but am adjacent to, similar liked/dismissed jobs at the same company, `SIMILAR_TO` duplicate status, my own verdict on the job, and the evidence path.

## Setup and run
```bash
curl -sSfL https://relatedb.ai/install.sh | bash     # Relate CLI (tested with v1.2.0)
python3 -m venv .venv && .venv/bin/pip install relate-db

# inspect the committed graph (read-only)
relate query --database ./jobradar.rl --read-only --mode envelope \
  'MATCH (n) RETURN labels(n)[0] AS l, count(*) AS n ORDER BY l'

# import jobs (idempotent MERGE, never deletes) and add SIMILAR_TO edges
make import        # = PYTHONPATH=. .venv/bin/python -m jobradar_relate.importer data/sample_jobs.json jobradar.rl

# score with graph facts + explanation path
make score         # j02 j06 j09
make test          # unit tests (temp store, never touches jobradar.rl)
```
SQLite: `jobradar_relate/sqlite_adapter.py` reads a `jobs` table (synthetic schema built by `data/make_sample_sqlite.py`) into importer JSON; `make sqlite` demos it.
The scorer uses a deterministic fallback by default. To use an LLM, set `LLM_URL`, `LLM_API_KEY`, `LLM_MODEL` (OpenAI-compatible, temperature 0); it receives only the graph facts. The output field `scorer` says which one ran. The LLM path was run once against an OpenAI-compatible gateway (`deepseek-flash`): 2 of 3 jobs were scored by the LLM, 1 timed out and used the fallback, which `scorer` reported correctly.

`make build OUT=/tmp/x.rl` rebuilds the example graph from `data/sample_jobs.json` + `graph/profile.cypher` into a new file; `graph/explain.cypher` is a standalone query returning the same facts as the scorer.

## Where the data lives
`./jobradar.rl` in the repo root (single file, ~48 KB, synthetic data).

## Limits
- SIMILAR_TO is a simple heuristic (same company, different source, title + skill overlap); cross-company duplicates are not detected.
- The SQLite adapter targets a synthetic schema, not the real Jobradar database.
- Job Ops, a separate earlier project of mine, is not part of this.
