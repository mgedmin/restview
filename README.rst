========
restview
========

|buildstatus|_ |coverage|_

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
-l PORT, --listen=PORT
                      listen on a given port (or interface:port, e.g.
                      \*:8080) [default: random port on localhost]
-b, --browser         open a web browser [default: only if -l was not
                      specified]
-e COMMAND, --execute=COMMAND
                      run a command to produce ReStructuredText
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
--strict              halt at the slightest problem
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


.. |buildstatus| image:: https://api.travis-ci.org/mgedmin/restview.svg?branch=master
.. _buildstatus: https://travis-ci.org/mgedmin/restview

.. |coverage| image:: https://coveralls.io/repos/mgedmin/restview/badge.svg?branch=master
.. _coverage: https://coveralls.io/r/mgedmin/restview
