import json, pathlib, shutil, sqlite3, subprocess, sys, tempfile, unittest
import relate
from jobradar_relate import importer, facts, score, sqlite_adapter

ROOT = pathlib.Path(__file__).resolve().parent.parent

class Pipeline(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.db = relate.connect(f"{self.tmp}/t.rl")
        with open(ROOT / "data/sample_jobs.json") as fh: self.jobs = json.load(fh)
        importer.import_jobs(self.db, self.jobs)
        self.db.execute("MERGE (u:User {id:'me'})")
        for s in ("Python", "SQL"):
            self.db.execute("MATCH (u:User {id:'me'}),(k:Skill {name:$s}) MERGE (u)-[:HAS_SKILL]->(k)", {"s": s})
    def tearDown(self):
        self.db.close(); shutil.rmtree(self.tmp)

    def test_idempotent(self):
        importer.import_jobs(self.db, self.jobs)
        n = list(self.db.execute("MATCH (j:Job) RETURN count(*) AS n"))[0]["n"]
        self.assertEqual(n, 10)

    def test_duplicate_detected(self):
        self.assertEqual(facts.gather(self.db, "j02")["status"], "new")
        self.db.execute("MATCH (u:User {id:'me'}),(j:Job {id:'j01'}) MERGE (u)-[:SEEN]->(j)")
        self.assertEqual(facts.gather(self.db, "j01")["status"], "seen")
        self.assertEqual(facts.gather(self.db, "j02", "someone_else")["status"], "new")
        f = facts.gather(self.db, "j02")
        self.assertEqual(f["status"], "likely_duplicate")
        self.assertEqual(f["overlap"], ["Python", "SQL"])
        self.assertIn("-REQUIRES->", f["path"])

    def test_search_shortlist_and_no_matches(self):
        from jobradar_relate.discover import discover
        for statement in (ROOT / "graph/profile.cypher").read_text().splitlines():
            if statement and not statement.startswith("//"):
                self.db.execute(statement)
        hits, rows = discover(self.db, "engineer")
        self.assertEqual(hits, 5)
        self.assertEqual([r["facts"]["job"] for r in rows], ["j04", "j08", "j02"])
        self.assertEqual(discover(self.db, "volcanologist"), (0, []))
        self.assertEqual(len(discover(self.db, "engineer", "another-profile")[1]), 5)

    def test_score_range(self):
        r = score.recommend(self.db, "j02")
        self.assertTrue(0 <= r["score"] <= 100)
        self.assertEqual(r["scorer"], "fallback")

    def test_llm_output_validated(self):
        f = facts.gather(self.db, "j02")
        ok = score.validate({"score": 70, "explanation": "2 of 3 skills match and j01 is similar.", "status": "new", "salary": 9}, f)
        self.assertEqual(set(ok), {"score", "explanation"})
        for bad in ({"score": 101, "explanation": "x"}, {"score": 5, "explanation": "pays 90000 DKK"}, {"score": 5, "explanation": "like j99"}):
            with self.assertRaises(ValueError): score.validate(bad, f)

    def test_cross_batch_and_no_reciprocal(self):
        db = relate.connect(f"{self.tmp}/b.rl")
        importer.import_jobs(db, self.jobs[:1])
        importer.import_jobs(db, list(reversed(self.jobs[1:2])))   # j02 arrives in a later batch
        r = [x.data() for x in db.execute("MATCH (a:Job)-[r:SIMILAR_TO]-(b:Job) RETURN a.id AS a, b.id AS b")]
        self.assertEqual(len(r), 2)                                # one edge, seen from both ends
        n = list(db.execute("MATCH ()-[r:SIMILAR_TO]->() RETURN count(*) AS n"))[0]["n"]
        self.assertEqual(n, 1); db.close()

    def _context(self):
        for q in ("MATCH (u:User {id:'me'}) UNWIND ['j01','j05'] AS id MATCH (j:Job {id:id}) MERGE (u)-[:SEEN]->(j)",
                  "MATCH (a:Skill {name:'SQL'}),(b:Skill {name:'dbt'}) MERGE (a)-[:RELATED_TO]->(b)",
                  "MATCH (u:User {id:'me'}),(j:Job {id:'j05'}) MERGE (u)-[:DISMISSED]->(j)",
                  "MATCH (u:User {id:'me'}),(j:Job {id:'j01'}) MERGE (u)-[:LIKED]->(j)"):
            self.db.execute(q)

    def test_same_day_has_no_publication_order(self):
        self._context()
        self.assertEqual(facts.gather(self.db, "j06")["status"], "similar_seen")
        self.assertEqual(facts.gather(self.db, "j05")["status"], "seen")

    def test_related_skill_changes_score(self):
        before = score.fallback(facts.gather(self.db, "j01"))["score"]
        self.db.execute("MATCH (a:Skill {name:'SQL'}),(b:Skill {name:'dbt'}) MERGE (a)-[:RELATED_TO]->(b)")
        f = facts.gather(self.db, "j01")
        self.assertEqual(f["related"], [{"skill": "dbt", "via": "SQL"}])
        self.assertEqual(score.fallback(f)["score"], before + 5)

    def test_replay_moves_exactly_the_expected_job(self):
        from jobradar_relate import demo
        self._context(); self.db.close()
        path = f"{self.tmp}/t.rl"
        shutil.copy(path, f"{self.tmp}/c.rl")
        db = relate.connect(f"{self.tmp}/c.rl"); base = {x["f"]["job"]: x["score"] for x in demo.rank(db)}; db.close()
        after = {x["f"]["job"]: x["score"] for x in demo.replay(path, "j05", "LIKED")}
        self.assertLessEqual(base["j02"], 60)                      # duplicate cap
        changed = {j for j in base if base[j] != after[j]}
        self.assertEqual(changed, {"j05", "j06"})                  # only the flipped job and its repost
        self.assertEqual(after["j05"] - base["j05"], 35)           # dismissed(-25) -> liked(+10)
        self.assertGreater(after["j06"], base["j06"])
        self.db = relate.connect(path)

    def test_sqlite_adapter_roundtrip(self):
        p = f"{self.tmp}/s.sqlite"
        subprocess.check_call([sys.executable, str(ROOT / "data/make_sample_sqlite.py"), p])
        self.assertEqual(sqlite_adapter.read_jobs(p), self.jobs)

if __name__ == "__main__":
    unittest.main()
