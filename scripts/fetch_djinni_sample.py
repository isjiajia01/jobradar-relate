"""Re-create data/real/djinni50.json from the public Djinni dataset (MIT) via the Hugging Face rows API.
Stdlib only; reads 8 chunks of 100 rows (not the full dataset). Usage: python3 scripts/fetch_djinni_sample.py data/real/djinni50.json"""
import json, random, re, sys, urllib.request
URL = ("https://datasets-server.huggingface.co/rows?dataset=lang-uk/recruitment-dataset-job-descriptions-english"
       "&config=default&split=train&offset=%d&length=100")
VOCAB = ["Python","Java","JavaScript","TypeScript","Scala","Ruby","Go","C++","C#",".NET","SQL","PostgreSQL","MySQL","MongoDB","Redis","Kafka","Spark","Airflow","dbt","Docker","Kubernetes","AWS","Azure","GCP","Terraform","React","Node.js","Django","Spring","Rails","Pandas","PyTorch","TensorFlow","Git","Linux","REST","GraphQL","Snowflake","Hadoop","Machine Learning"]
TECH = {"Java","Ruby","Scala","Python","JavaScript","Data Science","Data Engineer",".NET","C++","Sysadmin","Lead"}

def skills(text):
    return [s for s in VOCAB if re.search(r"(?<![A-Za-z0-9])" + re.escape(s) + r"(?![A-Za-z0-9+#])", text, re.I if len(s) > 3 else 0)]

def main(out):
    rng, rows = random.Random(7), []
    for off in sorted(rng.sample(range(0, 141800, 100), 8)):
        rows += [r["row"] for r in json.load(urllib.request.urlopen(URL % off, timeout=60))["rows"]]
    jobs, seen = [], set()
    for r in rows:
        sk = skills(r["Position"] + " " + r["Long Description"])
        if r["Primary Keyword"] in TECH and len(sk) >= 2 and r["Long Description_lang"] == "en" and r["Company Name"] not in seen:
            seen.add(r["Company Name"])
            jobs.append({"id": f"d{len(jobs)+1:02d}", "title": r["Position"][:80], "company": r["Company Name"], "location": "Remote",
                         "source": "djinni", "posted_date": r["Published"][:10], "skills": sk,
                         "url": "https://huggingface.co/datasets/lang-uk/recruitment-dataset-job-descriptions-english#" + r["id"]})
        if len(jobs) == 50: break
    json.dump(jobs, open(out, "w"), indent=1)

if __name__ == "__main__":
    main(sys.argv[1])
