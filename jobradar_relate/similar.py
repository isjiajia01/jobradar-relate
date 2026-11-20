"""Find lexical neighbors in a temporary vector index and explain graph evidence."""
import argparse
from contextlib import closing, contextmanager
import hashlib
from pathlib import Path
import re
import shutil
from tempfile import TemporaryDirectory

import relate

from .facts import Q3, Q4, Q6

DIMENSIONS = 256
TOP_K = 3
PAIRS = (("j01", "j02"), ("j05", "j06"))
TEXT = """MATCH (j:Job) OPTIONAL MATCH (j)-[:REQUIRES]->(s:Skill)
RETURN j.id AS id, j.title AS title, j.description AS description, collect(DISTINCT s.name) AS skills"""
SEARCH = """CALL db.index.vector.queryNodes($index, $count, $vector)
YIELD node, score RETURN node.id AS id, score"""


def embedding(title, description, skills):
    counts = [0] * DIMENSIONS
    for field in (title, description, *skills):
        for token in re.findall(r"\w+", (field or "").casefold()):
            digest = hashlib.sha256(token.encode()).digest()
            counts[int.from_bytes(digest[:4], "big") % DIMENSIONS] += 1
    return counts


@contextmanager
def indexed_copy(source):
    with TemporaryDirectory() as directory:
        store = shutil.copyfile(source, Path(directory) / "similar.rl")
        with closing(relate.connect(str(store))) as db:
            vectors = {row['id']: embedding(row['title'], row['description'], row['skills'])
                       for row in db.execute(TEXT)}
            for job, vector in vectors.items():
                if any(vector):
                    db.execute("MATCH (j:Job {id:$id}) SET j.lexical = $vector",
                               {"id": job, "vector": vector})
            db.execute(f"""CREATE VECTOR INDEX job_lexical FOR (j:Job) ON (j.lexical)
                OPTIONS {{indexConfig: {{`vector.dimensions`: {DIMENSIONS},
                `vector.similarity_function`: 'cosine'}}}}""")
            yield db, vectors


def neighbors(db, vectors, job):
    if job not in vectors:
        raise ValueError(f"unknown JOB {job!r}")
    if not any(vectors[job]):
        raise ValueError(f"no indexable words for JOB {job!r}")
    rows = db.execute(SEARCH, {"index": "job_lexical", "count": len(vectors), "vector": vectors[job]})
    # Request all ten fixture jobs so ties at the shortlist boundary resolve by ID.
    peers = [(r['id'], r['score']) for r in rows if r['id'] != job]
    return sorted(peers, key=lambda pair: (-pair[1], pair[0]))[:TOP_K]


def show(db, vectors, job):
    shortlist = neighbors(db, vectors, job)
    params = {"id": job, "user": "me"}
    company = db.execute(Q4, params).single()['company']
    links = {r['id']: r['score'] for r in db.execute(Q3, params)}
    results = []
    for rank, (peer, score) in enumerate(shortlist, 1):
        params = {"id": peer, "user": "me"}
        head = db.execute(Q4, params).single()
        verdict = next((r['verdict'] for r in db.execute(Q6, params)), 'none')
        same = head['company'] == company
        line = (f"{peer} {head['title']} | lexical #{rank} {score:.3f} | "
                f"same company={company if same else 'no'} | "
                f"SIMILAR_TO={links.get(peer, 'none')} | my verdict={verdict}")
        results.append(((peer not in links, not same, rank), line))
    print(f"{job} | toy lexical embedding (non-semantic) | top {TOP_K}")
    for _, line in sorted(results):
        print(line)


def check(db, vectors):
    hits = 0
    for a, b in PAIRS:
        for source, target in ((a, b), (b, a)):
            ranks = [peer for peer, _ in neighbors(db, vectors, source)]
            rank = ranks.index(target) + 1 if target in ranks else 'miss'
            hits += target in ranks
            print(f"{source} -> {target} lexical rank {rank}")
    print(f"Vector-only hits@{TOP_K}: {hits}/{2 * len(PAIRS)} directions")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("job", nargs="?")
    mode.add_argument("--check", action="store_true")
    args = parser.parse_args()
    with indexed_copy("jobradar.rl") as (db, vectors):
        if args.check:
            check(db, vectors)
        else:
            try:
                show(db, vectors, args.job)
            except ValueError as exc:
                parser.error(str(exc))


if __name__ == "__main__":
    main()
