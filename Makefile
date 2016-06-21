PYTHON = python

FILE_WITH_VERSION = src/restview/restviewhttp.py
FILE_WITH_CHANGELOG = CHANGES.rst
VCS_STATUS = git status --porcelain
VCS_EXPORT = git archive --format=tar --prefix=tmp/tree/ HEAD | tar -xf -
VCS_TAG = git tag
VCS_COMMIT_AND_PUSH = git commit -av -m "Post-release version bump" && git push && git push --tags


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

.PHONY: dist
dist:
	$(PYTHON) setup.py -q sdist bdist_wheel

.PHONY: distcheck
distcheck:
	# Bit of a chicken-and-egg here, but if the tree is unclean, make
	# distcheck will fail.
ifndef FORCE
	@test -z "`$(VCS_STATUS) 2>&1`" || { echo; echo "Your working tree is not clean" 1>&2; $(VCS_STATUS); exit 1; }
endif
	make dist
	pkg_and_version=`$(PYTHON) setup.py --name`-`$(PYTHON) setup.py --version` && \
	rm -rf tmp && \
	mkdir tmp && \
	$(VCS_EXPORT) && \
	cd tmp && \
	tar xvzf ../dist/$$pkg_and_version.tar.gz && \
	diff -ur $$pkg_and_version tree -x PKG-INFO -x setup.cfg -x '*.egg-info' && \
	cd $$pkg_and_version && \
	make dist check && \
	cd .. && \
	mkdir one two && \
	cd one && \
	tar xvzf ../../dist/$$pkg_and_version.tar.gz && \
	cd ../two/ && \
	tar xvzf ../$$pkg_and_version/dist/$$pkg_and_version.tar.gz && \
	cd .. && \
	diff -ur one two -x SOURCES.txt && \
	cd .. && \
	rm -rf tmp && \
	echo "sdist seems to be ok"

.PHONY: releasechecklist
releasechecklist:
	@$(PYTHON) setup.py --version | grep -qv dev || { \
	    echo "Please remove the 'dev' suffix from the version number in $(FILE_WITH_VERSION)"; exit 1; }
	@$(PYTHON) setup.py --long-description | rst2html --exit-status=2 > /dev/null
	@ver_and_date="`$(PYTHON) setup.py --version` (`date +%Y-%m-%d`)" && \
	    grep -q "^$$ver_and_date$$" $(FILE_WITH_CHANGELOG) || { \
	        echo "$(FILE_WITH_CHANGELOG) has no entry for $$ver_and_date"; exit 1; }
	make distcheck

.PHONY: release
release: releasechecklist
	# I'm chicken so I won't actually do these things yet
	@echo "Please run"
	@echo
	@echo "  rm -rf dist && $(PYTHON) setup.py -q sdist bdist_wheel && twine upload dist/* && $(VCS_TAG) `$(PYTHON) setup.py --version`"
	@echo
	@echo "Please increment the version number in $(FILE_WITH_VERSION)"
	@echo "and add a new empty entry at the top of the changelog in $(FILE_WITH_CHANGELOG), then"
	@echo
	@echo '  $(VCS_COMMIT_AND_PUSH)'
	@echo

bin/py.test: bin/pip
	bin/pip install pytest mock

bin/restview: bin/pip setup.py
	bin/pip install -e .

bin/pip: .venv/bin/pip
	ln -sf .venv/bin bin

.venv/bin/pip:
	virtualenv -p $(PYTHON) .venv
