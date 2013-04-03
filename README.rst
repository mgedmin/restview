========
restview
========

|buildstatus|_

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

  restview -e 'python setup.py --long-description' --strict

This is so useful restview has a shortcut for it ::

  restview --long-description --strict

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
--long-description    run "python setup.py --long-description" to produce
                      ReStructuredText
--css=URL-or-FILENAME
                      use the specified stylesheet
--strict              halt at the slightest problem


.. |buildstatus| image:: https://api.travis-ci.org/mgedmin/restview.png?branch=master
.. _buildstatus: https://travis-ci.org/mgedmin/restview
