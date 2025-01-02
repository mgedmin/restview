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
#
# override the release recipe in release.mk
define release_recipe =
$(default_release_recipe_publish_and_tag)
$(default_release_recipe_increment_and_push)
	@echo "Then please create a GitHub release with"
	@echo
	@echo "  gh release create"
	@echo
endef


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
