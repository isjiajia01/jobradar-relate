// SYNTHETIC profile for the real Djinni catalog (make real). The jobs are real public postings; the profile is invented.
MERGE (u:User {id:'me'});
MATCH (u:User {id:'me'}) UNWIND ['Python','SQL','Docker','Spark'] AS s MATCH (k:Skill {name:s}) MERGE (u)-[:HAS_SKILL]->(k);
MATCH (a:Skill {name:'Spark'}),(b:Skill {name:'Hadoop'}) MERGE (a)-[:RELATED_TO]->(b);
MATCH (a:Skill {name:'Docker'}),(b:Skill {name:'Kubernetes'}) MERGE (a)-[:RELATED_TO]->(b);
CREATE FULLTEXT INDEX job_titles IF NOT EXISTS FOR (j:Job) ON EACH [j.title];
MATCH (u:User {id:'me'}) SET u.skill_basis='count', u.excluded_titles=['manager','management','director','head of','architect','cto','chief technology officer'];
MATCH (u:User {id:'me'}) UNWIND ['Java','Scala'] AS name MERGE (k:Skill {name:name}) MERGE (u)-[:AVOIDS]->(k);
