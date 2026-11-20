"""Title search with a personal, unseen shortlist. Usage: make search QUERY=engineer"""
import argparse
from pathlib import Path
import shutil
import tempfile

import relate

from .facts import gather
from .score import fallback

SEARCH = """MATCH (j:Job)
SEARCH j IN (FULLTEXT INDEX job_titles FOR $term LIMIT 25) SCORE AS relevance
RETURN j.id AS id, relevance ORDER BY relevance DESC, id"""


def discover(db, term, user="me"):
    matches = list(db.execute(SEARCH, {"term": term}))
    shortlist = []
    for hit in matches:
        facts = gather(db, hit["id"], user)
        if not facts["seen"]:
            shortlist.append({"facts": facts, "relevance": hit["relevance"], **fallback(facts)})
    shortlist.sort(key=lambda row: (-row["score"], -row["relevance"], row["facts"]["job"]))
    return len(matches), shortlist


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("term")
    parser.add_argument("--database", default="jobradar.rl")
    args = parser.parse_args()
    with tempfile.TemporaryDirectory() as tmp:
        path = shutil.copyfile(args.database, Path(tmp) / "search.rl")
        db = relate.connect(str(path))
        try:
            count, rows = discover(db, args.term)
        finally:
            db.close()
    print(f"{count} title hits · {len(rows)} unseen")
    for row in rows:
        f = row["facts"]
        print(f"{f['job']}  {f['title']}  {f['status']}  text {row['relevance']:.3f}  fit {row['score']}")
        print(f"  {row['explanation']}")


if __name__ == "__main__":
    main()
