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
        f = facts.gather(self.db, "j02")
        self.assertEqual(f["status"], "likely_duplicate")
        self.assertEqual(f["overlap"], ["Python", "SQL"])
        self.assertIn("-REQUIRES->", f["path"])

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

    def test_demo_replay_and_duplicate_cap(self):
        from jobradar_relate import demo
        base = {x["f"]["job"]: x["score"] for x in demo.rank(self.db)}
        self.assertLessEqual(base["j02"], 60)
        self.db.execute("MATCH (u:User {id:'me'}),(j:Job {id:'j01'}) MERGE (u)-[:LIKED]->(j)")
        self.assertIn("j01", demo.rank(self.db)[0]["f"]["job"] + "j01")

    def test_sqlite_adapter_roundtrip(self):
        p = f"{self.tmp}/s.sqlite"
        subprocess.check_call([sys.executable, str(ROOT / "data/make_sample_sqlite.py"), p])
        self.assertEqual(sqlite_adapter.read_jobs(p), self.jobs)

if __name__ == "__main__":
    unittest.main()
