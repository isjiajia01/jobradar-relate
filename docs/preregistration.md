# Djinni held-out ranking protocol

## Stage B annotation brief

Give a fresh annotator only the following paragraph and the 50 records' IDs, titles, companies and skill keywords in file order. Withhold the scores, ranking, evaluation code, historical labels and model rules.

> Label each posting LIKED, NEUTRAL or DISMISSED for a fictional candidate whose skills are Python, SQL, Docker and Spark. The candidate is lukewarm on pure Java or Scala roles and does not want management, architect or CTO roles. Judge each posting from its title, company and listed skills. Use NEUTRAL for uncertain or mixed fit. Return one label per ID as `{"labels":[{"id":"…","label":"…"}]}`.

## Frozen decisions before sampling or evaluation

Djinni skill tags are keyword mentions from the title and description. The denominator in the old scorer treats every mention as a requirement. Even with more evidence of fit, a three-match listing with twelve tags earns fewer points than a one-match listing with two. This is a possible mechanism for the historical AUC gap, not an attribution measured from the exposed labels. The graph also omitted preferences given to the historical annotator.

1. Opt this profile into positive skill evidence. Add 10 points per exact match. One exact match is worth twice the existing five-point adjacent-skill bonus. The four stated skills can contribute 40 points over the existing base of 50, leaving room for both existing adjacency bonuses. Additional unrelated keywords do not demote a listing. Profiles without this option retain their fraction formula.
2. Record Java and Scala as `AVOIDS` skills. Apply one soft penalty of five points (one adjacency bonus) when an avoided language appears as a whole word in the title and Python is absent from the extracted skills. The title indicates emphasis beyond a passing mention. Python evidence conservatively exempts mixed stacks. This proxy can still mistake a multilingual role for a pure one.
3. Store explicit excluded title terms on the user. A case-insensitive whole-word or whole-phrase match for `manager`, `management`, `director`, `head of`, `architect`, `cto` or `chief technology officer` sets the final score to zero. A stated exclusion overrides skill evidence. A lead or senior title alone does not establish management. Titles can obscure duties or mention another role.

The old scorer is the exact original fraction formula with its adjacency, feedback, saturation and duplicate rules. Count uses only the number of distinct matched skills. The three methods use the same fresh graph with the same four skills, no feedback, and the original Spark–Hadoop and Docker–Kubernetes adjacency rules. The small synthetic demo retains its existing profile and scorer.

## Sample and analysis

Draw the first 50 eligible English postings under the existing Djinni category and skill filters, using seed 19 for eight sorted 100-row offsets. Exclude the original sample's source URLs and companies (case-folded alphanumeric company names), and select unique companies and URLs within the new sample. Seed 19's initial offsets are disjoint from seed 7's. If eight chunks are insufficient, continue drawing unused offsets with the same RNG, excluding the seed-7 offsets. Freeze the extracted JSON with this document before annotation. No replacement sample or subgroup selection after annotation.

Stage C runs `make real-holdout-eval` once after saving all labels in `data/real/holdout_labels.json`. For all three methods report LIKED vs DISMISSED AUC: compare every such pair, awarding 1 for a win and 0.5 for a tie. Exclude NEUTRAL only from AUC. Report exact pair credit and denominator. Top-k hits are secondary, with k equal to the number of LIKED postings, ranking all 50. If the cutoff splits a tied score group, credit the fraction of the group's LIKED entries corresponding to the remaining slots (uniform tie-breaking in expectation). Never use ID order to resolve ties. Missing, extra, duplicate or invalid labels invalidate the run. Without both LIKED and DISMISSED the primary result is undefined.

**Success requires strictly higher held-out AUC than the skill-count baseline.** Compare exact credit before rounding. Report win, tie or loss and the old scorer's result regardless. A win measures agreement with one AI annotator sharing the same fictional profile. It does not establish statistical significance or generalization to real people. The historical aggregate and criterion were already exposed. The preference-aware scorer has more profile information than the count baseline. No historical per-posting outcomes are used to select rules or weights.

## Amendment 1 (2026-11-20, before any label was produced or seen)

The first draw (SHA-256 `ab4cd2bc…`, 8 chunks) was a one-stack sample: 3 of 50 postings contained Python and almost all were `.NET` or `Middle Java Developer` titles, so it could not contain enough LIKED postings to test the scorer. This was judged from titles and keywords only; no labels existed. The Djinni dataset is sorted by title, so 8 contiguous chunks cluster by stack. Replacement rule, applied once: for the held-out draw, read 40 chunks (seed 19, seed-7 offsets excluded), pool all eligible postings, shuffle with the same RNG, then take the first 50 with unique companies and URLs not in the first sample. The scorer, metrics and success rule above are unchanged. The first draw is discarded and never labelled. No further replacement is allowed.

## Result (Stage C, run once, 2026-11-20)

`make real-holdout-eval`, 50 held-out postings labelled by a fresh AI annotator (LIKED 9, NEUTRAL 7, DISMISSED 34; 306 LIKED/DISMISSED pairs):

| Method | AUC | Top-9 expected LIKED hits |
|---|---|---|
| New (preference-aware) scorer | 0.8905 | 6.5 |
| Old scorer | 0.9788 | 6 |
| Skill-count baseline | 0.9869 | 6.33 |

**Outcome: loss.** The new scorer ranks below both the old scorer and the baseline. Nothing was changed after seeing this. Post-hoc note (not used to change anything): the hard exclusion matched the title word "Management" in "Senior Backend Engineer, Data Management Team" (a LIKED posting), scoring it zero, and the +10-per-skill rule produces many coarse ties. The new scorer is therefore not merged into main.
