MATCH (j:Job {id:$job})-[:AT]->(c:Company)
OPTIONAL MATCH (j)-[:REQUIRES]->(s:Skill)
OPTIONAL MATCH (:User {id:'me'})-[:HAS_SKILL]->(s)
WITH j, c, collect(DISTINCT s.name) AS required, collect(DISTINCT CASE WHEN EXISTS { (:User {id:'me'})-[:HAS_SKILL]->(s) } THEN s.name END) AS overlap
OPTIONAL MATCH (c)-[:POSTED]->(o:Job) WHERE o <> j
OPTIONAL MATCH (:User {id:'me'})-[:LIKED]->(o2:Job) WHERE o2 = o
OPTIONAL MATCH (:User {id:'me'})-[:DISMISSED]->(o3:Job) WHERE o3 = o
WITH j, c, required, overlap, count(DISTINCT o2) AS liked_at_company, count(DISTINCT o3) AS dismissed_at_company
OPTIONAL MATCH (j)-[r:SIMILAR_TO]-(d:Job)
WITH j, c, required, overlap, liked_at_company, dismissed_at_company, collect(DISTINCT {id:d.id, source:d.source, score:r.score}) AS dups
RETURN j.id AS job, j.title AS title, required, overlap, liked_at_company, dismissed_at_company, dups,
  j.title + ' -REQUIRES-> ' + toString(required) + '; User has ' + toString(overlap)
  + '; User -LIKED-> ' + toString(liked_at_company) + ' / -DISMISSED-> ' + toString(dismissed_at_company)
  + ' other jobs at ' + c.name AS path
LIMIT 1
