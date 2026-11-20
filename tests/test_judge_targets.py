import hashlib
from pathlib import Path
import re
import subprocess
import unittest


ROOT = Path(__file__).resolve().parents[1]
STORE = ROOT / "jobradar.rl"


class JudgeTargets(unittest.TestCase):
    def run_make(self, *args, success=True):
        before = hashlib.sha256(STORE.read_bytes()).digest()
        result = subprocess.run(["make", *args], cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(hashlib.sha256(STORE.read_bytes()).digest(), before)
        if success:
            self.assertEqual(result.returncode, 0, result.stderr)
            return result.stdout
        self.assertNotEqual(result.returncode, 0)
        return result.stderr

    def test_replay_reports_every_changed_score_and_path(self):
        output = self.run_make("replay", "JOB=j05", "VERDICT=LIKED")
        self.assertEqual(re.findall(r"^j\d+ \d+ -> \d+$", output, re.M), ["j05 45 -> 80", "j06 50 -> 75"])
        self.assertIn("own verdict: LIKED", output)
        self.assertIn("User -LIKED-> j05 -SIMILAR_TO(0.8)-> j06", output)

    def test_seen_preserves_existing_feedback(self):
        self.assertIn("No scores changed.", self.run_make("replay", "JOB=j05", "VERDICT=SEEN"))

    def test_dismiss_another_job(self):
        self.assertIn("own verdict: DISMISSED", self.run_make("replay", "JOB=j04", "VERDICT=DISMISSED"))

    def test_why(self):
        output = self.run_make("why", "JOB=j06")
        self.assertIn("j06 score 50", output)
        self.assertIn("-15 dismissed similar x1", output)
        self.assertIn("User -DISMISSED-> j05 -SIMILAR_TO(0.8)-> j06", output)

    def test_unknown_job(self):
        for target in ("why", "replay"):
            with self.subTest(target=target):
                self.assertIn("unknown JOB 'missing'", self.run_make(target, "JOB=missing", success=False))

    def test_unknown_verdict(self):
        error = self.run_make("replay", "JOB=j05", "VERDICT=SKIPPED", success=False)
        self.assertIn("invalid VERDICT 'SKIPPED' (choose LIKED|DISMISSED|SEEN)", error)
