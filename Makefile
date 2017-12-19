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
	detox

.PHONY: coverage
coverage:
	tox -e coverage

.PHONY: diff-cover
diff-cover: coverage
	diff-cover coverage.xml


include release.mk


bin/py.test: bin/pip
	bin/pip install pytest mock

bin/restview: bin/pip setup.py
	bin/pip install -e .

bin/pip: .venv/bin/pip
	ln -sf .venv/bin bin

.venv/bin/pip:
	virtualenv -p $(PYTHON) .venv
