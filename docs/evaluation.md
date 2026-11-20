# Evaluation and limits


On six author-labelled comparisons, the graph scores **6/6** and skill overlap alone scores **4/6**, counting ties as half. The labels mirror the scorer's signals, making this a regression check. Ten synthetic jobs cannot establish real-world ranking quality. Similarity can miss renamed roles and confuse genuinely separate openings with identical titles. Inspect every pair and both scores in [the generated evaluation](../eval/results.md).

Repost identity improved from **4/6 to 5/6** on the original synthetic two-board feeds. Only the grader sees the synthetic requisition IDs. The revised rule catches the renamed opening. The verbatim repost and the separate-team openings have identical public fields in both pairs, so the latter still triggers a false positive. [Original cases](../eval/requisitions.json)

On five synthetic cases authored after the rule was frozen, both versions scored **3/5**. The revised rule catches a renamed accessibility role and distinguishes branch teams listing different cities. It misses a single opening listed in two cities and flags two unrelated functions that share common tools. These results measure behavior on constructed examples. [Held-out cases](../eval/requisitions_holdout.json) · [Predictions](../eval/results.md)
