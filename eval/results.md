# Pairwise evaluation (synthetic, author-labelled)

Graph scorer: **6.0/6**. Context-free baseline (skill overlap only): **4.0/6**.

| pair | graph scores | graph | baseline scores | baseline | why |
|---|---|---|---|---|---|
| j09 > j02 | 80 vs 60 | win | 80 vs 70 | win | control: new job with full skill match beats a cross-board repost |
| j03 > j10 | 90 vs 60 | win | 65 vs 60 | win | control: liked job with related skills beats a weak skill match |
| j08 > j05 | 65 vs 45 | win | 60 vs 70 | LOSS | I dismissed j05 myself; j08 is a fresh job with a weaker skill match |
| j07 > j02 | 70 vs 60 | win | 70 vs 70 | tie | j02 is a LinkedIn repost of a job I already saw; j07 is new with equal skill match |
| j08 > j06 | 65 vs 50 | win | 60 vs 60 | tie | j06 resembles j05, which I dismissed |
| j04 > j06 | 70 vs 50 | win | 70 vs 60 | win | j06 resembles a dismissed job; j04 is new |

Caveats: 6 pairs on a 10-job fixture, labelled by the author; this shows the graph signals change rankings in the intended direction, not general ranking quality. The labels follow the same signals the graph scorer uses (dismissals, reposts, related skills), so a graph win is expected by construction; the value is showing a skill-only baseline cannot see them. Controls (first two rows) are expected to be easy for both.

## Repost detection on separate synthetic feeds

Each pair has its own store. The importer receives two batches of public listing fields. Only the grader compares the withheld requisitions. A positive prediction is `likely_duplicate`. Case frequencies are constructed.

### Original cases

The previous rule scored 4/6 (TP 2, TN 2, FP 1, FN 1).

| case | withheld requisitions | prediction | outcome |
|---|---|---|---|
| verbatim syndication | R11 / R11 | likely_duplicate | TP |
| minor skill edit | R12 / R12 | likely_duplicate | TP |
| board rewrites the title | R13 / R13 | likely_duplicate | TP |
| two teams advertise identical roles | R14 / R15 | likely_duplicate | FP |
| same employer, distinct tracks | R16 / R17 | new | TN |
| shared discipline, distinct openings | R18 / R19 | new | TN |

Correct: **5/6**. TP: 3, TN: 2, FP: 1, FN: 0.

The verbatim repost and separate-team case have identical observable inputs, so any deterministic classifier must miss at least one.

### Held-out cases

These synthetic cases were authored after the revised rule was frozen in `e173fd3`. The previous rule scored 3/5 (TP 1, TN 2, FP 1, FN 1). They were scored without further tuning.

| case | withheld requisitions | prediction | outcome |
|---|---|---|---|
| renamed accessibility opening | H21 / H21 | likely_duplicate | TP |
| separate branch teams hiring identical roles | H22 / H23 | similar_seen | TN |
| one multi-site opening advertised by city | H24 / H24 | similar_seen | FN |
| different functions share common tools | H25 / H26 | likely_duplicate | FP |
| later hiring cycle with shared tools | H27 / H28 | new | TN |

Correct: **3/5**. TP: 1, TN: 2, FP: 1, FN: 1.
