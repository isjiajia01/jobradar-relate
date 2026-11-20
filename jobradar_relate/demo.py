"""Keyless judge demo: rank every job from the graph, show evidence paths, replay a feedback change.
Works on a temporary COPY of the .rl file, so the shipped store is never modified.
Usage: python -m jobradar_relate.demo [jobradar.rl] [out.html]"""
import html, shutil, sys, tempfile, os
from contextlib import closing
from pathlib import Path

import relate
from .discover import discover
from .facts import gather
from .score import breakdown, fallback

VERDICTS = ("LIKED", "DISMISSED", "SEEN")


def score_job(db, job):
    facts = gather(db, job)
    result = fallback(facts)
    return {"f": facts, "score": result["score"], "why": result["explanation"], "parts": breakdown(facts)}


def rank(db):
    ids = [r["id"] for r in db.execute("MATCH (j:Job) RETURN j.id AS id ORDER BY id")]
    return sorted((score_job(db, job) for job in ids), key=lambda x: (-x["score"], x["f"]["job"]))


def replay(src, job, verdict, *, temp_dir=None):
    """Apply one feedback or exposure edit in an isolated copy and rank it."""
    if verdict not in VERDICTS:
        raise ValueError(f"invalid VERDICT {verdict!r} (choose {'|'.join(VERDICTS)})")
    with tempfile.TemporaryDirectory(dir=temp_dir) as tmp:
        path = shutil.copyfile(src, Path(tmp) / "replay.rl")
        with closing(relate.connect(str(path))) as db:
            params = {"j": job}
            if not list(db.execute("MATCH (j:Job {id:$j}) RETURN j.id", params)):
                raise KeyError(job)
            if verdict != "SEEN":
                db.execute("MATCH (:User {id:'me'})-[r:LIKED|DISMISSED]->(:Job {id:$j}) DELETE r", params)
            db.execute(f"MATCH (u:User {{id:'me'}}),(j:Job {{id:$j}}) MERGE (u)-[:{verdict}]->(j)", params)
            return rank(db)


def score_changes(base, after):
    before = {row["f"]["job"]: row for row in base}
    for row in after:
        old = before[row["f"]["job"]]
        if row["score"] != old["score"]:
            yield old, row

def unseen_order(rows):
    """Unseen jobs in review-queue order (rank() already sorts by score, then id)."""
    return [x for x in rows if not x["f"]["seen"]]


def queue_compare(base, after_rows, job):
    """Side-by-side unseen review queue before and after a replay; rows whose rank or score moved are marked."""
    old, new = unseen_order(base), unseen_order(after_rows)
    pos = {x["f"]["job"]: i for i, x in enumerate(old, 1)}
    npos = {x["f"]["job"]: i for i, x in enumerate(new, 1)}
    olds = {x["f"]["job"]: x["score"] for x in old}
    news = {x["f"]["job"]: x["score"] for x in new}
    def cell(x, n):
        j = x["f"]["job"]; mark = " class=moved" if news.get(j) != olds.get(j) else ""
        return f"<td{mark}>{n}. {html.escape(j)} {html.escape(x['f']['title'])} <b>{x['score']}</b></td>"
    rows = "".join(f"<tr>{cell(o, i)}{cell(n, i)}</tr>" for i, (o, n) in enumerate(zip(old, new), 1))
    shifts = [f"{j} {pos[j]}→{npos[j]}" for j in npos if j in pos and pos[j] != npos[j]]
    note = ("Position changes: " + ", ".join(shifts) + ".") if shifts else "The queue order did not change."
    return (f"<h3>Tomorrow's review queue (unseen jobs only)</h3><p>{html.escape(job)} is in neither list because it is already seen. {note}</p>"
            "<table class=queue><thead><tr><th>Before replay</th><th>After replay</th></tr></thead>"
            f"<tbody>{rows}</tbody></table><p><small>Highlighted: the job whose score changed. Other jobs only shift position.</small></p>")


