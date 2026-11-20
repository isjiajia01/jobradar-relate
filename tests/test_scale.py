import hashlib
import json
from pathlib import Path
import re
import subprocess
import unittest

from jobradar_relate.scale import generate_jobs

ROOT = Path(__file__).resolve().parents[1]


class ScaleTests(unittest.TestCase):
    def test_generator_is_seeded_and_matches_sample_schema(self):
        jobs = generate_jobs(12)
        self.assertEqual(jobs, generate_jobs(12, seed=42))
        self.assertNotEqual(jobs, generate_jobs(12, seed=43))
        self.assertEqual(len(jobs), 12)
        self.assertEqual(len({job["id"] for job in jobs}), 12)
        self.assertGreaterEqual(len({job["company"] for job in jobs}), 3)
        self.assertEqual(len({job["source"] for job in jobs}), 3)
        sample = json.loads((ROOT / "data/sample_jobs.json").read_text(encoding="utf-8"))[0]
        for job in jobs:
            self.assertEqual(set(job), set(sample))
            for field, value in sample.items():
                self.assertIsInstance(job[field], type(value))
        original, repost = jobs[:2]
        self.assertNotEqual(original["source"], repost["source"])
        self.assertLess(original["posted_date"], repost["posted_date"])
        for key in ("title", "company", "location", "skills"):
            self.assertEqual(original[key], repost[key])

    def test_make_scale_reports_sanity_without_changing_shipped_store(self):
        store = ROOT / "jobradar.rl"
        before = hashlib.sha256(store.read_bytes()).digest()
        result = subprocess.run(["make", "scale", "N=12"], cwd=ROOT, capture_output=True,
                                text=True, timeout=30)
        self.assertEqual(hashlib.sha256(store.read_bytes()).digest(), before)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Synthetic scale: 12 jobs, seed 42", result.stdout)
        for stage in ("Import + profile", "Rank", "Why", "Replay", "SEARCH"):
            self.assertRegex(result.stdout, rf"(?m)^{re.escape(stage)}: \d+\.\d+ s ")
        self.assertIn("(12 jobs)", result.stdout)
        self.assertIn("j02, score 60, likely_duplicate", result.stdout)
        self.assertIn("j01 DISMISSED, 3 changed scores", result.stdout)
        self.assertIn("engineer, 6 title hits, 4 unseen", result.stdout)
        self.assertIn("35 nodes, 87 edges, 2 detected repost pairs, 1 marked likely_duplicate by the profile", result.stdout)
