# Synthetic scale benchmark

Run `make scale N=500` from the repository root. `N` defaults to 500 and accepts a positive integer. The generator uses seed 42 and returns listing records in the `data/sample_jobs.json` schema. It draws from three boards, 30 synthetic companies, four locations, and eight role and skill combinations. In each group of ten, the second listing is a next-day cross-board repost of the first. The benchmark uses the generated records in memory. It creates the graph and its replay copy in a temporary directory under `/tmp` and removes both on exit. It uses `relate-db==1.2.0` and the keyless scorer.

## One local run at N=500

These wall-clock measurements are machine-specific. This run used an Apple M1 Pro with 32 GB RAM, macOS 27.3, and Python 3.12.13. Generation, graph sanity queries, and final cleanup are outside the timed stages.

| Stage | Seconds | Work measured |
| --- | ---: | --- |
| Import + profile | 1.341344 | Create the store, import all listings, and apply `graph/profile.cypher`, including its full-text index |
| Rank | 0.278784 | Score and sort all 500 listings |
| Why | 0.000488 | Score `j02` and gather its explanation evidence |
| Replay | 0.288900 | Copy the store, change `j01` from liked to dismissed, rerank all jobs, and count changed scores |
| SEARCH | 0.013686 | Run title SEARCH for `engineer` and score the unseen shortlist |

The graph contained 548 nodes and 3,393 edges. The importer produced 380 similarity links. Of the graph's cross-board similarity pairs, 123 met the application's 0.8 repost threshold. The generator planted 50 pairs. The 123 threshold matches also include similar listings created independently from the small pool of roles and skills. With the stock profile's fixed seen history, one listing (`j02`) was marked `likely_duplicate`. Replay changed four scores. SEARCH returned its capped 25 title hits, including 23 unseen listings.

This is a synthetic workload, so the timings and counts describe this fixture. They provide no real-world performance or repost-accuracy evidence. The current importer compares listing pairs and reads at most 10,000 stored listings for similarity linking. The benchmark also reuses the application's 25-hit SEARCH cap.