def card(x, delta=None):
    f, e = x["f"], html.escape
    parts = "".join(f"<li>{e(n)}: <b>{v:+d}</b></li>" for n, v in x["parts"])
    hops = "".join(f"<li class=hop>{e(h['text'])}</li>" for h in f["hops"]) or "<li>no liked/dismissed similar jobs</li>"
    dup = "".join(f"<li class=dup>{e(l['id'])} ({e(l['source'])}) score {l['score']}</li>" for l in f["similar_links"]) or "<li>none</li>"
    d = f" <span class=delta>{delta:+d} after replay</span>" if delta else ""
    return (f"<div class=card><h3>{e(f['job'])} {e(f['title'])} @ {e(f['company'])} <small>({e(f['source'])})</small>"
            f"<span class=score>{x['score']}</span>{d}</h3><p>{e(x['why'])}</p><b>status:</b> {e(f['status'])}"
            f"<div class=cols><div><b>Score parts</b><ul>{parts}</ul></div><div><b>Graph path</b><ul>{hops}</ul>"
            f"<b>SIMILAR_TO links</b><ul>{dup}</ul></div></div><details><summary>Raw evidence string</summary><code>{e(f['path'])}</code></details></div>")

def main(db_path="jobradar.rl", out="docs/demo.html", job="j05", verdict="LIKED"):
    with closing(relate.connect(db_path, read_only=True)) as db:
        base = rank(db)
        hits, shortlist = discover(db, "engineer")
    after_rows = replay(db_path, job, verdict)
    moved = [(new, new["score"] - old["score"]) for old, new in score_changes(base, after_rows)]
    search_rows = "".join(
        f"<tr><td>{html.escape(row['facts']['job'])} {html.escape(row['facts']['title'])}</td>"
        f"<td>{row['relevance']:.3f}</td><td>{row['score']}</td><td>{html.escape(row['facts']['status'])}</td></tr>"
        for row in shortlist)
    page = ("<!doctype html><html lang=en><meta charset=utf-8><meta name=viewport content='width=device-width,initial-scale=1'><title>jobradar-relate demo</title><style>body{color:#172d34;background:#fafbf8;font:16px/1.5 system-ui;max-width:900px;margin:2em auto;padding:0 1em}"
            ".card{border:1px solid #ccc;border-radius:8px;padding:.8em 1em;margin:.8em 0}.score{float:right;background:#0a5;color:#fff;border-radius:6px;padding:0 .5em}"
            ".cols{display:flex;gap:2em}table{border-collapse:collapse;width:100%}td,th{text-align:left;border-bottom:1px solid #ccd6d3;padding:.4em}th{background:#e3ede6}@media(max-width:600px){.cols{display:block}td,th{padding:.2em}h3{font-size:1rem}}.hop{color:#06c}.dup{color:#c60}.delta{color:#a0a;font-size:.8em}td.moved{background:#fff3c4;font-weight:600}details{margin-top:.5em;font-size:13px;color:#555}summary{cursor:pointer}details code{display:block;font-size:12px;margin-top:.3em;overflow-wrap:anywhere}</style>"
            "<h1>Which opening is worth a closer look?</h1><p>Synthetic data. Every score and evidence path is read from one Relate graph file: "
            f"<code>{html.escape(db_path)}</code> (opened read-only). Deterministic scorer, no API key. <a href='https://github.com/isjiajia01/jobradar-relate'>Repository</a></p><h2>Search for “engineer”</h2>"
            f"<p>Relate found {hits} title matches. {len(shortlist)} are unseen. Personal fit orders those listings using graph evidence.</p>"
            "<table><thead><tr><th>Unseen listing</th><th>Text score</th><th>Fit</th><th>Status</th></tr></thead>"
            f"<tbody>{search_rows}</tbody></table><p><a href='#all'>Jump to all listings</a></p>"
            f"<h2 id='feedback'>Feedback replay: what if I {verdict} {job}?</h2><p>Run on a temporary copy of the graph. {len(moved)} of {len(base)} scores changed; the other {len(base) - len(moved)} stayed fixed.</p>"
            + queue_compare(base, after_rows, job) + ("".join(card(x, dlt) for x, dlt in moved) or "<p>No scores changed.</p>")
            + "<h2 id='all'>All listings</h2>" + "".join(card(x) for x in base))
    os.makedirs(os.path.dirname(out) or ".", exist_ok=True); open(out, "w").write(page)
    for x in base: print(f"{x['score']:>3}  {x['f']['job']}  {x['f']['title']} @ {x['f']['company']}  [{x['f']['status']}]")
    for x, dlt in moved: print(f"replay {verdict} {job}: {x['f']['job']} {dlt:+d} -> {x['score']}")
    print("wrote", out)

if __name__ == "__main__":
    main(*sys.argv[1:3])
