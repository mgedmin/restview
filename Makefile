PYTHON = python3


.PHONY: all
all: bin/restview bin/pytest    ##: build a local virtualenv (default target)


.PHONY: test
test:                           ##: run tests
	tox -p auto

.PHONY: coverage
coverage:                       ##: measure test coverage
	tox -e coverage

.PHONY: diff-cover
diff-cover: coverage            ##: show untested code in this branch
	diff-cover coverage.xml

.PHONY: clean
clean:                          ##: remove build artifacts
	rm -rf bin .venv


FILE_WITH_VERSION = src/restview/restviewhttp.py
include release.mk


bin/pytest: | bin/pip
	bin/pip install pytest
	ln -sfr .venv/$@ $@

bin/restview: setup.py | bin/pip
	bin/pip install -e .
	ln -sfr .venv/$@ $@

bin/pip: | .venv/bin/pip
	mkdir -p bin
	ln -sfr .venv/$@ $@

.venv/bin/pip:
	virtualenv -p $(PYTHON) .venv
