"""Single-run comparison specified in docs/preregistration.md."""
from collections import Counter
from contextlib import closing
from fractions import Fraction
import json
from pathlib import Path
import subprocess
import tempfile

import relate
from .facts import gather
from .importer import import_jobs
from .score import fallback

ROOT = Path(__file__).resolve().parents[1]


def validate_labels(records, jobs):
    labels = {}
    for row in records:
        job, verdict = row['id'], row['label']
        if job in labels or verdict not in ('LIKED', 'DISMISSED', 'NEUTRAL'):
            raise ValueError(f'duplicate ID or invalid label for {job}')
        labels[job] = verdict
    if set(labels) != {j['id'] for j in jobs} or len(labels) != 50 or len(jobs) != 50:
        raise ValueError('expected one label for each of the 50 held-out IDs')
    return labels


def metrics(scores, labels):
    pos = [s for j, s in scores.items() if labels[j] == 'LIKED']
    neg = [s for j, s in scores.items() if labels[j] == 'DISMISSED']
    pairs = len(pos) * len(neg)
    credit = Fraction(sum((p > n) * 2 + (p == n) for p in pos for n in neg), 2)
    hits = Fraction(0)
    if pos:
        cutoff = sorted(scores.values(), reverse=True)[len(pos) - 1]
        above = sum(s > cutoff for s in scores.values())
        tied = sum(s == cutoff for s in scores.values())
        hits = sum(s > cutoff for s in pos) + Fraction((len(pos) - above) * pos.count(cutoff), tied)
    return credit, pairs, hits


def main():
    folder = ROOT / 'data/real'
    label_file = folder / 'holdout_labels.json'
    if not label_file.exists():
        raise SystemExit('Stage B labels required at data/real/holdout_labels.json')
    jobs = json.loads((folder / 'djinni_holdout50.json').read_text())
    labels = validate_labels(json.loads(label_file.read_text())['labels'], jobs)
    methods = {name: {} for name in ('new scorer', 'old scorer', 'skill-count baseline')}
    with tempfile.TemporaryDirectory() as tmp:
        path = str(Path(tmp) / 'holdout.rl')
        with closing(relate.connect(path)) as db:
            import_jobs(db, jobs)
        subprocess.run(['relate', 'query', '--database', path], check=True, capture_output=True,
                       text=True, input=(ROOT / 'graph/profile_real.cypher').read_text())
        with closing(relate.connect(path, read_only=True)) as db:
            for job in jobs:
                key = job['id']
                f = gather(db, key)
                methods['new scorer'][key] = fallback(f)['score']
                methods['old scorer'][key] = fallback(f, legacy=True)['score']
                methods['skill-count baseline'][key] = len(f['overlap'])
    counts = Counter(labels.values())
    print('Fictional candidate, AI labels:', ', '.join(f'{k} {counts[k]}' for k in ('LIKED', 'NEUTRAL', 'DISMISSED')))
    credits = {}
    for name, scores in methods.items():
        credit, pairs, hits = metrics(scores, labels)
        credits[name] = credit
        auc = f'{float(credit / pairs):.4f}' if pairs else 'undefined'
        print(f'{name}: AUC LIKED>DISMISSED {auc} ({credit} credit over {pairs} pairs), '
              f'top-{counts["LIKED"]} expected LIKED hits {hits}')
    if not (counts['LIKED'] and counts['DISMISSED']):
        print('Primary outcome undefined: both LIKED and DISMISSED are required.')
        return
    delta = credits['new scorer'] - credits['skill-count baseline']
    outcome = 'win' if delta > 0 else 'loss' if delta < 0 else 'tie'
    print(f'New scorer vs baseline: {outcome}.')


if __name__ == '__main__':
    main()
