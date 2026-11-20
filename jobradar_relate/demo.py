"""Keyless judge demo: rank every job from the graph, show evidence paths, replay a feedback change.
Works on a temporary COPY of the .rl file, so the shipped store is never modified.
Usage: python -m jobradar_relate.demo [jobradar.rl] [out.html]"""
import datetime, html, shutil, sys, tempfile, os
from contextlib import closing
from pathlib import Path

import relate
from .discover import discover
from .facts import gather
from .score import breakdown, fallback

VERDICTS = ("LIKED", "DISMISSED", "SEEN")
REPO = "https://github.com/isjiajia01/jobradar-relate"


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


# ---------------------------------------------------------------- page rendering
# Visual direction: a transit route map of the user's job memory. Graph nodes are stations,
# scores sit in station roundels, relationship types are coloured, always-labelled lines.
e = html.escape
BOARDS = {"jobindex": "Jobindex", "linkedin": "LinkedIn", "jobnet": "Jobnet"}
REL = {"LIKED": "liked", "DISMISSED": "dismissed", "SEEN": "seen"}


def board(source):
    return BOARDS.get(source, (source or "").title())


def day(iso):
    try:
        d = datetime.date.fromisoformat(iso)
    except (TypeError, ValueError):
        return e(str(iso or "undated"))
    return f"{d.day} {d:%b}"


def signed(v):
    return f"{v:+d}".replace("-", "\u2212")


def part_kind(name):
    if name == "base":
        return "base"
    if name.startswith(("skills", "related")):
        return "skill"
    if "dismissed" in name or "duplicate" in name:
        return "bad"
    return "like"


def equation(x, label=None, key=True):
    """Score parts as a sum strip: 50 base +20 skills ... = 95."""
    parts = "".join(f"<li class={part_kind(n)}><b>{v if n == 'base' else signed(v)}</b> {e(n)}</li>" for n, v in x["parts"])
    total = sum(v for _, v in x["parts"])
    cap = "" if total == x["score"] else f"<li class=bad><b>cap</b> sum {total} held at {x['score']}</li>"
    job = x["f"]["job"]
    key = f"<a class=key href='#{e(job)}'>{e(label or job)}</a>" if key else ""
    return f"<div class=eqrow>{key}<ol class=eq aria-label='Score parts for {e(job)}'>{parts}{cap}<li class=sum><b>= {x['score']}</b></li></ol></div>"


def roundel(cx, cy, score, r=31):
    return (f"<circle class=rd cx={cx} cy={cy} r={r} />"
            f"<text class=rdn x={cx} y={cy + 10} text-anchor=middle>{score}</text>")


def you(cx, cy):
    return (f"<circle class=you cx={cx} cy={cy} r=22 />"
            f"<text class=yout x={cx} y={cy + 5} text-anchor=middle>You</text>")


def txt(x, y, s, cls, anchor=None):
    a = f" text-anchor={anchor}" if anchor else ""
    return f"<text class='{cls}' x={x} y={y}{a}>{s}</text>"


