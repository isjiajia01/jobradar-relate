"""Pairwise comparison: graph scorer vs a context-free baseline (skill overlap only).
Pairs come from eval/pairs.json (author-labelled, synthetic). Ties count 0.5.
Usage: python -m jobradar_relate.evaluate [jobradar.rl] [eval/results.md]"""
import json, os, shutil, sys, tempfile
import relate
from pathlib import Path
from .demo import rank
from .importer import import_jobs
from .facts import gather

def baseline(f):
    return 50 + 30 * len(f["overlap"]) // (len(f["required"]) or 1)

def requisition_table(cases):
    counts = {label: 0 for label in ("TP", "TN", "FP", "FN")}
    rows = ["| case | withheld requisitions | prediction | outcome |", "|---|---|---|---|"]
    for case in cases:
        first, later = case["first"], case["later"]
        locations = case.get("locations", ["Example City", "Example City"])
        dates = case.get("dates", ["2026-10-01", "2026-10-02"])
        db = relate.connect(":memory:")
        try:
            for i, ((_, title, skills), location, posted) in enumerate(
                    zip((first, later), locations, dates, strict=True), start=1):
                import_jobs(db, [{"id": f"p{i}", "title": title, "skills": skills,
                                  "company": "Example Studio", "location": location,
                                  "posted_date": posted, "source": f"board{i}",
                                  "url": f"https://example.invalid/p{i}"}])
            db.execute("MATCH (p:Job {id:'p1'}) MERGE (u:User {id:'me'}) MERGE (u)-[:SEEN]->(p)")
            status = gather(db, "p2")["status"]
        finally:
            db.close()
        expected = first[0] == later[0]
        predicted = status == "likely_duplicate"
        label = ("T" if expected == predicted else "F") + ("P" if predicted else "N")
        counts[label] += 1
        rows.append(f"| {case['case']} | {first[0]} / {later[0]} | {status} | {label} |")
    return ("\n".join(rows) + f"\n\nCorrect: **{counts['TP'] + counts['TN']}/{len(cases)}**. "
            + ", ".join(f"{key}: {value}" for key, value in counts.items()) + ".\n")


def requisition_report():
    original = json.loads(Path("eval/requisitions.json").read_text())["cases"]
    held_out = json.loads(Path("eval/requisitions_holdout.json").read_text())["cases"]
    return ("\n## Repost detection on separate synthetic feeds\n\n"
            "Each pair has its own store. The importer receives two batches of public listing fields. "
            "Only the grader compares the withheld requisitions. A positive prediction is `likely_duplicate`. "
            "Case frequencies are constructed.\n\n"
            "### Original cases\n\nThe previous rule scored 4/6 (TP 2, TN 2, FP 1, FN 1).\n\n"
            + requisition_table(original) + "\nThe verbatim repost and separate-team case have identical "
            "observable inputs, so any deterministic classifier must miss at least one.\n\n"
            "### Held-out cases\n\nThese synthetic cases were authored after the revised rule was frozen "
            "in `e173fd3`. The previous rule scored 3/5 (TP 1, TN 2, FP 1, FN 1). They were scored without further tuning.\n\n" + requisition_table(held_out))

def main(db_path="jobradar.rl", out="eval/results.md"):
    pairs = json.load(open("eval/pairs.json"))["pairs"]
    d = tempfile.mkdtemp(); p = os.path.join(d, "c.rl"); shutil.copy(db_path, p)
    db = relate.connect(p)
    graph = {x["f"]["job"]: x["score"] for x in rank(db)}
    base = {j: baseline(gather(db, j)) for j in graph}
    db.close(); shutil.rmtree(d)
    rows, wins = [], {"graph": 0.0, "baseline": 0.0}
    for better, worse, why in pairs:
        r = {}
        for name, sc in (("graph", graph), ("baseline", base)):
            v = 1.0 if sc[better] > sc[worse] else 0.5 if sc[better] == sc[worse] else 0.0
            wins[name] += v; r[name] = {1.0: "win", 0.5: "tie", 0.0: "LOSS"}[v]
        rows.append(f"| {better} > {worse} | {graph[better]} vs {graph[worse]} | {r['graph']} | {base[better]} vs {base[worse]} | {r['baseline']} | {why} |")
    n = len(pairs)
    md = ("# Pairwise evaluation (synthetic, author-labelled)\n\n"
          f"Graph scorer: **{wins['graph']}/{n}**. Context-free baseline (skill overlap only): **{wins['baseline']}/{n}**.\n\n"
          "| pair | graph scores | graph | baseline scores | baseline | why |\n|---|---|---|---|---|---|\n" + "\n".join(rows) +
          "\n\nCaveats: 6 pairs on a 10-job fixture, labelled by the author; this shows the graph signals change rankings in the intended direction, "
          "not general ranking quality. The labels follow the same signals the graph scorer uses (dismissals, reposts, related skills), so a graph win is expected by construction; the value is showing a skill-only baseline cannot see them. Controls (first two rows) are expected to be easy for both.\n")
    md += requisition_report()
    Path(out).write_text(md)
    print(md)

if __name__ == "__main__":
    main(*sys.argv[1:3])
