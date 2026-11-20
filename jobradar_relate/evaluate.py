"""Pairwise comparison: graph scorer vs a context-free baseline (skill overlap only).
Pairs come from eval/pairs.json (author-labelled, synthetic). Ties count 0.5.
Usage: python -m jobradar_relate.evaluate [jobradar.rl] [eval/results.md]"""
import json, os, shutil, sys, tempfile
import relate
from .demo import rank
from .facts import gather

def baseline(f):
    return 50 + 30 * len(f["overlap"]) // (len(f["required"]) or 1)

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
    open(out, "w").write(md); print(md)

if __name__ == "__main__":
    main(*sys.argv[1:3])
