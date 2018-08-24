PYTHON = python

FILE_WITH_VERSION = src/restview/restviewhttp.py
FILE_WITH_CHANGELOG = CHANGES.rst


.PHONY: default
default: all


.PHONY: all
all: bin/restview bin/py.test


.PHONY: test
test: bin/py.test bin/restview
	bin/py.test

.PHONY: check
check:
	tox

.PHONY: coverage
coverage:
	tox -e coverage

.PHONY: diff-cover
diff-cover: coverage
	diff-cover coverage.xml


clean:
	rm -rf bin .venv


include release.mk


bin/py.test: | bin/pip
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