def repost_plate(base):
    """Story 1: the same opening on two boards, linked by SIMILAR_TO, scored 95 and 60."""
    rows = {x["f"]["job"]: x for x in base}
    dup = next((x for x in base if x["f"]["status"] == "likely_duplicate"), None)
    hop = dup and next((h for h in dup["f"]["hops"] if h["verdict"] == "SEEN"), None)
    if not hop:
        return ""
    peer, d = rows[hop["via"]], dup["f"]
    p = peer["f"]
    pen = next((v for n, v in dup["parts"] if "duplicate" in n), 0)
    svg = []
    if p["own"]:
        svg += [f"<path class='e {REL.get(p['own'], 'seen')}' d='M40,135 L111,64 H200' />",
                txt(140, 52, f"{e(p['own'])} \u2192", "rel " + REL.get(p["own"], "seen"), "middle")]
    if p["seen"]:
        svg += ["<path class='e seen' d='M47,146 L119,74 H200' />", txt(140, 96, "SEEN \u2192", "rel seen", "middle")]
    svg += ["<path class='e sim' d='M200,64 V206' />",
            txt(186, 130, "SIMILAR_TO", "rel sim", "end"), txt(186, 150, f"{hop['weight']}", "rel sim", "end"),
            you(40, 135), roundel(200, 64, peer["score"]), roundel(200, 206, dup["score"]),
            txt(244, 56, f"{e(p['job'])} {e(p['title'])}", "t"),
            txt(244, 77, f"{e(board(p['source']))} \u00b7 posted {day(p['posted_date'])}", "m"),
            txt(244, 97, ("you liked it" if p["own"] == "LIKED" else "seen") + (" \u00b7 seen" if p["seen"] and p["own"] else ""), "m"),
            txt(244, 198, f"{e(d['job'])} {e(d['title'])}", "t"),
            txt(244, 219, f"{e(board(d['source']))} \u00b7 posted {day(d['posted_date'])} \u00b7 unseen", "m"),
            "<rect class=flag x=244 y=232 width=222 height=28 rx=3 />",
            txt(253, 251, f"{e(d['status'])} \u00b7 {signed(pen)}, cap 60", "flagt")]
    label = (f"Graph drawing: You {p['own'] or ''} and SEEN {p['job']} on {board(p['source'])}, score {peer['score']}. "
             f"{p['job']} SIMILAR_TO {d['job']} on {board(d['source'])} with weight {hop['weight']}; {d['job']} scores {dup['score']}.")
    return (f"<section class=plate id=repost aria-labelledby=repost-h><h2 id=repost-h>Same opening, two boards: "
            f"<span class=num>{peer['score']}</span> vs <span class=num>{dup['score']}</span></h2>"
            f"<p>{e(p['job'])} ({e(board(p['source']))}) and {e(d['job'])} ({e(board(d['source']))}) are the same {e(d['title'])} opening at {e(d['company'])}, "
            f"joined by a SIMILAR_TO edge. You saw and liked the earlier posting, so the repost is flagged "
            f"<code>{e(d['status'])}</code>: \u221220 points, capped at 60.</p>"
            f"<figure class=map><svg viewBox='0 24 476 242' role=img aria-label='{e(label)}'>{''.join(svg)}</svg></figure>"
            + equation(peer) + equation(dup) + "</section>")


def replay_plate(base, after_rows, moved, job, verdict):
    """Story 3: flip one verdict on a temporary copy and watch it travel along SIMILAR_TO."""
    b = {x["f"]["job"]: x for x in base}
    a = {x["f"]["job"]: x for x in after_rows}
    src = b[job]["f"]
    others = [x for x, _ in moved if x["f"]["job"] != job]
    svg, label = [], [f"Graph drawing: You {verdict} {job} (before: {src['own'] or 'no verdict'})."]
    if src["own"]:
        svg += [f"<path class='e old {REL.get(src['own'], 'seen')}' d='M56,98 H200' />",
                txt(116, 86, f"was {e(src['own'])}", "rel " + REL.get(src["own"], "seen"), "middle")]
    svg += [f"<path class='e {REL.get(verdict, 'seen')} draw' pathLength=1 d='M56,122 H200' />",
            txt(116, 146, f"{e(verdict)} \u2192 (replay)", "rel " + REL.get(verdict, "seen"), "middle")]

    def node(cx, jid):
        f, old, new = b[jid]["f"], b[jid]["score"], a[jid]["score"]
        dlt = new - old
        cls = "up" if dlt > 0 else "down" if dlt < 0 else "m"
        return [roundel(cx, 110, new, 33),
                txt(cx, 182, f"{e(jid)} {e(f['title'])}", "t", "middle"),
                txt(cx, 203, f"{e(board(f['source']))} \u00b7 {'seen' if f['seen'] else 'unseen'}", "m", "middle"),
                txt(cx, 228, f"{old} \u2192 {new}" + (f" ({signed(dlt)})" if dlt else ""), "delta " + cls, "middle")]
    if others:
        nb = others[0]["f"]["job"]
        w = next((l["score"] for l in src["similar_links"] if l["id"] == nb), "")
        svg += ["<path class='e sim' d='M200,110 H420' />", txt(310, 98, f"SIMILAR_TO {w}", "rel sim", "middle")]
        svg += node(420, nb)
        label.append(f"{job} SIMILAR_TO {nb} ({w}). {nb}: {b[nb]['score']} to {a[nb]['score']}.")
    svg += [you(34, 110)] + node(200, job)
    label.append(f"{job}: {b[job]['score']} to {a[job]['score']}.")
    detail = "".join(equation(x, f"{x['f']['job']} after") for x, _ in moved)
    return (f"<section class=plate id=feedback aria-labelledby=feedback-h><h2 id=feedback-h>Feedback replay: what if I {e(verdict)} {e(job)}?</h2>"
            f"<p>Run on a temporary copy of the graph. <strong>{len(moved)} of {len(base)} scores changed</strong>; the other {len(base) - len(moved)} stayed fixed. "
            + (f"The new verdict reaches {e(others[0]['f']['job'])} along one SIMILAR_TO edge." if others else "") + "</p>"
            f"<figure class=map><svg viewBox='0 66 520 170' role=img aria-label='{e(' '.join(label))}'>{''.join(svg)}</svg></figure>"
            + queue_compare(base, after_rows, job)
            + (f"<details class=more><summary>Score parts after the replay</summary>{detail}</details>" if detail else "<p>No scores changed.</p>")
            + "</section>")


