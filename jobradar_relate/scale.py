"""Benchmark the Jobradar graph pipeline on seeded synthetic listings."""
import argparse
from contextlib import closing
from datetime import date, timedelta
from pathlib import Path
from random import Random
from tempfile import TemporaryDirectory
from time import perf_counter

import relate

from .demo import rank, replay, score_changes, score_job
from .discover import discover
from .facts import DUP_SCORE
from .importer import import_jobs

SEED = 42
BOARDS = ("jobindex", "linkedin", "jobnet")
COMPANIES = tuple(
    f"Synthetic {name} {sector}"
    for name in ("Birch", "Cedar", "Elm", "Maple", "Pine", "Spruce")
    for sector in ("Analytics", "Energy", "Logistics", "Robotics", "Software")
)
LOCATIONS = ("Copenhagen", "Aarhus", "Odense", "Aalborg")
ROLES = (
    ("Data Engineer", ("Python", "SQL", "Docker")),
    ("Analytics Engineer", ("SQL", "dbt", "Kubernetes")),
    ("ML Engineer", ("Python", "PyTorch", "Docker")),
    ("Backend Developer", ("Java", "SQL", "Kubernetes")),
    ("Data Scientist", ("Python", "SQL", "Statistics")),
    ("DevOps Engineer", ("Docker", "Kubernetes", "Terraform")),
    ("Frontend Developer", ("TypeScript", "React", "CSS")),
    ("Data Analyst", ("SQL", "Excel", "Statistics")),
)
PROFILE = Path(__file__).resolve().parents[1] / "graph" / "profile.cypher"


def generate_jobs(count, seed=SEED):
    """Return jobs in the sample JSON schema, with reposts at j02, j12, and so on."""
    if count < 1:
        raise ValueError("N must be a positive integer")
    rng = Random(seed)
    jobs = []
    for index in range(count):
        job_id = f"j{index + 1:02d}"
        if index % 10 == 1:
            original = jobs[-1]
            source = BOARDS[(BOARDS.index(original["source"]) + 1) % len(BOARDS)]
            posted = date.fromisoformat(original["posted_date"]) + timedelta(days=1)
            job = {**original, "skills": original["skills"].copy()}
        else:
            source = BOARDS[index % len(BOARDS)]
            posted = date(2026, 11, 1) + timedelta(days=rng.randrange(30))
            company = rng.choice(COMPANIES)
            location = rng.choice(LOCATIONS)
            title, skills = rng.choice(ROLES)
            if index == 0:
                # The stock profile sees and likes j01, making j02 a likely duplicate.
                title, skills = ROLES[0]
            elif index == 2:
                # The stock profile links j01 and j03 as related roles at one company.
                title, skills = ROLES[1]
                company, source = jobs[0]["company"], jobs[0]["source"]
            job = {"title": title, "company": company, "location": location, "skills": list(skills)}
        jobs.append({**job, "id": job_id, "source": source, "posted_date": posted.isoformat(),
                     "url": f"https://{source}.example.invalid/jobs/{job_id}"})
    return jobs


def benchmark(count):
    jobs = generate_jobs(count)
    with TemporaryDirectory(dir="/tmp", prefix="jobradar-scale-") as tmp:
        path = str(Path(tmp) / "scale.rl")
        started = perf_counter()
        with closing(relate.connect(path)) as db:
            imported, links = import_jobs(db, jobs)
            for statement in PROFILE.read_text(encoding="utf-8").splitlines():
                if statement.strip() and not statement.lstrip().startswith("//"):
                    db.execute(statement)
            import_time = perf_counter() - started

            started = perf_counter()
            base = rank(db)
            rank_time = perf_counter() - started

            why_id = jobs[min(1, len(jobs) - 1)]["id"]
            started = perf_counter()
            why = score_job(db, why_id)
            why_time = perf_counter() - started

            started = perf_counter()
            hits, shortlist = discover(db, "engineer")
            search_time = perf_counter() - started

            nodes = next(iter(db.execute("MATCH (n) RETURN count(*) AS n")))["n"]
            edges = next(iter(db.execute("MATCH ()-[r]->() RETURN count(*) AS n")))["n"]
            repost_pairs = next(iter(db.execute("""
                MATCH (a:Job)-[r:SIMILAR_TO]->(b:Job)
                WHERE r.score >= $threshold AND a.source <> b.source
                RETURN count(*) AS n
            """, {"threshold": DUP_SCORE})))["n"]

        replay_id = jobs[0]["id"]
        started = perf_counter()
        after = replay(path, replay_id, "DISMISSED", temp_dir=tmp)
        changed = sum(1 for _ in score_changes(base, after))
        replay_time = perf_counter() - started

    duplicates = sum(row["f"]["status"] == "likely_duplicate" for row in base)
    print(f"Synthetic scale: {len(jobs)} jobs, seed {SEED}")
    print(f"Import + profile: {import_time:.6f} s ({imported} jobs, {links} importer similarity links)")
    print(f"Rank: {rank_time:.6f} s ({len(base)} jobs)")
    print(f"Why: {why_time:.6f} s ({why_id}, score {why['score']}, {why['f']['status']})")
    print(f"Replay: {replay_time:.6f} s ({replay_id} DISMISSED, {changed} changed scores)")
    print(f"SEARCH: {search_time:.6f} s (engineer, {hits} title hits, {len(shortlist)} unseen)")
    print(f"Graph: {nodes} nodes, {edges} edges, {repost_pairs} detected repost pairs, "
          f"{duplicates} marked likely_duplicate by the profile")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("count", type=int, metavar="N")
    args = parser.parse_args()
    if args.count < 1:
        parser.error("N must be a positive integer")
    benchmark(args.count)


if __name__ == "__main__":
    main()
