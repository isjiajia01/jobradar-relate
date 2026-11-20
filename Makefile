PY := PYTHONPATH=. .venv/bin/python
.PHONY: venv test import score sqlite
venv:
	python3 -m venv .venv && .venv/bin/pip install relate-db
test:
	$(PY) -m unittest discover -s tests -v
import:
	$(PY) -m jobradar_relate.importer data/sample_jobs.json jobradar.rl
score:
	$(PY) -m jobradar_relate.score jobradar.rl j02 j06 j09
sqlite:  # synthetic SQLite -> JSON -> graph
	$(PY) data/make_sample_sqlite.py /tmp/jr-sample.sqlite && $(PY) -m jobradar_relate.sqlite_adapter /tmp/jr-sample.sqlite > /tmp/jr-sample.json