def queue_compare(base, after_rows, job):
    """Side-by-side unseen review queue before and after a replay; rows whose rank or score moved are marked."""
    old, new = unseen_order(base), unseen_order(after_rows)
    pos = {x["f"]["job"]: i for i, x in enumerate(old, 1)}
    npos = {x["f"]["job"]: i for i, x in enumerate(new, 1)}
    olds = {x["f"]["job"]: x["score"] for x in old}
    news = {x["f"]["job"]: x["score"] for x in new}
    changed = {j for j in news if news[j] != olds.get(j)}

    def cell(x, n):
        j = x["f"]["job"]
        mark, sr = (" class=moved", "<span class=vh> (score changed)</span>") if j in changed else ("", "")
        return f"<td{mark}><span class=n>{n}</span> {e(j)} <span class=qt>{e(x['f']['title'])}</span> <b>{x['score']}</b>{sr}</td>"
    k = len(new)
    lines = "".join(
        f"<line class='{'hot draw' if j in changed else 'cold'}' pathLength=1 vector-effect=non-scaling-stroke "
        f"x1=0 y1={pos[j] - .5} x2=100 y2={npos[j] - .5} />"
        for j in sorted(npos, key=lambda j: j in changed) if j in pos)
    slope = (f"<td class=slope rowspan={k} aria-hidden=true><svg viewBox='0 0 100 {k}' preserveAspectRatio=none>{lines}</svg></td>")
    rows = "".join(f"<tr>{cell(o, i)}{slope if i == 1 else ''}{cell(n, i)}</tr>" for i, (o, n) in enumerate(zip(old, new), 1))
    shifts = [f"{j} {pos[j]}→{npos[j]}" for j in npos if j in pos and pos[j] != npos[j]]
    note = ("Position changes: " + ", ".join(shifts) + ".") if shifts else "The queue order did not change."
    return (f"<h3>Tomorrow's review queue (unseen jobs only)</h3><p class=small>{e(job)} is in neither list because it is already seen. {note}</p>"
            "<table class=queue><colgroup><col><col class=slopecol><col></colgroup>"
            "<thead><tr><th scope=col>Before replay</th><td class=slope></td><th scope=col>After replay</th></tr></thead>"
            f"<tbody>{rows}</tbody></table><p class=small>Highlighted: the job whose score changed. Other jobs only shift position.</p>")


def route(aria, items):
    """A metro strip. items: ('st', name, sub) or ('ln', label, kind)."""
    out = []
    for kind, a, b in items:
        if kind == "st":
            out.append(f"<li class=st><i></i><span>{e(a)}</span>{f'<small>{e(b)}</small>' if b else ''}</li>")
        else:
            out.append(f"<li class='ln {b}'><span>{e(a)}</span></li>")
    return f"<ol class=route role=img aria-label='{e(aria)}'>{''.join(out)}</ol>"


