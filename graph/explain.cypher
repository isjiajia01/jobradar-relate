// Standalone version of the scorer's facts (same semantics as jobradar_relate/facts.py).
// Usage: relate query --database ./jobradar.rl --read-only --mode envelope --param job=j02 "$(cat graph/explain.cypher)"
MATCH (j:Job {id:$job})-[:AT]->(c:Company)
OPTIONAL MATCH (j)-[:REQUIRES]->(s:Skill)
OPTIONAL MATCH (me:User {id:'me'})-[h:HAS_SKILL]->(s)
WITH j, c, collect(DISTINCT s.name) AS required, collect(DISTINCT CASE WHEN h IS NOT NULL THEN s.name END) AS overlap
OPTIONAL MATCH (j)-[:SIMILAR_TO]-(o:Job)-[:AT]->(c)
OPTIONAL MATCH (:User {id:'me'})-[:LIKED]->(lo:Job) WHERE lo = o
OPTIONAL MATCH (:User {id:'me'})-[:DISMISSED]->(dis:Job) WHERE dis = o
RETURN j.id AS job, c.name AS company, required, overlap,
       count(DISTINCT lo) AS liked_similar, count(DISTINCT dis) AS dismissed_similar LIMIT 1
