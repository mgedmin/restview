Changelog
=========

3.0.2 (2024-10-09)
------------------

- Add support for Python 3.12 and 3.13.


3.0.1 (2023-01-10)
------------------

- Add support for Python 3.11.

- Drop support for Python 3.6.

- Restrict readme-renderer to < 37.0, because it switched to a different
  docutils writer (html5_polyglot instead of html4css1), which causes issues
  (`issue 65 <https://github.com/mgedmin/restview/issues/65>`_).  This will
  be fixed properly in a newer release.


3.0.0 (2022-01-12)
------------------

- Drop support for Python 2.7.


2.9.3 (2021-11-29)
------------------

- Fix incompatibility with docutils 0.18.1 that resulted in "Cannot embed
  stylesheet" errors (`issue 61 <https://github.com/mgedmin/restview/pull/61>`_,
  contributed by Sébastien Besson).

- Add support for Python 3.8, 3.9, and 3.10.

- Drop support for Python 3.5.


2.9.2 (2019-04-23)
------------------

- Claim Python 3.7 support.

- Drop Python 3.4 support.


2.9.1 (2018-05-18)
------------------

- Ignore stderr from external commands that successfully produce stdout
  (like warnings printed by setup.py --long-description).
  Fixes `#55 <https://github.com/mgedmin/restview/issues/55>`_.

- Cope with readme_renderer.clean.clean() returning None on failure.


2.9.0 (2018-05-03)
------------------

- Added ``__main__.py`` module to allow package to be executable with
  ``python -m restview``. - SimplyKnownAsG


2.8.1 (2018-01-28)
------------------

- Protect against DNS rebinding attacks.  See `#51
  <https://github.com/mgedmin/restview/issues/51>`_.


2.8.0 (2017-12-07)
------------------

- Claim Python 3.6 support.

- Drop Python 3.3 support.

- New option ``--report-level`` that defaults to 2 (previously this was
  hardcoded to 0).  See `#49 <https://github.com/mgedmin/restview/issues/49>`_.

- Relax ``--strict`` to mean ``--halt-level=2`` (previously it meant
  ``--halt-level=1``).  See `#49`_.


2.7.0 (2016-09-15)
------------------

- New option ``--halt-level`` (`#44
  <https://github.com/mgedmin/restview/pull/44>`_), contributed by Kunshan
  Wang.

- New option ``-B``/``--no-browser`` (`#46
  <https://github.com/mgedmin/restview/issues/46>`_).


2.6.1 (2016-01-05)
------------------

- The ``readme`` dependency was renamed ``readme_renderer`` (fixes
  `#30 <https://github.com/mgedmin/restview/issues/30>`_,
  `#41 <https://github.com/mgedmin/restview/issues/41>`_).


2.6.0 (2015-12-31)
------------------

- Implement ``restview --version`` (`#37
  <https://github.com/mgedmin/restview/issues/37>`_).

- Highlight the bad source line when rendering fails completely due to an
  error, e.g. in ``--strict`` mode (`#40
  <https://github.com/mgedmin/restview/issues/40>`_).


2.5.2 (2015-11-20)
------------------

- Use the right content type for SVG images (`#36
  <https://github.com/mgedmin/restview/issues/36>`_).


2.5.1 (2015-11-17)
------------------

- Support SVG images (`#36 <https://github.com/mgedmin/restview/issues/36>`_).


2.5.0 (2015-10-27)
------------------

- Fix HTML cleaning code in --pypi-strict mode (`#33
  <https://github.com/mgedmin/restview/issues/33>`_).

- Drop Python 2.6 support.

- Claim Python 3.5 support.


2.4.0 (2015-05-27)
------------------

- Drop Python 3.2 support.

- Stop dynamic computation of install_requires in setup.py, this doesn't work
  well in the presence of the pip 7 wheel cache.


2.3.0 (2015-01-26)
------------------

- Follow PyPI's lead and rely on `readme
  <https://pypi.python.org/pypi/readme>`__ for rendering in --pypi-strict mode.
  Fixes https://github.com/mgedmin/restview/issues/28.


2.2.1 (2015-01-06)
------------------

- Fix style loss on autoreloading.
  Fixes https://github.com/mgedmin/restview/issues/25.


2.2.0 (2014-12-10)
------------------

- Reload the page using AJAX to preserve scroll position.
  Fixes https://github.com/mgedmin/restview/issues/22.