def job_row(x, index, is_open=False):
    f = x["f"]
    job = f["job"]

    def sub(jid):
        g = index.get(jid)
        return f"{board(g['source'])}, {day(g['posted_date'])}" if g else ""
    routes = []
    if f["own"]:
        routes.append(route(f"User -{f['own']}-> {job}", [("st", "You", ""), ("ln", f"{f['own']} \u2192", REL[f["own"]]), ("st", job, "this job")]))
    rel_hops = [h for h in f["hops"] if h["verdict"] == "RELATED_TO"]
    for h in f["hops"]:
        if h["verdict"] in ("LIKED", "DISMISSED", "SEEN"):
            routes.append(route(h["text"], [("st", "You", ""), ("ln", f"{h['verdict']} \u2192", REL[h["verdict"]]),
                                            ("st", h["via"], sub(h["via"])), ("ln", f"SIMILAR_TO {h['weight']}", "sim"),
                                            ("st", job, "this job")]))
    for h, r in zip(rel_hops, f["related"]):
        routes.append(route(h["text"], [("st", "You", ""), ("ln", "HAS_SKILL \u2192", "skill"), ("st", r["via"], "your skill"),
                                        ("ln", "RELATED_TO", "skill"), ("st", r["skill"], "required"),
                                        ("ln", "\u2190 REQUIRES", "skill"), ("st", job, "this job")]))
    near = {r["skill"]: r["via"] for r in f["related"]}
    skills = "".join(
        f"<li class=have>\u2713 {e(s)}</li>" if s in f["overlap"] else
        f"<li class=near>\u2248 {e(s)} <small>via {e(near[s])}</small></li>" if s in near else
        f"<li class=miss>\u2717 {e(s)}</li>" for s in f["required"])
    links = "".join(
        f"<li><a href='#{e(l['id'])}'>{e(l['id'])}</a> {e(board(l['source']))} \u00b7 posted {day(l['posted_date'])} \u00b7 "
        f"{'seen' if l['seen'] else 'unseen'} \u00b7 similarity <b>{l['score']}</b></li>" for l in f["similar_links"]) or "<li>none</li>"
    paths = "".join(routes) or "<p class=small>No liked, dismissed or seen neighbours: this score comes from skills alone.</p>"
    return (f"<details class=job id={e(job)}{' open' if is_open else ''}><summary>"
            f"<span class=sr>{x['score']}</span>"
            f"<span class=ttl><b>{e(job)} {e(f['title'])}</b> <span class=meta>{e(f['company'])} \u00b7 {e(board(f['source']))} \u00b7 posted {day(f['posted_date'])}</span></span>"
            f"<span class='tag s-{e(f['status'])}'>{e(f['status'])}</span>"
            f"<span class=why>{e(x['why'])}</span></summary><div class=body>"
            f"<div><h4>Score parts</h4>{equation(x, key=False)}<h4>Required skills</h4><ul class=skills>{skills}</ul></div>"
            f"<div><h4>Graph paths</h4>{paths}<h4>SIMILAR_TO links</h4><ul class=links>{links}</ul>"
            f"<details class=raw><summary>Raw evidence string</summary><code>{e(f['path'])}</code></details></div>"
            "</div></details>")


