# jobradar-relate

Explainable job recommendations on a [Relate](https://relatedb.ai) graph.
Entry for the *Relate by Neo4j Hackathon* (theme: Context, Connected).

Jobradar is a daily LLM job digest I built and run myself (Jobindex, Jobnet, LinkedIn -> filters -> LLM scoring -> email). This repo adds a **Relate memory layer** in front of the LLM scoring step. Everything here uses **synthetic example data only**; the original Jobradar repo is private and nothing from it is included. SQLite stays the store for dedup, status and history in Jobradar; Relate is the relationship memory.

## How I use Relate, and why
Before the LLM scores a job, four graph queries collect facts about it. The LLM (or a deterministic fallback) sees only those facts and returns a score plus one sentence, together with the graph path used. It cannot cite a reason that is not in the graph.

Problems this addresses:
1. LLM scoring was a black box on one JD with no relationships.
2. The same job appears on Jobindex / Jobnet / LinkedIn; SQLite dedup alone cannot show they are related. Relate stores `SIMILAR_TO` edges.
3. No memory of what I liked or dismissed. Relate stores `LIKED` / `DISMISSED` edges.
4. Recommendations could not explain themselves. Each result carries a path.

## Mode: single file
`./jobradar.rl` is one persistent Relate file, opened in-process (no server, no signup).

**Why this mode:** one file per agent/user, easy to back up, submit and inspect. Judges can open the committed file directly (see below). Not `:memory:`, so the data survives and is inspectable.

## What the graph models
Nodes: `Job {id,title,url,source,posted_date}`, `Company {name}`, `Skill {name}`, `Location {name}`, `User {id}` (one anonymised profile).

Edges: `(Job)-[:AT]->(Company)`, `(Company)-[:POSTED]->(Job)`, `(Job)-[:REQUIRES]->(Skill)`, `(Job)-[:IN]->(Location)`, `(Job)-[:SIMILAR_TO {score}]->(Job)`, `(User)-[:LIKED|DISMISSED]->(Job)`, `(Skill)-[:RELATED_TO]->(Skill)`, plus `(User)-[:HAS_SKILL]->(Skill)` (added to compute skill overlap).

The four queries (`jobradar_relate/facts.py`):
1. Required skills and overlap with my profile.
2. Liked/dismissed jobs that are similar to this one at the same company.
3. `SIMILAR_TO` links to jobs already seen: `likely_duplicate` (score >= 0.8, different source), `similar_seen`, or `new`.
4. One explanation path, e.g. `Data Engineer@Nordlys Analytics -REQUIRES-> Airflow, Python, SQL; User -HAS_SKILL-> Python, SQL; User -LIKED-> 1 similar job at same company; -SIMILAR_TO-> j01 (jobindex, 0.8) => likely_duplicate`.

## Setup and run
```bash
curl -sSfL https://relatedb.ai/install.sh | bash     # Relate CLI (tested with v1.2.0)
python3 -m venv .venv && .venv/bin/pip install relate-db

# inspect the committed graph (read-only)
relate query --database ./jobradar.rl --read-only --mode envelope \
  'MATCH (n) RETURN labels(n)[0] AS l, count(*) AS n ORDER BY l'

# import jobs (idempotent MERGE, never deletes) and add SIMILAR_TO edges
PYTHONPATH=. .venv/bin/python -m jobradar_relate.importer data/sample_jobs.json jobradar.rl

# score with graph facts + explanation path
PYTHONPATH=. .venv/bin/python -m jobradar_relate.score jobradar.rl j02 j06 j09
```
The scorer uses a deterministic fallback by default. To use an LLM, set `LLM_URL`, `LLM_API_KEY`, `LLM_MODEL` (OpenAI-compatible, temperature 0); it receives only the graph facts. The output field `scorer` says which one ran. (The LLM path is untested so far.)

`graph/seed.cypher` rebuilds the 10-job example graph from scratch; `graph/explain.cypher` is a single-query version of the explanation path.

## Where the data lives
`./jobradar.rl` in the repo root (single file, ~48 KB, synthetic data).

## Limits
- SIMILAR_TO is a simple heuristic (same company, different source, title + skill overlap); cross-company duplicates are not detected.
- Only a JSON importer is included; no SQLite adapter yet.
- Job Ops, a separate earlier project of mine, is not part of this.
