========
restview
========

|buildstatus|_ |appveyor|_ |coverage|_

A viewer for ReStructuredText documents that renders them on the fly.

Pass the name of a ReStructuredText document to ``restview``, and it will
launch a web server on localhost:random-port and open a web browser.
Every time you reload the page, restview will reload the document from
disk and render it.  This is very convenient for previewing a document
while you're editing it.

You can also pass the name of a directory, and restview will recursively
look for files that end in .txt or .rst and present you with a list.

Finally, you can make sure your Python package has valid ReStructuredText
in the long_description field by using ::

  restview --long-description


Synopsis
========

Usage: ``restview [options] filename-or-directory [...]``

-h, --help            show this help message and exit
--version             show program's version number and exit
-l PORT, --listen=PORT
                      listen on a given port (or interface:port, e.g.
                      \*:8080) [default: random port on localhost]
--allowed-hosts HOSTS
                      allowed values for the Host header (default: localhost
                      only, unless you specify -l \*:port, in which case any
                      Host: is accepted by default)
-b, --browser         open a web browser [default: only if -l was not
                      specified]
-B, --no-browser      don't open a web browser
-e COMMAND, --execute=COMMAND
                      run a command to produce ReStructuredText on stdout
-w FILENAME, --watch=FILENAME
                      reload the page when a file changes (use with
                      --execute); can be specified multiple times
--long-description    run "python setup.py --long-description" to produce
                      ReStructuredText; also enables --pypi-strict and watches
                      the usual long description sources (setup.py, README.rst,
                      CHANGES.rst)
--css=URL-or-FILENAME
                      use the specified stylesheet; can be specified multiple
                      times [default: html4css1.css,restview.css]
--report-level REPORT_LEVEL
                      set the "report_level" option of docutils; restview
                      will report system messages at or above this level
                      (1=info, 2=warnings, 3=errors, 4=severe)
--halt-level HALT_LEVEL
                      set the "halt_level" option of docutils; restview will
                      stop processing the document when a system message at
                      or above this level (1=info, 2=warnings, 3=errors,
                      4=severe) is logged
--strict              halt at the slightest problem; equivalent to --halt-
                      level=2
--pypi-strict         enable additional restrictions that PyPI performs


Installation
============

On .deb based systems (e.g. Ubuntu) ::

  sudo apt-get install python-pip
  sudo pip install restview

On .rpm based systems (e.g. Fedora) ::

  su
  yum install python-pip
  pip install restview


.. |buildstatus| image:: https://github.com/mgedmin/restview/workflows/build/badge.svg?branch=master
.. _buildstatus: https://github.com/mgedmin/restview/actions

.. |appveyor| image:: https://ci.appveyor.com/api/projects/status/github/mgedmin/restview?branch=master&svg=true
.. _appveyor: https://ci.appveyor.com/project/mgedmin/restview

.. |coverage| image:: https://coveralls.io/repos/mgedmin/restview/badge.svg?branch=master
.. _coverage: https://coveralls.io/r/mgedmin/restview