CSS = """
:root{--paper:#f2f4f5;--sheet:#fff;--ink:#0e2338;--ink2:#435468;--rule:#d2dae0;--like:#16784a;--bad:#b0261e;--sim:#1460a3;
--seen:#5b6877;--skill:#935600;--hl:#ffe17a;
--sans:"Avenir Next",Avenir,"Segoe UI","Helvetica Neue",Helvetica,Arial,sans-serif;
--cond:"Avenir Next Condensed","Avenir Next",Avenir,"Arial Narrow","Segoe UI",sans-serif;--mono:ui-monospace,Menlo,Consolas,monospace}
*{box-sizing:border-box}
html{background:var(--paper);color:var(--ink);font:16px/1.5 var(--sans);-webkit-text-size-adjust:100%}
body{margin:0}
a{color:var(--sim);text-underline-offset:2px}
a:focus-visible,summary:focus-visible{outline:3px solid var(--sim);outline-offset:2px}
code{font:.86em var(--mono)}
.vh{position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0 0 0 0);white-space:nowrap}
.band{background:var(--ink);color:#fff}
.in,.wrap{max-width:1240px;margin:0 auto;padding:0 1.25rem}
.band .in{display:flex;align-items:center;gap:.4rem 1.5rem;flex-wrap:wrap;min-height:48px}
.mark{display:flex;align-items:center;gap:.55rem;font-weight:700;font-size:1.05rem;color:#fff;text-decoration:none}
.band nav{display:flex;gap:.2rem 1.2rem;margin-left:auto;flex-wrap:wrap;font-size:.92rem}
.band nav a{color:#fff;text-decoration:none;display:inline-block;padding:.65rem 0;border-bottom:3px solid transparent}
.band nav a:hover{border-bottom-color:#7fc3ff}
.intro{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1.05fr);gap:.6rem 2.5rem;align-items:end;padding:1.3rem 0 1.1rem}
h1{font-size:2.15rem;line-height:1.08;font-weight:700;margin:0;letter-spacing:-.012em;max-width:16ch}
.lede{margin:0;color:var(--ink2);font-size:.95rem;max-width:64ch}
.key-legend{display:flex;flex-wrap:wrap;gap:.2rem 1.1rem;list-style:none;margin:.45rem 0 0;padding:0;font:600 .8rem var(--cond);color:var(--ink2)}
.key-legend li{display:flex;align-items:center;gap:.4rem}
.key-legend i{display:inline-block;width:26px;height:6px;border-radius:3px;background:var(--k)}
.key-legend .seen i{background:repeating-linear-gradient(90deg,var(--seen) 0 5px,transparent 5px 9px)}
.plates{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:1.25rem;align-items:start}
.col{display:grid;gap:1.25rem;min-width:0}
.plate,.ledger{background:var(--sheet);border:1px solid var(--rule);border-top:5px solid var(--ink)}
.plate{padding:.9rem 1.25rem 1.1rem;min-width:0}
h2{font-size:1.32rem;line-height:1.2;margin:0 0 .35rem;letter-spacing:-.005em}
h2 .num{font:800 1.55rem var(--cond)}
h3{font-size:1rem;margin:1rem 0 .1rem}
.plate p{margin:.25rem 0;font-size:.93rem;max-width:72ch}
.small{font-size:.85rem!important;color:var(--ink2)}
.map{margin:.5rem 0 .4rem;overflow-x:auto}
.map svg{display:block;width:100%;height:auto;max-width:600px}
svg text{font-family:var(--sans);fill:var(--ink)}
svg .t{font-size:17px;font-weight:700}
svg .m{font-size:14px;fill:var(--ink2)}
svg .rel{font:700 15px var(--cond)}
svg .rel.liked,.delta.up{fill:var(--like)} svg .rel.dismissed,.delta.down{fill:var(--bad)}
svg .rel.sim{fill:var(--sim)} svg .rel.seen{fill:var(--seen)}
svg .delta{font:800 17px var(--cond)}
svg .rdn{font:800 29px var(--cond)}
svg .yout{fill:#fff;font-size:13px;font-weight:700}
.e{fill:none;stroke-width:7;stroke-linecap:round;stroke-linejoin:round}
.e.liked{stroke:var(--like)} .e.dismissed{stroke:var(--bad)} .e.sim{stroke:var(--sim)}
.e.seen{stroke:var(--seen);stroke-width:5;stroke-dasharray:2 9}
.e.old{stroke-dasharray:12 9;opacity:.5}
.rd{fill:#fff;stroke:var(--ink);stroke-width:6}
.you{fill:var(--ink)}
.flag{fill:#fbe9e7;stroke:var(--bad);stroke-width:1.5}
svg .flagt{fill:var(--bad);font:700 15px var(--cond)}
.eqrow{display:flex;gap:.6rem;align-items:baseline;margin:.35rem 0}
.key{font:800 1rem var(--cond);min-width:2.2rem;white-space:nowrap}
.eq{display:flex;flex-wrap:wrap;gap:.3rem;list-style:none;padding:0;margin:0}
.eq li{border:1px solid var(--rule);border-top:4px solid var(--k,var(--ink));padding:.05rem .45rem;font-size:.82rem;background:#fff;white-space:nowrap}
.eq b{font:800 .98rem var(--cond)}
.eq .skill{--k:var(--skill)} .eq .like{--k:var(--like)} .eq .bad{--k:var(--bad)} .eq .base{--k:#8d9aa7}
.eq .sum{border-color:var(--ink);background:var(--ink);color:#fff}
table{border-collapse:collapse;width:100%}
th{text-align:left;font-size:.8rem;font-weight:600;color:var(--ink2);padding:.25rem .45rem;border-bottom:2px solid var(--ink)}
td{padding:.35rem .45rem;border-bottom:1px solid var(--rule);font-size:.9rem}
.search td.num,.search th.num{text-align:right;font-variant-numeric:tabular-nums}
.search .fit{font:800 1.05rem var(--cond)}
.queue{table-layout:fixed;font-size:.88rem}
.queue td{height:34px;padding:0 .45rem;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;font-size:.88rem}
.queue .slopecol{width:72px}
.queue td.slope{padding:0;border:0;position:relative;height:auto}
.queue td.slope svg{position:absolute;inset:0;width:100%;height:100%}
.queue line{stroke-linecap:round}
.queue .cold{stroke:#b9c4cd;stroke-width:2}
.queue .hot{stroke:var(--ink);stroke-width:4}
.queue td.moved{background:var(--hl);font-weight:700;box-shadow:inset 4px 0 0 var(--ink)}
.n{display:inline-block;min-width:1.2em;font:800 .95rem var(--cond)}
.qt{color:var(--ink2)} .moved .qt{color:var(--ink)}
details.more{margin-top:.6rem}
details>summary{cursor:pointer}
details.more>summary{font-weight:600;font-size:.9rem;min-height:32px;padding:.2rem 0}
.ledger{margin:1.25rem 0 0}
.ledger>header{padding:.9rem 1.25rem .5rem;display:flex;flex-wrap:wrap;gap:.2rem 1.5rem;align-items:baseline}
.ledger>header p{margin:0;font-size:.9rem;color:var(--ink2)}
details.job{border-top:1px solid var(--rule)}
details.job>summary{list-style:none;display:grid;grid-template-columns:52px minmax(0,1fr) auto 1.4rem;gap:.1rem 1rem;align-items:center;padding:.65rem 1.25rem;min-height:44px}
details.job>summary::-webkit-details-marker{display:none}
details.job>summary::after{content:"+";grid-column:4;grid-row:1;font-size:1.4rem;line-height:1;color:var(--ink2);justify-self:end}
details.job[open]>summary::after{content:"\\2212"}
details.job>summary:hover{background:#f7f9fa}
.sr{grid-row:1/3;width:48px;height:48px;border:5px solid var(--ink);border-radius:50%;display:grid;place-items:center;font:800 1.3rem var(--cond);background:#fff}
.ttl b{font-size:1.02rem}
.meta{color:var(--ink2);font-size:.88rem;margin-left:.35rem}
.why{grid-column:2/4;font-size:.88rem;color:var(--ink2)}
.tag{font:700 .82rem var(--cond);padding:.05rem .5rem;border:1.5px solid currentColor;border-radius:3px;white-space:nowrap;justify-self:end}
.s-new{color:var(--like)} .s-seen{color:var(--seen)} .s-likely_duplicate{color:var(--bad)} .s-similar_seen{color:var(--sim)}
.body{display:grid;grid-template-columns:minmax(0,.9fr) minmax(0,1.1fr);gap:.2rem 2.5rem;padding:0 1.25rem 1.1rem calc(52px + 2.25rem)}
h4{margin:.55rem 0 .25rem;font-size:.82rem;color:var(--ink2);font-weight:600}
.skills{display:flex;flex-wrap:wrap;gap:.3rem;list-style:none;margin:0;padding:0}
.skills li{font-size:.85rem;padding:.05rem .5rem;border:1px solid var(--rule);background:#fff}
.skills .have{border-color:var(--like);color:var(--like);font-weight:600}
.skills .near{border-color:var(--skill);color:var(--skill);font-weight:600}
.skills .miss{color:var(--ink2);border-style:dashed}
.links{margin:0;padding-left:1.1rem;font-size:.88rem}
.route{display:flex;flex-wrap:wrap;list-style:none;margin:.15rem 0 .55rem;padding:0 1.6rem 0 .9rem;row-gap:.3rem}
.route .st{width:16px;flex:none;grid-template-columns:16px}
.route li{display:grid;grid-template-rows:1.25rem 14px auto auto;justify-items:center;min-width:0}
.route .st i{grid-row:2;width:16px;height:16px;margin-top:-1px;border:4px solid var(--ink);border-radius:50%;background:#fff;position:relative;z-index:1}
.route .st span{grid-row:3;font-weight:700;font-size:.85rem;line-height:1.3;white-space:nowrap;padding:0 .2rem}
.route .st small{grid-row:4;font-size:.72rem;color:var(--ink2);white-space:nowrap}
.route .ln{flex:1 1 6.5rem;min-width:6.5rem;max-width:10rem;justify-items:stretch}
.route .ln span{grid-row:1;font:700 .78rem var(--cond);text-align:center;white-space:nowrap;color:var(--k)}
.route .ln::after{content:"";grid-row:2;align-self:center;height:6px;margin:0 -4px;background:var(--k)}
.route .liked{--k:var(--like)} .route .dismissed{--k:var(--bad)} .route .sim{--k:var(--sim)} .route .skill{--k:var(--skill)}
.route .seen{--k:var(--seen)} .route .seen::after{background:repeating-linear-gradient(90deg,var(--seen) 0 5px,transparent 5px 10px)}
.raw{margin-top:.5rem;font-size:.82rem;color:var(--ink2)}
.raw code{display:block;margin-top:.3rem;overflow-wrap:anywhere;font-size:.78rem;line-height:1.45}
footer{padding:1.5rem 0 2.5rem;font-size:.85rem;color:var(--ink2)}
.draw{animation:draw 1s .4s ease-out backwards}
.queue .draw{animation-delay:1.4s}
@keyframes draw{from{stroke-dasharray:1 1;stroke-dashoffset:1}to{stroke-dasharray:1 1;stroke-dashoffset:0}}
@media (prefers-reduced-motion:reduce){.draw{animation:none}}
@media (max-width:980px){.plates{grid-template-columns:minmax(0,1fr)}.intro{grid-template-columns:minmax(0,1fr);align-items:start}}
@media (max-width:640px){
 .in,.wrap{padding:0 .6rem} h1{font-size:1.7rem} .plate{padding:.8rem .6rem 1rem}
 .band nav{margin-left:0;gap:.1rem 1rem}
 .queue .slopecol,.queue td.slope{display:none}
 .queue{table-layout:auto} .queue td{white-space:normal;height:auto;padding:.3rem}
 .queue .qt{display:block;font-size:.8rem}
 details.job>summary{grid-template-columns:44px minmax(0,1fr) 1.2rem;padding:.6rem .8rem;gap:.1rem .7rem}
 details.job>summary::after{grid-column:3}
 .sr{width:42px;height:42px;font-size:1.1rem;border-width:4px;grid-row:1/4}
 .tag{grid-column:2;grid-row:2;justify-self:start}.why{grid-column:2/4}.meta{display:block;margin:0}
 .body{grid-template-columns:minmax(0,1fr);padding:0 .8rem 1rem}
 .search .rel-col{display:none}
 .route{flex-wrap:nowrap} .route .ln{min-width:2.6rem;flex-basis:3.2rem} .route .ln span{font-size:.7rem;overflow:visible}
 .route .st span{font-size:.8rem} .route .st small{font-size:.68rem}
}
"""

