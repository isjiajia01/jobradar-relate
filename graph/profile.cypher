// SYNTHETIC profile layer applied after the job import (make import). Idempotent, MERGE only.
MERGE (u:User {id:'me'});
MATCH (u:User {id:'me'}) UNWIND ['Python','SQL','Docker'] AS s MATCH (k:Skill {name:s}) MERGE (u)-[:HAS_SKILL]->(k);
MATCH (a:Skill {name:'SQL'}),(b:Skill {name:'dbt'}) MERGE (a)-[:RELATED_TO]->(b);
MATCH (a:Skill {name:'Docker'}),(b:Skill {name:'Kubernetes'}) MERGE (a)-[:RELATED_TO]->(b);
// hand-curated similar pair (different titles, same team) to show a weaker link
MATCH (a:Job {id:'j01'}),(b:Job {id:'j03'}) MERGE (a)-[r:SIMILAR_TO]->(b) SET r.score=0.7;
MATCH (u:User {id:'me'}) UNWIND ['j01','j03'] AS i MATCH (j:Job {id:i}) MERGE (u)-[:LIKED]->(j);
MATCH (u:User {id:'me'}) MATCH (j:Job {id:'j05'}) MERGE (u)-[:DISMISSED]->(j);
MATCH (u:User {id:'me'}) UNWIND ['j01','j03','j05','j10'] AS i MATCH (j:Job {id:i}) MERGE (u)-[:SEEN]->(j);
CREATE FULLTEXT INDEX job_titles IF NOT EXISTS FOR (j:Job) ON EACH [j.title];
