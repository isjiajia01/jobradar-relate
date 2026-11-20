import json, pathlib, shutil, sqlite3, subprocess, sys, tempfile, unittest
import relate
from jobradar_relate import importer, facts, score, sqlite_adapter

ROOT = pathlib.Path(__file__).resolve().parent.parent

class Pipeline(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.db = relate.connect(f"{self.tmp}/t.rl")
        self.jobs = json.load(open(ROOT / "data/sample_jobs.json"))
        importer.import_jobs(self.db, self.jobs)
        self.db.execute("MERGE (u:User {id:'me'})")
        for s in ("Python", "SQL"):
            self.db.execute("MATCH (u:User {id:'me'}),(k:Skill {name:$s}) MERGE (u)-[:HAS_SKILL]->(k)", {"s": s})
    def tearDown(self):
        self.db.close(); shutil.rmtree(self.tmp)

    def test_idempotent(self):
        importer.import_jobs(self.db, self.jobs)
        n = list(self.db.execute("MATCH (j:Job) RETURN count(*) AS n"))[0]["n"]
        self.assertEqual(n, 6)

    def test_duplicate_detected(self):
        f = facts.gather(self.db, "j02")
        self.assertEqual(f["status"], "likely_duplicate")
        self.assertEqual(f["overlap"], ["Python", "SQL"])
        self.assertIn("-REQUIRES->", f["path"])

    def test_score_range(self):
        r = score.recommend(self.db, "j02")
        self.assertTrue(0 <= r["score"] <= 100)
        self.assertEqual(r["scorer"], "fallback")

    def test_sqlite_adapter_roundtrip(self):
        p = f"{self.tmp}/s.sqlite"
        subprocess.check_call([sys.executable, str(ROOT / "data/make_sample_sqlite.py"), p])
        self.assertEqual(sqlite_adapter.read_jobs(p), self.jobs)

if __name__ == "__main__":
    unittest.main()