- Use the default docutils CSS instead of replacing it wholesale.
  Drop some of our styles, including:

  - left-aligned document title
  - sans-serif font override for document text
  - fully-justified text
  - bold terms in definition lists
  - custom table rendering with just horizontal rules (issue #23)

  Keep other custom style overrides:

  - custom footnote rendering (I really like it)
  - white background for code blocks
  - prettier system error messages
  - unified alignment of code blocks, block quotes and doctests

  Fixes https://github.com/mgedmin/restview/issues/23.

- The ``--css`` option can be provided multiple times and can refer to
  standard stylesheets (the ones provided by docutils as well as the ones
  provided by restview) without specifying the full path.

  For example, if you want to go back to the style used by restview before
  version 2.2.0, you can use ::

    restview --css oldrestview.css ...

  If you want your own custom style on top of the standard docutils
  styles, use ::

    restview --css html4css1.css --css ./path/to/my.css

  And if you want to completely override the stylesheet, use ::

    restview --css ./path/to/my.css

- New option: ``--watch``.  Reloads pages when a given file changes.  Mostly
  useful with ``-e``, but can also come in handy when you're developing your
  CSS.  Can be specified multiple times, e.g. ::

    restview --css my.css -e 'cat one.rst two.rst' -w my.css -w one.rst -w two.rst

- ``restview --long-description`` watches setup.py, README.rst and CHANGES.rst
  for updates and reloads the description automatically.

- Error pages will also reload automatically if the source file changes.

- Error pages in strict mode will mention the filename instead of ``<string>``.

- File watching now pays attention to fractional seconds.


2.1.1 (2014-09-28)
------------------

- Fix TypeError on Python 3 when reporting ReST errors (typically in strict
  mode).
  Fixes https://github.com/mgedmin/restview/issues/21.

- Fix TypeError on Python 3 when using ``--pypi-strict``.


2.1.0 (2014-09-02)
------------------

- ``--pypi-strict`` mode to catch additional problems that break rendering
  on the Python Packaging Index.  ``--long-description`` enables this
  automatically.
  Fixes https://github.com/mgedmin/restview/issues/18.

- Added installation section to the README.
  Fixes https://github.com/mgedmin/restview/issues/19.


2.0.5 (2014-06-09)
------------------

- Avoid Unicode errors on Python 3 when the ReStructuredText file is in an
  encoding that doesn't match the locale.
  Fixes https://github.com/mgedmin/restview/issues/16.

- Avoid Unicode errors on Python 3when there are filenames in an encoding that
  doesn't match the locale.
  Fixes https://github.com/mgedmin/restview/issues/17.


2.0.4 (2014-04-28)
------------------

- Show a clear error when external command fails.
  Fixes https://github.com/mgedmin/restview/issues/14.

- Stop mangling document titles.
  Fixes https://github.com/mgedmin/restview/issues/15.


2.0.3 (2014-02-01)
------------------

- Distinguish document title from section titles with a larger font.
  Fixes https://github.com/mgedmin/restview/issues/12.

- Minor tweaks and fixes to make restview work better on Windows (e.g. all
  tests now pass).


2.0.2 (2013-10-02)
------------------

- Suppress errors when file disappears while restview is polling for changes.
  Fixes https://github.com/mgedmin/restview/issues/11.

- Added a favicon.  Fixes https://github.com/mgedmin/restview/issues/8.


2.0.1 (2013-05-01)
------------------

- Always require Pygments.  Fixes https://github.com/mgedmin/restview/issues/9.


2.0 (2013-04-04)
----------------

- Python 3 support (LP#1093098).  Patch by Steven Myint (git@stevenmyint.com).

- Moved to Github.

- 100% test coverage.

- Automatically reload the web page when the source file changes (LP#965746).
  Patch by speq (sp@bsdx.org), with modifications by Eric Knibbe and Marius
  Gedminas.

- New option: restview --long-description (shows the output of python setup.py
  --long-description).

- New option: restview --strict. Patch by Steven Myint (git@stevenmyint.com).

- Improve auto-linkification of local file names:

  * allow subdirectories
  * recognize .rst extensions

- Many improvements by Eric Knibbe:

  * ``restview dirname`` now ignores hidden subdirectories.
  * files in directory listings are sorted case-insensitively.
  * allow serving gif and jpg images.
  * CSS rules for rubric, sidebars, and many other things.
  * syntax highlighting for code blocks.
  * improved HTTP error messages.
  * HTTP headers to prevent browser caching of dynamic content.


1.2.2 (2010-09-14)
------------------

- setup.py no longer requires docutils (LP#637423).


1.2.1 (2010-09-12)
------------------

- Handle spaces and other special characters in URLs (LP#616335).

- Don't linkify filenames inside external references (LP#634827).


1.2 (2010-08-06)
----------------

- "SEVERE" docutils errors now display a message and unformatted file in
  the browser, instead of a traceback on the console.
- New command-line option, -e COMMAND.
- Added styles for admonitions; many other important styles are still missing.


1.1.3 (2009-10-25)
------------------

- Spell 'extras_require' correctly in setup.py (LP#459840).
- Add a MANIFEST.in for complete source distributions (LP#459845).


1.1.2 (2009-10-14)
------------------

- Fix for 'localhost' name resolution error on Mac OS X.


1.1.1 (2009-07-13)
------------------

- Launches the web server in the background.


1.1.0 (2008-08-26)
------------------

- Accepts any number of files and directories on the command line.


1.0.1 (2008-07-26)
------------------

- New option: --css.  Accepts a filename or an HTTP/HTTPS URL.


1.0.0 (2008-07-26)
------------------

- Bumped version number to reflect the stability.
- Minor CSS tweaks.


0.0.5 (2007-09-29)
------------------

- Create links to other local files referenced by name.
- Use pygments (if available) to syntax-highlight doctest blocks.
- Handle JPEG images.


0.0.4 (2007-09-28)
------------------

- Remove the unstable Gtk+ version.


0.0.3 (2007-09-28)
------------------

- Use setuptools for packaging.


0.0.2 (2007-01-21)
------------------

- Browser-based version.
- Command line options -l, -b (thanks to Charlie Shepherd).
- CSS tweaks.
- Unicode bugfix.
- Can browse directory trees.
- Can serve images.


0.0.1 (2005-12-06)
------------------

- PyGtk+ version with GtkMozEmbed.  Not very stable.
