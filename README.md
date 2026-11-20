# Jobradar · connected job memory

Explainable job recommendations, remembered in a single-file Relate graph.

Why does the same Data Engineer opening score **95 on one board and 60 on another**? The synthetic profile has seen and liked `j01`, which was published before `j02`. A cross-board similarity edge connects the listings. The later posting gets a repost penalty. Both scores carry the graph evidence that produced them.

This solo entry for the *Relate by Neo4j Hackathon* explores a memory layer for a personal job digest. All listings, profile choices and outcomes in this repository are synthetic.

## Use case

I keep a personal daily LLM job digest (Jobindex, Jobnet, LinkedIn). It scores each posting from one description, so it forgets what I liked or dismissed, cannot see that boards repost the same opening, and cannot explain a score. The relationships that matter: job to skills, job to company, job to similar listings on other boards, and my verdicts on neighbouring jobs. This repo is a synthetic prototype of that memory layer.

## How it uses Relate

- **Mode:** single file (embedded, in-process; no server, no signup).
- **Why this mode:** one file per user is easy to back up, commit and inspect. Judges can open the exact store, `jobradar.rl`, with the `relate` CLI or the Python client. It is persistent, not `:memory:`.
- **What the graph models:** `Job`, `Company`, `Skill`, `Location`, `User`; edges `AT`, `POSTED`, `REQUIRES`, `IN`, `SIMILAR_TO {score}`, `LIKED`, `DISMISSED`, `SEEN`, `HAS_SKILL`, `RELATED_TO`. Details below.
- **Relate capabilities used:** embedded Python client (`relate-db` 1.2.0), CLI (`--read-only`), Cypher with bound parameters, persisted full-text index and `SEARCH`.

## Where the data lives

`./jobradar.rl` in the repo root (about 48 KB, synthetic). `make build OUT=<new path>` rebuilds an equivalent store from `data/sample_jobs.json` and `graph/profile.cypher`.

## Origin, disclosure and AI use

- **Started during the contest:** all code in this repository was first committed on 2026-11-20, after the contest began. No code was copied from my earlier private Jobradar project; only the idea (a daily job digest with LLM scoring) carries over. Jobradar is a personal tool, not an employer or production system.
- **Data:** every job, company and profile choice is synthetic. No real feedback or other people's data is included.
- **AI tools:** the repository was written with AI coding agents under my direction, running in the Pi coding-agent harness. An agent wrote most of the code, tests, fixtures and docs; a separate review agent audited the design and led to fixes (unvalidated LLM output, inconsistent fixtures, a scoring gap, repost-detection changes). I chose the scope, approved each step and checked results. The optional LLM scoring path calls an OpenAI-compatible endpoint; the judge path uses no model.
- **Third-party:** Relate v1.2.0 (Apache-2.0), `relate-db` 1.2.0, Python standard library (including SQLite).

## License

MIT, see [LICENSE](LICENSE).

## Setup and run (judge demo)

```bash
# Prerequisites: Python 3.12+, make; Relate CLI optional (relatedb.ai)
make demo    # installs the pinned Python client on first run
make search QUERY=engineer
make replay JOB=j05 VERDICT=LIKED
make why JOB=j06
make test
make eval
```

Open `docs/demo.html` locally for the ranked cards, score breakdowns and evidence paths. The demo reads the committed `jobradar.rl` in read-only mode. Replay and evaluation work on disposable copies. No server or model download is needed. The score is a preference heuristic out of 100.

**Search for “engineer”.** Relate's persisted `job_titles` full-text index retrieves up to 25 listings with a text relevance score. Five titles match, all tied on text relevance. Two are already seen. The three remaining candidates rank **ML Engineer (70), DevOps Engineer (65), Data Engineer (60)** by personal fit, with text relevance and job ID breaking ties. Search matches titles only. Try `make search QUERY=developer` to inspect another shortlist.

`make why` prints one job’s score contributions and evidence paths. `make replay` prints before/after scores and paths for each job whose score changes. `LIKED` and `DISMISSED` replace the selected job’s feedback. `SEEN` records exposure while preserving feedback. The HTML demo shows the default replay. Changing one verdict on `j05` from dismissed to liked raises its score from **45 to 80**. Its neighbor `j06` moves from **50 to 75** through the same-company similarity edge. The other eight scores stay fixed. The two listings share a publication date, so their publication order is unknown.

