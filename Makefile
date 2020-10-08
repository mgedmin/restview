PYTHON = python

FILE_WITH_VERSION = src/restview/restviewhttp.py
FILE_WITH_CHANGELOG = CHANGES.rst


.PHONY: default
default: all


.PHONY: all
all: bin/restview bin/pytest


.PHONY: test check
test check:
	tox -p auto

.PHONY: coverage
coverage:
	tox -e coverage

.PHONY: diff-cover
diff-cover: coverage
	diff-cover coverage.xml


clean:
	rm -rf bin .venv


include release.mk


bin/pytest: | bin/pip
	bin/pip install pytest mock
	ln -sfr .venv/$@ $@

bin/restview: setup.py | bin/pip
	bin/pip install -e .
	ln -sfr .venv/$@ $@

bin/pip: | .venv/bin/pip
	mkdir -p bin
	ln -sfr .venv/$@ $@

.venv/bin/pip:
	virtualenv -p $(PYTHON) .venv
