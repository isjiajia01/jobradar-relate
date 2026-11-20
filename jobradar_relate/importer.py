"""Upsert Jobradar jobs into a Relate graph (idempotent, MERGE only, never deletes)."""
import json, re, sys
import relate

def norm(s): return re.sub(r"[^a-z0-9]+", " ", s.lower()).strip()

def similarity(a, b):
    """Cross-source near-duplicate score: same company required; title + skill overlap."""
    if norm(a["company"]) != norm(b["company"]): return 0.0
    sa, sb = {s.lower() for s in a["skills"]}, {s.lower() for s in b["skills"]}
    jac = len(sa & sb) / len(sa | sb) if sa | sb else 0.0
    ta, tb = set(norm(a["title"]).split()), set(norm(b["title"]).split())
    tj = len(ta & tb) / len(ta | tb) if ta | tb else 0.0
    return round(0.6 * tj + 0.4 * jac, 2)

UPSERT = """
MERGE (c:Company {name:$company}) MERGE (l:Location {name:$location})
MERGE (j:Job {id:$id})
SET j.title=$title, j.url=$url, j.source=$source, j.posted_date=$posted_date
MERGE (c)-[:POSTED]->(j) MERGE (j)-[:AT]->(c) MERGE (j)-[:IN]->(l)
WITH j UNWIND $skills AS s MERGE (k:Skill {name:s}) MERGE (j)-[:REQUIRES]->(k)
"""
LINK = """MATCH (a:Job {id:$a}),(b:Job {id:$b})
MERGE (a)-[r:SIMILAR_TO]->(b) SET r.score=$score"""

STORED = """MATCH (j:Job)-[:AT]->(c:Company) OPTIONAL MATCH (j)-[:REQUIRES]->(k:Skill)
RETURN j.id AS id, j.title AS title, j.source AS source, c.name AS company, collect(k.name) AS skills LIMIT 10000"""

def import_jobs(db, jobs, threshold=0.6):
    """Upsert jobs, then link each new job to ALL stored jobs (not just this batch).
    Edges point from the smaller id to the larger id, so re-imports never create reciprocal pairs."""
    for j in jobs:
        db.execute(UPSERT, {**{k: j[k] for k in ("id","title","url","source","posted_date","company","location")}, "skills": j["skills"]})
    stored = [dict(r.data()) for r in db.execute(STORED)]
    new_ids = {j["id"] for j in jobs}
    links = 0
    for i, a in enumerate(stored):
        for b in stored[i+1:]:
            if a["id"] not in new_ids and b["id"] not in new_ids: continue
            if a["source"] != b["source"] and (sc := similarity(a, b)) >= threshold:
                lo, hi = sorted((a["id"], b["id"]))
                db.execute(LINK, {"a": lo, "b": hi, "score": sc}); links += 1
    return len(jobs), links

if __name__ == "__main__":
    path, dbpath = sys.argv[1], sys.argv[2]
    db = relate.connect(dbpath)
    print("jobs, similar_links =", import_jobs(db, json.load(open(path))))
    db.close()
