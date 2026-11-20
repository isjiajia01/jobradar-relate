"""Build a synthetic SQLite file (jobs table) from data/sample_jobs.json. Usage: make_sample_sqlite.py OUT.sqlite"""
import json, sqlite3, sys, pathlib
src = json.load(open(pathlib.Path(__file__).with_name("sample_jobs.json")))
con = sqlite3.connect(sys.argv[1])
con.execute("CREATE TABLE IF NOT EXISTS jobs(id TEXT PRIMARY KEY,title,company,location,source,url,posted_date,skills)")
for j in src:
    con.execute("INSERT OR REPLACE INTO jobs VALUES(?,?,?,?,?,?,?,?)",
        (j["id"],j["title"],j["company"],j["location"],j["source"],j["url"],j["posted_date"],",".join(j["skills"])))
con.commit(); con.close()
