"""Compare the deterministic scorer with AI-annotated labels on the 50 real Djinni postings.
The labels come from a fresh reviewer agent for a FICTIONAL candidate; they are not a real person's feedback,
and the annotator's criterion (skill fit) overlaps the scorer's, so agreement is NOT independent validation.
Usage: make real-eval"""
import json, tempfile, subprocess
from contextlib import closing
from itertools import combinations
from pathlib import Path
import relate
from .demo import rank
from .importer import import_jobs, norm, similarity

ROOT = Path(__file__).resolve().parents[1]

def auc(pos, neg):
    """P(score of a random pos > random neg), ties count 0.5."""
    w = sum(1.0 if p > n else 0.5 if p == n else 0.0 for p in pos for n in neg)
    return w / (len(pos) * len(neg))

def main():
    jobs = json.load(open(ROOT / "data/real/djinni50.json"))
    lab = json.load(open(ROOT / "data/real/ai_labels.json"))
    label = {x["id"]: x["label"] for x in lab["labels"]}
    with tempfile.TemporaryDirectory() as tmp:
        path = str(Path(tmp) / "r.rl")
        db = relate.connect(path)
        try: import_jobs(db, jobs)
        finally: db.close()
        subprocess.run(["relate", "query", "--database", path], input=(ROOT / "graph/profile_real.cypher").read_text(),
                       text=True, check=True, capture_output=True)
        with closing(relate.connect(path, read_only=True)) as db:
            ranked = rank(db)
    graph = {x["f"]["job"]: x["score"] for x in ranked}
    overlap = {x["f"]["job"]: len(x["f"]["overlap"]) for x in ranked}   # baseline: count of matched skills only
    ids = {k: [i for i in label if label[i] == k] for k in ("LIKED", "NEUTRAL", "DISMISSED")}
    print("AI labels (fictional candidate): " + ", ".join(f"{k} {len(v)}" for k, v in ids.items()))
    for name, s in (("graph scorer", graph), ("skill-count baseline", overlap)):
        a = auc([s[i] for i in ids["LIKED"]], [s[i] for i in ids["DISMISSED"]])
        top = sorted(s, key=lambda i: (-s[i], i))[:len(ids["LIKED"])]
        hit = sum(label[i] == "LIKED" for i in top)
        print(f"{name:22} AUC LIKED>DISMISSED {a:.2f} · top-{len(top)} contains {hit}/{len(top)} LIKED")
    print("(random = AUC 0.50; ties count half; there are no SIMILAR_TO or feedback edges here, so the graph adds nothing beyond skills)")
    rule = [(a["id"], b["id"]) for a, b in combinations(jobs, 2) if similarity(a, b) >= 0.6]
    ident = [(a["id"], b["id"]) for a, b in combinations(jobs, 2)
             if norm(a["title"]) == norm(b["title"]) and set(a["skills"]) == set(b["skills"])]
    clear = [tuple(p) for p in lab["similar_pairs_clear"]]
    print(f"clear similar pairs per annotator: {clear}")
    print(f"importer rule (same company, different source) finds {len(rule)} pairs; recovers {sum(p in rule for p in clear)}/{len(clear)}")
    print(f"post-hoc check, same title + identical skill set: {ident} (defined after seeing the labels, not part of the importer)")

if __name__ == "__main__":
    main()
