PY := PYTHONPATH=. .venv/bin/python
QUERY ?= engineer
export QUERY
.PHONY: search eval demo venv test import build score sqlite
venv:
	python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
test eval demo search: | .venv/bin/python
.venv/bin/python:
	$(MAKE) venv
test:
	$(PY) -m unittest discover -s tests -v
import:  # additive MERGE into ./jobradar.rl, then the synthetic profile layer
	$(PY) -m jobradar_relate.importer data/sample_jobs.json jobradar.rl
	relate query --database jobradar.rl < graph/profile.cypher >/dev/null
build:  # fresh graph in $(OUT), never touches jobradar.rl; usage: make build OUT=/tmp/x.rl
	test ! -e $(OUT)
	$(PY) -m jobradar_relate.importer data/sample_jobs.json $(OUT)
	relate query --database $(OUT) < graph/profile.cypher >/dev/null
score:
	$(PY) -m jobradar_relate.score jobradar.rl j02 j06 j09
sqlite:  # synthetic SQLite -> JSON -> graph
	$(PY) data/make_sample_sqlite.py /tmp/jr-sample.sqlite && $(PY) -m jobradar_relate.sqlite_adapter /tmp/jr-sample.sqlite > /tmp/jr-sample.json
demo:  # one command, no API key; writes docs/demo.html
	$(PY) -m jobradar_relate.demo jobradar.rl docs/demo.html
eval:  # graph scorer vs context-free baseline on eval/pairs.json -> eval/results.md
	$(PY) -m jobradar_relate.evaluate jobradar.rl eval/results.md
search:
	$(PY) -m jobradar_relate.discover -- "$$QUERY"
