"""Read jobs from a SQLite file (synthetic schema, see data/make_sample_sqlite.py) into importer dicts."""
import sqlite3, sys, json

def read_jobs(path):
    con = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    jobs = []
    for r in con.execute("SELECT id,title,company,location,source,url,posted_date,skills FROM jobs ORDER BY id"):
        d = dict(r)
        d["skills"] = [s.strip() for s in (d["skills"] or "").split(",") if s.strip()]
        jobs.append(d)
    con.close()
    return jobs

if __name__ == "__main__":
    print(json.dumps(read_jobs(sys.argv[1]), indent=1))