## Inside the single-file graph

`Job` nodes link to `Company`, `Skill` and `Location`. A synthetic `User` has skills, has seen listings and can like or dismiss them. `RELATED_TO` connects adjacent skills. `SIMILAR_TO` connects cross-board listings at the same company using title and skill overlap, plus one curated weaker link. A matching location and at least two identical required skills (the entire set) can support a renamed title when publication dates are within seven days. Conflicting location strings cap similarity at 0.7. The edge's stored direction follows job ID only.

The scorer reads required skills, exact matches, adjacent skills, own verdicts and same-company neighbor verdicts. A likely repost requires a personally seen, strictly earlier ISO-dated listing on another board with similarity at least 0.8. Reposts lose 20 points and are capped at 60. Similarity alone carries no repost penalty. SEEN records exposure, independent of feedback. The ranking includes seen jobs so judges can inspect the propagation.

```bash
# With Relate CLI v1.2.0 installed and make demo run:
make build OUT=/tmp/fresh-jobradar.rl   # choose a path that does not exist
relate query -d jobradar.rl --read-only 'MATCH (:User)-[:SEEN]->(j:Job) RETURN j.id ORDER BY j.id'
make score                             # three individual explanations
make sqlite                            # synthetic SQLite -> importer JSON
```

`make build` imports `data/sample_jobs.json` and applies `graph/profile.cypher`. `make import` additively applies those fixtures to the root store. `graph/explain.cypher` illustrates the overlap and same-company feedback portion of the evidence. The Python client is pinned to `relate-db==1.2.0`. Install the matching CLI from [Relate](https://relatedb.ai).

The individual scorer optionally calls an OpenAI-compatible endpoint if `LLM_URL`, `LLM_MODEL` and `LLM_API_KEY` are set. Its response passes a schema and token heuristic before use. That heuristic cannot establish factual faithfulness. The judge demo and evaluation always use deterministic scoring.

## Optional read-only MCP recipe

With the Relate v1.2.0 CLI on `PATH`, configure your MCP host to launch the absolute path to `scripts/mcp-readonly.sh` over stdio. From the repository root, its command is `relate serve --database jobradar.rl --mcp stdio --read-only`. The judge targets work without MCP.

We called `get_schema` with `{}` and `read_cypher` directly over MCP stdio on a temporary copy of the shipped store. Verification covered the protocol and tools only. No particular agent client was tested. Pass each query below as the `statement` argument to `read_cypher`.

**Which dismissed listing contributes to j06’s penalty?** The result is `j05`, `DISMISSED`, similarity `0.8`, at Havn Pay. That same-company feedback costs j06 15 points.

```cypher
MATCH (:User {id:'me'})-[v:DISMISSED]->(peer:Job)-[s:SIMILAR_TO]-(j:Job {id:'j06'})
MATCH (peer)-[:AT]->(c:Company)<-[:AT]-(j)
RETURN peer.id AS peer, type(v) AS verdict, s.score AS similarity, c.name AS company
```

**Which Jobindex listings has the profile seen?** The result is `j01`.

```cypher
CYPHER 25 MATCH (:User {id:'me'})-[:SEEN]->(j:Job)
FILTER j.source = 'jobindex'
RETURN j.id AS job ORDER BY job
```

## Evaluation and limits

On six author-labelled comparisons, the graph scores **6/6** and skill overlap alone scores **4/6**, counting ties as half. The labels mirror the scorer's signals, making this a regression check. Ten synthetic jobs cannot establish real-world ranking quality. Similarity can miss renamed roles and confuse genuinely separate openings with identical titles. Inspect every pair and both scores in [the generated evaluation](eval/results.md).

Repost identity improved from **4/6 to 5/6** on the original synthetic two-board feeds. Only the grader sees the synthetic requisition IDs. The revised rule catches the renamed opening. The verbatim repost and the separate-team openings have identical public fields in both pairs, so the latter still triggers a false positive. [Original cases](eval/requisitions.json)

On five synthetic cases authored after the rule was frozen, both versions scored **3/5**. The revised rule catches a renamed accessibility role and distinguishes branch teams listing different cities. It misses a single opening listed in two cities and flags two unrelated functions that share common tools. These results measure behavior on constructed examples. [Held-out cases](eval/requisitions_holdout.json) · [Predictions](eval/results.md)
