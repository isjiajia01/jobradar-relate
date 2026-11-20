"""Score a job from graph facts only. LLM is optional (OpenAI-compatible endpoint via env);
without it a deterministic scorer runs. The LLM output is validated against the facts."""
import json, os, re, sys, urllib.request
import relate
from .facts import gather

def breakdown(f):
    """Deterministic score as itemised contributions (used by the keyless demo)."""
    n = len(f["required"]) or 1
    parts = [("base", 50), (f"skills {len(f['overlap'])}/{len(f['required'])} matched", 30 * len(f["overlap"]) // n),
             (f"related skills x{len(f['related'])}", 5 * min(len(f["related"]), 2)),
             (f"liked similar x{len(f['liked_similar'])}", 10 * min(len(f["liked_similar"]), 2)),
             (f"dismissed similar x{len(f['dismissed_similar'])}", -15 * min(len(f["dismissed_similar"]), 2))]
    if f["own"]: parts.append((f"you {f['own'].lower()} this job", 10 if f["own"] == "LIKED" else -25))
    if f["status"] == "likely_duplicate": parts.append(("likely duplicate of a seen job", -20))
    return [p for p in parts if p[1] or p[0] == "base"]

def fallback(f):
    s = max(0, min(100, sum(v for _, v in breakdown(f))))
    why = f"{len(f['overlap'])} of {len(f['required'])} required skills match your profile"
    if f["own"]: why += f", you already {f['own'].lower()} this exact job"
    if f["related"]: why += f", {len(f['related'])} more are related to skills you have"
    if f["liked_similar"]: why += f", you liked {len(f['liked_similar'])} similar job(s) at {f['company']}"
    if f["dismissed_similar"]: why += f", you dismissed {len(f['dismissed_similar'])} similar job(s) there"
    if f["status"] == "likely_duplicate": why += ", and it looks like a duplicate of a job already seen"
    return {"score": s, "explanation": why + "."}

def llm(f):
    url, key, model = os.environ.get("LLM_URL"), os.environ.get("LLM_API_KEY"), os.environ.get("LLM_MODEL")
    if not (url and key and model): return None
    facts = {k: f[k] for k in ("title", "company", "required", "overlap", "related", "own", "liked_similar", "dismissed_similar", "similar_links", "status")}
    msg = ("Use ONLY these graph facts. Reply JSON {\"score\":0-100,\"explanation\":\"one sentence\"}. "
           "Do not state any reason that is not in the facts.\n" + json.dumps(facts))
    req = urllib.request.Request(url, json.dumps({"model": model, "temperature": 0,
        "messages": [{"role": "user", "content": msg}]}).encode(),
        {"Authorization": "Bearer " + key, "Content-Type": "application/json"})
    timeout = int(os.environ.get("LLM_TIMEOUT", "90"))
    for attempt in (1, 2):
        try:
            out = json.load(urllib.request.urlopen(req, timeout=timeout))["choices"][0]["message"]["content"]
            break
        except Exception:
            if attempt == 2: raise
    return validate(json.loads(out), facts)

def validate(r, facts):
    """Keep only score+explanation. Reject anything not grounded in the facts."""
    if not isinstance(r, dict): raise ValueError("not an object")
    score, why = r.get("score"), r.get("explanation")
    if not (isinstance(score, int) and not isinstance(score, bool) and 0 <= score <= 100): raise ValueError("bad score")
    if not (isinstance(why, str) and 0 < len(why) <= 400): raise ValueError("bad explanation")
    blob = json.dumps(facts)
    for tok in re.findall(r"\b(?:j\d+|\d+(?:\.\d+)?)\b", why):   # job ids and numbers must exist in the facts
        if tok not in blob and tok not in {str(len(facts["required"])), str(len(facts["overlap"]))}:
            raise ValueError(f"ungrounded token in explanation: {tok}")
    return {"score": score, "explanation": why}

def recommend(db, job_id):
    f = gather(db, job_id)
    try: r = llm(f)
    except Exception as e: print("llm failed, using fallback:", e, file=sys.stderr); r = None
    used = "llm" if r is not None else "fallback"
    r = r or fallback(f)
    if f["status"] == "likely_duplicate": r["score"] = min(r["score"], 60)   # duplicates never outrank new jobs
    return {"job": job_id, "title": f["title"], "status": f["status"], **r, "path": f["path"], "scorer": used}

if __name__ == "__main__":
    db = relate.connect(sys.argv[1])
    for j in sys.argv[2:]: print(json.dumps(recommend(db, j), indent=1))
    db.close()