MARK = ("<svg width=30 height=22 viewBox='0 0 30 22' aria-hidden=true><path d='M6,16 L15,6 H24' fill=none stroke='#7fd07a' stroke-width=4 stroke-linecap=round stroke-linejoin=round />"
        "<circle cx=6 cy=16 r=4.5 fill='#fff' /><circle cx=24 cy=6 r=4.5 fill='#0e2338' stroke='#fff' stroke-width=2.5 /></svg>")


def main(db_path="jobradar.rl", out="docs/demo.html", job="j05", verdict="LIKED"):
    with closing(relate.connect(db_path, read_only=True)) as db:
        base = rank(db)
        hits, shortlist = discover(db, "engineer")
    after_rows = replay(db_path, job, verdict)
    moved = [(new, new["score"] - old["score"]) for old, new in score_changes(base, after_rows)]
    index = {x["f"]["job"]: x["f"] for x in base}
    search_rows = "".join(
        f"<tr><td><a href='#{e(row['facts']['job'])}'>{e(row['facts']['job'])}</a> {e(row['facts']['title'])}</td>"
        f"<td class='num rel-col'>{row['relevance']:.3f}</td><td class='num fit'>{row['score']}</td>"
        f"<td><span class='tag s-{e(row['facts']['status'])}'>{e(row['facts']['status'])}</span></td></tr>"
        for row in shortlist)
    search = (f"<section class=plate id=search aria-labelledby=search-h><h2 id=search-h>Search for “engineer”</h2>"
              f"<p>Relate found {hits} title matches. {len(shortlist)} are unseen. Personal fit orders those listings using graph evidence.</p>"
              "<table class=search><thead><tr><th scope=col>Unseen listing</th><th scope=col class='num rel-col'>Text score</th>"
              f"<th scope=col class=num>Fit</th><th scope=col>Status</th></tr></thead><tbody>{search_rows}</tbody></table></section>")
    legend = "".join(f"<li class='{c}'><i style='--k:var(--{v})'></i>{n}</li>" for c, v, n in (
        ("", "like", "LIKED"), ("", "bad", "DISMISSED"), ("seen", "seen", "SEEN"), ("", "sim", "SIMILAR_TO"), ("", "skill", "skill links")))
    page = ("<!doctype html><html lang=en><head><meta charset=utf-8><meta name=viewport content='width=device-width,initial-scale=1'>"
            f"<title>jobradar-relate · connected job memory</title><style>{CSS}</style></head><body>"
            f"<div class=band><div class=in><a class=mark href='#top'>{MARK}jobradar-relate</a>"
            "<nav aria-label='Page sections'><a href='#repost'>95 vs 60</a><a href='#search'>Search</a><a href='#feedback'>Replay</a>"
            f"<a href='#all'>All {len(base)} listings</a><a href='{REPO}'>Repository</a></nav></div></div>"
            "<main class=wrap id=top><header class=intro><h1>Which opening is worth a closer look?</h1>"
            "<div><p class=lede>Synthetic data. Every score and evidence path is read from one Relate graph file: "
            f"<code>{e(db_path)}</code> (opened read-only). Deterministic scorer, no API key. <a href='{REPO}'>Repository</a></p>"
            f"<ul class=key-legend aria-label='Line key'>{legend}</ul></div></header>"
            f"<div class=plates><div class=col>{repost_plate(base)}{search}</div>"
            f"<div class=col>{replay_plate(base, after_rows, moved, job, verdict)}</div></div>"
            f"<section class=ledger id=all aria-labelledby=all-h><header><h2 id=all-h>All {len(base)} listings, ranked by the graph</h2>"
            "<p>Open a row for its score parts, graph paths and SIMILAR_TO links.</p></header>"
            + "".join(job_row(x, index, i == 0) for i, x in enumerate(base)) + "</section>"
            "<footer>Generated by <code>make demo</code> from jobradar_relate/demo.py. System fonts and inline SVG only; no scripts, no third-party assets.</footer>"
            "</main></body></html>")
    os.makedirs(os.path.dirname(out) or ".", exist_ok=True); open(out, "w").write(page)
    for x in base: print(f"{x['score']:>3}  {x['f']['job']}  {x['f']['title']} @ {x['f']['company']}  [{x['f']['status']}]")
    for x, dlt in moved: print(f"replay {verdict} {job}: {x['f']['job']} {dlt:+d} -> {x['score']}")
    print("wrote", out)

if __name__ == "__main__":
    main(*sys.argv[1:3])
