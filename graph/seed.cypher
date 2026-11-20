// SYNTHETIC example data only. No real jobs, people or feedback.
UNWIND [
 {id:'j01',title:'Data Engineer',company:'Nordlys Analytics',loc:'Copenhagen',source:'jobindex',posted:'2026-11-10',skills:['Python','SQL','dbt']},
 {id:'j02',title:'Data Engineer',company:'Nordlys Analytics',loc:'Copenhagen',source:'linkedin',posted:'2026-11-11',skills:['Python','SQL','Airflow']},
 {id:'j03',title:'Analytics Engineer',company:'Nordlys Analytics',loc:'Copenhagen',source:'jobnet',posted:'2026-11-12',skills:['SQL','dbt']},
 {id:'j04',title:'ML Engineer',company:'Fjord Robotics',loc:'Aarhus',source:'jobindex',posted:'2026-11-09',skills:['Python','PyTorch','Docker']},
 {id:'j05',title:'Backend Developer',company:'Havn Pay',loc:'Copenhagen',source:'linkedin',posted:'2026-11-13',skills:['Java','SQL','Docker']},
 {id:'j06',title:'Backend Developer',company:'Havn Pay',loc:'Copenhagen',source:'jobnet',posted:'2026-11-13',skills:['Java','SQL','Kubernetes']},
 {id:'j07',title:'Data Scientist',company:'Kyst Energy',loc:'Odense',source:'jobindex',posted:'2026-11-08',skills:['Python','SQL','Statistics']},
 {id:'j08',title:'DevOps Engineer',company:'Fjord Robotics',loc:'Aarhus',source:'linkedin',posted:'2026-11-14',skills:['Docker','Kubernetes','Terraform']},
 {id:'j09',title:'Python Developer',company:'Bryggen Labs',loc:'Copenhagen',source:'jobindex',posted:'2026-11-15',skills:['Python','Docker','SQL']},
 {id:'j10',title:'Data Analyst',company:'Kyst Energy',loc:'Odense',source:'jobnet',posted:'2026-11-07',skills:['SQL','Statistics','Excel']}
] AS j
MERGE (c:Company {name:j.company}) MERGE (l:Location {name:j.loc})
MERGE (job:Job {id:j.id}) SET job.title=j.title, job.source=j.source, job.posted_date=j.posted, job.url='https://example.invalid/jobs/'+j.id
MERGE (c)-[:POSTED]->(job) MERGE (job)-[:AT]->(c) MERGE (job)-[:IN]->(l)
WITH job, j UNWIND j.skills AS s MERGE (k:Skill {name:s}) MERGE (job)-[:REQUIRES]->(k);
MERGE (u:User {id:'me'});
MATCH (u:User {id:'me'}) UNWIND ['Python','SQL','Docker'] AS s MATCH (k:Skill {name:s}) MERGE (u)-[:HAS_SKILL]->(k);
MATCH (a:Skill {name:'SQL'}),(b:Skill {name:'dbt'}) MERGE (a)-[:RELATED_TO]->(b);
MATCH (a:Skill {name:'Docker'}),(b:Skill {name:'Kubernetes'}) MERGE (a)-[:RELATED_TO]->(b);
UNWIND [['j01','j02',0.92],['j05','j06',0.95],['j01','j03',0.7]] AS p MATCH (a:Job {id:p[0]}),(b:Job {id:p[1]}) MERGE (a)-[:SIMILAR_TO {score:p[2]}]->(b);
MATCH (u:User {id:'me'}) UNWIND ['j01','j03'] AS i MATCH (j:Job {id:i}) MERGE (u)-[:LIKED]->(j);
MATCH (u:User {id:'me'}) MATCH (j:Job {id:'j05'}) MERGE (u)-[:DISMISSED]->(j);
