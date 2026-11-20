"""Score a job from graph facts only. LLM is optional (OpenAI-compatible endpoint via env);
without it a deterministic scorer runs. The LLM output is validated against the facts."""
import json, os, sys, urllib.request
import relate
from .facts import gather

def fallback(f):
    n = len(f["required"]) or 1
    s = 50 + 30 * len(f["overlap"]) // n + 10 * min(len(f["liked_similar"]), 2) - 15 * min(len(f["dismissed_similar"]), 2)
    if f["status"] == "likely_duplicate": s -= 20
    s = max(0, min(100, s))
    why = f"{len(f['overlap'])} of {len(f['required'])} required skills match your profile"
    if f["liked_similar"]: why += f", you liked {len(f['liked_similar'])} similar job(s) at {f['company']}"
    if f["dismissed_similar"]: why += f", you dismissed {len(f['dismissed_similar'])} similar job(s) there"
    if f["status"] == "likely_duplicate": why += ", and it looks like a duplicate of a job already seen"
    return {"score": s, "explanation": why + "."}

def llm(f):
    url, key, model = os.environ.get("LLM_URL"), os.environ.get("LLM_API_KEY"), os.environ.get("LLM_MODEL")
    if not (url and key and model): return None
    facts = {k: f[k] for k in ("title", "company", "required", "overlap", "liked_similar", "dismissed_similar", "similar_links", "status")}
    msg = ("Use ONLY these graph facts. Reply JSON {\"score\":0-100,\"explanation\":\"one sentence\"}. "
           "Do not state any reason that is not in the facts.\n" + json.dumps(facts))
    req = urllib.request.Request(url, json.dumps({"model": model, "temperature": 0,
        "messages": [{"role": "user", "content": msg}]}).encode(),
        {"Authorization": "Bearer " + key, "Content-Type": "application/json"})
    out = json.load(urllib.request.urlopen(req, timeout=30))["choices"][0]["message"]["content"]
    r = json.loads(out)
    assert isinstance(r["score"], int) and 0 <= r["score"] <= 100 and isinstance(r["explanation"], str)
    return r

def recommend(db, job_id):
    f = gather(db, job_id)
    try: r = llm(f)
    except Exception as e: print("llm failed, using fallback:", e, file=sys.stderr); r = None
    used = "llm" if r is not None else "fallback"
    r = r or fallback(f)
    return {"job": job_id, "title": f["title"], "status": f["status"], **r, "path": f["path"], "scorer": used}

if __name__ == "__main__":
    db = relate.connect(sys.argv[1])
    for j in sys.argv[2:]: print(json.dumps(recommend(db, j), indent=1))
    db.close()
