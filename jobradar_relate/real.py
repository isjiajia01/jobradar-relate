"""Rank a real public job catalog (50 Djinni postings) on a temp graph. Synthetic profile; no SIMILAR_TO links.
Usage: make real [QUERY=engineer] | make real-why [JOB=d02]"""
import json, subprocess, sys, tempfile
from contextlib import closing
from pathlib import Path
import relate
from .demo import rank
from .discover import discover
from .facts import gather
from .importer import import_jobs

ROOT = Path(__file__).resolve().parents[1]

def main(term="developer"):
    jobs = json.load(open(ROOT / "data/real/djinni50.json"))
    with tempfile.TemporaryDirectory() as tmp:
        path = str(Path(tmp) / "real.rl")
        db = relate.connect(path)
        try:
            n, links = import_jobs(db, jobs)
        finally:
            db.close()
        subprocess.run(["relate", "query", "--database", path], input=(ROOT / "graph/profile_real.cypher").read_text(),
                       text=True, check=True, capture_output=True)
        with closing(relate.connect(path, read_only=True)) as db:
            ranked = rank(db)
            hits, shortlist = discover(db, term)
    print(f"{n} real postings (Djinni, MIT) · SIMILAR_TO links: {links} (single source) · profile is synthetic")
    for x in ranked[:5]:
        f = x["f"]; print(f"{x['score']:>3}  {f['job']}  {f['title']} @ {f['company']}  {x['why']}")
    print(f"search {term!r}: {hits} title hits · {len(shortlist)} unseen; top: " +
          ", ".join(f"{r['facts']['job']} fit {r['score']}" for r in shortlist[:3]))

def explain(job="d02"):
    """Which required skills do I already have, which are only adjacent, which are missing? Temp graph, read-only query."""
    jobs = json.load(open(ROOT / "data/real/djinni50.json"))
    with tempfile.TemporaryDirectory() as tmp:
        path = str(Path(tmp) / "real.rl")
        db = relate.connect(path)
        try: import_jobs(db, jobs)
        finally: db.close()
        subprocess.run(["relate", "query", "--database", path], input=(ROOT / "graph/profile_real.cypher").read_text(),
                       text=True, check=True, capture_output=True)
        with closing(relate.connect(path, read_only=True)) as db:
            f = gather(db, job)
    adjacent = {r["skill"]: r["via"] for r in f["related"]}
    missing = [s for s in f["required"] if s not in f["overlap"] and s not in adjacent]
    print(f"{job}  {f['title']} @ {f['company']}  (public Djinni listing; profile is invented)")
    print("have (exact):  " + (", ".join(f["overlap"]) or "none"))
    for skill, via in adjacent.items():
        print(f"adjacent:      {skill}  via  {skill} -RELATED_TO- {via} <-HAS_SKILL- User   (adjacent only, not a claim of qualification)")
    print("not covered:   " + (", ".join(missing) or "none"))

if __name__ == "__main__":
    if sys.argv[1:2] == ["--why"]: explain(*sys.argv[2:3])
    else: main(*sys.argv[1:2])
