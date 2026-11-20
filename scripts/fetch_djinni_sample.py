"""Re-create data/real/djinni50.json from the public Djinni dataset (MIT) via the Hugging Face rows API.
Stdlib only; reads 100-row chunks until 50 eligible jobs are found. Usage: python3 scripts/fetch_djinni_sample.py data/real/djinni50.json"""
import argparse, json, random, re, urllib.request
from pathlib import Path
URL = ("https://datasets-server.huggingface.co/rows?dataset=lang-uk/recruitment-dataset-job-descriptions-english"
       "&config=default&split=train&offset=%d&length=100")
VOCAB = ["Python","Java","JavaScript","TypeScript","Scala","Ruby","Go","C++","C#",".NET","SQL","PostgreSQL","MySQL","MongoDB","Redis","Kafka","Spark","Airflow","dbt","Docker","Kubernetes","AWS","Azure","GCP","Terraform","React","Node.js","Django","Spring","Rails","Pandas","PyTorch","TensorFlow","Git","Linux","REST","GraphQL","Snowflake","Hadoop","Machine Learning"]
TECH = {"Java","Ruby","Scala","Python","JavaScript","Data Science","Data Engineer",".NET","C++","Sysadmin","Lead"}

def skills(text):
    return [s for s in VOCAB if re.search(r"(?<![A-Za-z0-9])" + re.escape(s) + r"(?![A-Za-z0-9+#])", text, re.I if len(s) > 3 else 0)]

def company_key(name):
    return "".join(c for c in name.casefold() if c.isalnum())


def main(out, seed=7, exclude=None):
    excluded = json.loads(exclude.read_text()) if exclude else []
    seen = {company_key(j["company"]) for j in excluded}
    urls = {j["url"] for j in excluded}
    rng = random.Random(seed)
    offsets = range(0, 141800, 100)
    original = set(random.Random(7).sample(offsets, 8)) if exclude else set()
    initial = sorted(set(rng.sample(offsets, 8)) - original)
    remaining = sorted(set(offsets) - original - set(initial))
    rng.shuffle(remaining)
    jobs = []
    for off in initial + remaining:
        with urllib.request.urlopen(URL % off, timeout=60) as response:
            rows = json.load(response)["rows"]
        for row in rows:
            r = row["row"]
            sk = skills(r["Position"] + " " + r["Long Description"])
            if r["Primary Keyword"] not in TECH or len(sk) < 2 or r["Long Description_lang"] != "en":
                continue
            company = company_key(r["Company Name"]) if exclude else r["Company Name"]
            url = "https://huggingface.co/datasets/lang-uk/recruitment-dataset-job-descriptions-english#" + r["id"]
            if company in seen or url in urls:
                continue
            seen.add(company)
            urls.add(url)
            prefix = "h" if exclude else "d"
            jobs.append({"id": f"{prefix}{len(jobs)+1:02d}", "title": r["Position"][:80], "company": r["Company Name"], "location": "Remote",
                         "source": "djinni", "posted_date": r["Published"][:10], "skills": sk, "url": url})
            if len(jobs) == 50:
                out.write_text(json.dumps(jobs, indent=1))
                return
    raise ValueError("fewer than 50 eligible postings")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("out", type=Path)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--exclude", type=Path, help="existing sample to exclude (seed-7 offsets also omitted)")
    args = parser.parse_args()
    main(args.out, args.seed, args.exclude)
