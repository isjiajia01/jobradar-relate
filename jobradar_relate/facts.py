"""The four graph queries run BEFORE LLM scoring. Read-only; values bound as parameters."""
Q1 = """MATCH (j:Job {id:$id})-[:REQUIRES]->(s:Skill)
OPTIONAL MATCH (:User {id:$user})-[h:HAS_SKILL]->(s)
RETURN s.name AS skill, h IS NOT NULL AS have ORDER BY skill LIMIT 50"""
# Q2: only jobs at the SAME company that are SIMILAR_TO this job, and my verdict on them.
Q2 = """MATCH (j:Job {id:$id})-[:SIMILAR_TO]-(o:Job)-[:AT]->(:Company)<-[:AT]-(j)
OPTIONAL MATCH (:User {id:$user})-[f:LIKED|DISMISSED]->(o)
RETURN o.id AS id, type(f) AS verdict ORDER BY id LIMIT 50"""
Q3 = """MATCH (j:Job {id:$id})-[r:SIMILAR_TO]-(d:Job)
RETURN d.id AS id, d.source AS source, r.score AS score ORDER BY score DESC, id LIMIT 10"""
Q4 = """MATCH (j:Job {id:$id})-[:AT]->(c:Company) RETURN j.title AS title, j.source AS source, c.name AS company LIMIT 1"""
# Q5: required skills I lack but that are RELATED_TO a skill I have (either direction)
Q5 = """MATCH (j:Job {id:$id})-[:REQUIRES]->(s:Skill)
MATCH (s)-[:RELATED_TO]-(m:Skill)<-[:HAS_SKILL]-(:User {id:$user})
WHERE NOT EXISTS { (:User {id:$user})-[:HAS_SKILL]->(s) }
RETURN DISTINCT s.name AS skill, m.name AS via ORDER BY skill, via LIMIT 50"""
# Q6: my own verdict on this very job
Q6 = """MATCH (:User {id:$user})-[f:LIKED|DISMISSED]->(:Job {id:$id}) RETURN type(f) AS verdict LIMIT 1"""
DUP_SCORE = 0.8

def _rows(db, q, p): return [dict(r.data()) for r in db.execute(q, p)]

def gather(db, job_id, user="me"):
    p = {"id": job_id, "user": user}
    head = _rows(db, Q4, p)
    if not head: raise KeyError(job_id)
    skills = _rows(db, Q1, p)
    required = [s["skill"] for s in skills]
    overlap = [s["skill"] for s in skills if s["have"]]
    related = _rows(db, Q5, p)
    own = (_rows(db, Q6, p) or [{}])[0].get("verdict")
    sim = _rows(db, Q2, p)
    liked = [r["id"] for r in sim if r["verdict"] == "LIKED"]
    dismissed = [r["id"] for r in sim if r["verdict"] == "DISMISSED"]
    links = _rows(db, Q3, p)
    dup = [l for l in links if l["score"] >= DUP_SCORE and l["source"] != head[0]["source"]]
    status = "likely_duplicate" if dup else ("similar_seen" if links else "new")
    h = head[0]
    wt = {l["id"]: l["score"] for l in links}
    hops = [{"verdict": r["verdict"], "via": r["id"], "weight": wt.get(r["id"]),
             "text": f"User -{r['verdict']}-> {r['id']} -SIMILAR_TO({wt.get(r['id'])})-> {job_id} (same company: {h['company']})"}
            for r in sim if r["verdict"]]
    hops += [{"verdict": "RELATED_TO", "via": r["via"], "weight": None,
              "text": f"{job_id} -REQUIRES-> {r['skill']} -RELATED_TO- {r['via']} <-HAS_SKILL- User"} for r in related]
    path = (f"{h['title']}@{h['company']} -REQUIRES-> {', '.join(required) or 'none'}; "
            f"User -HAS_SKILL-> {', '.join(overlap) or 'none'}; "
            f"{'own verdict: ' + own + '; ' if own else ''}"
            f"{'related: ' + ', '.join(r['skill'] + ' ~ ' + r['via'] for r in related) + '; ' if related else ''}"
            f"User -LIKED-> {len(liked)} / -DISMISSED-> {len(dismissed)} similar jobs at same company; "
            f"-SIMILAR_TO-> {', '.join(l['id'] + ' (' + l['source'] + ', ' + str(l['score']) + ')' for l in links) or 'none'} => {status}")
    return {"job": job_id, **h, "required": required, "overlap": overlap, "related": related, "own": own, "liked_similar": liked,
            "dismissed_similar": dismissed, "similar_links": links, "status": status, "path": path, "hops": hops}
