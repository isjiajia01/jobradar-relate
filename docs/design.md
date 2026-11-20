# Design notes

## The graph and scorer

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


## Search and replay details

Open `docs/demo.html` locally for the ranked cards, score breakdowns and evidence paths. The demo reads the committed `jobradar.rl` in read-only mode. Replay and evaluation work on disposable copies. No server or model download is needed. The score is a preference heuristic out of 100.

**Search for “engineer”.** Relate's persisted `job_titles` full-text index retrieves up to 25 listings with a text relevance score. Five titles match, all tied on text relevance. Two are already seen. The three remaining candidates rank **ML Engineer (70), DevOps Engineer (65), Data Engineer (60)** by personal fit, with text relevance and job ID breaking ties. Search matches titles only. Try `make search QUERY=developer` to inspect another shortlist.

`make why` prints one job’s score contributions and evidence paths. `make replay` prints before/after scores and paths for each job whose score changes. `LIKED` and `DISMISSED` replace the selected job’s feedback. `SEEN` records exposure while preserving feedback. The HTML demo shows the default replay. Changing one verdict on `j05` from dismissed to liked raises its score from **45 to 80**. Its neighbor `j06` moves from **50 to 75** through the same-company similarity edge. The other eight scores stay fixed. The two listings share a publication date, so their publication order is unknown.

