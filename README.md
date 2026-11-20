# Jobradar · connected job memory

Why does the same Data Engineer opening score **95 on one board and 60 on another**? The synthetic profile liked `j01` and saw it before encountering `j02`. A cross-board similarity edge connects the listings. The later posting gets a repost penalty. Both scores carry the graph evidence that produced them.

This solo entry for the *Relate by Neo4j Hackathon* explores a memory layer for a personal job digest. All listings, profile choices and outcomes in this repository are synthetic.

## Run the judge demo

```bash
make demo    # installs the pinned Python client on first run
make test
make eval
```

Open `docs/demo.html` locally for the ranked cards, score breakdowns and evidence paths. The keyless demo and evaluation read disposable copies of the committed `jobradar.rl`. No server or model download is needed. The score is a preference heuristic out of 100.

Try the feedback replay at the end of the demo. Changing one verdict on `j05` from dismissed to liked raises its score from **45 to 80**. Its neighbor `j06` moves from **50 to 75** through the same-company similarity edge. The other eight scores stay fixed. The two listings share a publication date, so their publication order is unknown.

## Inside the single-file graph

`Job` nodes link to `Company`, `Skill` and `Location`. A synthetic `User` has skills, has seen listings and can like or dismiss them. `RELATED_TO` connects adjacent skills. `SIMILAR_TO` connects cross-board listings at the same company using title and skill overlap, plus one curated weaker link. The edge's stored direction follows job ID only.

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

## Evaluation and limits

On six author-labelled comparisons, the graph scores **6/6** and skill overlap alone scores **4/6**, counting ties as half. The labels mirror the scorer's signals, making this a regression check. Ten synthetic jobs cannot establish real-world ranking quality. Similarity can miss renamed roles and confuse genuinely separate openings with identical titles. Inspect every pair and both scores in [the generated evaluation](eval/results.md).
