"""Keyless judge demo: rank every job from the graph, show evidence paths, replay a feedback change.
Works on a temporary COPY of the .rl file, so the shipped store is never modified.
Usage: python -m jobradar_relate.demo [jobradar.rl] [out.html]"""
import html, shutil, sys, tempfile, os
import relate
from .facts import gather
from .score import breakdown, fallback

def rank(db):
    ids = [r["id"] for r in db.execute("MATCH (j:Job) RETURN j.id AS id ORDER BY id LIMIT 500")]
    out = []
    for i in ids:
        f = gather(db, i); r = fallback(f)
        if f["status"] == "likely_duplicate": r["score"] = min(r["score"], 60)
        out.append({"f": f, "score": r["score"], "why": r["explanation"], "parts": breakdown(f)})
    return sorted(out, key=lambda x: (-x["score"], x["f"]["job"]))

def replay(src, job, verdict):
    """Flip my verdict on `job` in a temp copy; return the new ranking."""
    d = tempfile.mkdtemp(); p = os.path.join(d, "r.rl"); shutil.copy(src, p)
    db = relate.connect(p)
    db.execute("MATCH (:User {id:'me'})-[r:LIKED|DISMISSED]->(:Job {id:$j}) DELETE r", {"j": job})
    db.execute(f"MATCH (u:User {{id:'me'}}),(j:Job {{id:$j}}) MERGE (u)-[:{verdict}]->(j)", {"j": job})
    res = rank(db); db.close(); shutil.rmtree(d); return res

def card(x, delta=None):
    f, e = x["f"], html.escape
    parts = "".join(f"<li>{e(n)}: <b>{v:+d}</b></li>" for n, v in x["parts"])
    hops = "".join(f"<li class=hop>{e(h['text'])}</li>" for h in f["hops"]) or "<li>no liked/dismissed similar jobs</li>"
    dup = "".join(f"<li class=dup>{e(l['id'])} ({e(l['source'])}) score {l['score']}</li>" for l in f["similar_links"]) or "<li>none</li>"
    d = f" <span class=delta>{delta:+d} after replay</span>" if delta else ""
    return (f"<div class=card><h3>{e(f['job'])} {e(f['title'])} @ {e(f['company'])} <small>({e(f['source'])})</small>"
            f"<span class=score>{x['score']}</span>{d}</h3><p>{e(x['why'])}</p><b>status:</b> {e(f['status'])}"
            f"<div class=cols><div><b>Score parts</b><ul>{parts}</ul></div><div><b>Graph path</b><ul>{hops}</ul>"
            f"<b>SIMILAR_TO links</b><ul>{dup}</ul></div></div><code>{e(f['path'])}</code></div>")

def main(db_path="jobradar.rl", out="docs/demo.html", job="j05", verdict="LIKED"):
    d = tempfile.mkdtemp(); p = os.path.join(d, "c.rl"); shutil.copy(db_path, p)
    db = relate.connect(p); base = rank(db); db.close(); shutil.rmtree(d)
    after = replay(db_path, job, verdict)
    before = {x["f"]["job"]: x["score"] for x in base}
    moved = [(x, x["score"] - before[x["f"]["job"]]) for x in after if x["score"] != before[x["f"]["job"]]]
    page = ("<!doctype html><meta charset=utf-8><title>jobradar-relate demo</title><style>body{font:15px system-ui;max-width:900px;margin:2em auto;padding:0 1em}"
            ".card{border:1px solid #ccc;border-radius:8px;padding:.8em 1em;margin:.8em 0}.score{float:right;background:#0a5;color:#fff;border-radius:6px;padding:0 .5em}"
            ".cols{display:flex;gap:2em}.hop{color:#06c}.dup{color:#c60}.delta{color:#a0a;font-size:.8em}code{display:block;font-size:12px;color:#555;margin-top:.5em}</style>"
            "<h1>jobradar-relate: ranked from the Relate graph</h1><p>Synthetic data. Deterministic scorer, no API key. Source: "
            f"<code>{html.escape(db_path)}</code> (read as a temporary copy).</p><h2>Ranking</h2>" + "".join(card(x) for x in base)
            + f"<h2>Feedback replay: what if I {verdict} {job}?</h2><p>Only the {verdict} edge changes in a temporary copy.</p>"
            + ("".join(card(x, dlt) for x, dlt in moved) or "<p>No scores changed.</p>"))
    os.makedirs(os.path.dirname(out) or ".", exist_ok=True); open(out, "w").write(page)
    for x in base: print(f"{x['score']:>3}  {x['f']['job']}  {x['f']['title']} @ {x['f']['company']}  [{x['f']['status']}]")
    for x, dlt in moved: print(f"replay {verdict} {job}: {x['f']['job']} {dlt:+d} -> {x['score']}")
    print("wrote", out)

if __name__ == "__main__":
    main(*sys.argv[1:3])
