========
restview
========

A viewer for ReStructuredText documents that renders them on the fly.

Pass the name of a ReStructuredText document to restview, and it will
launch a web server on localhost:random-port and open a web browser.
Every time you reload the page, restview will reload the document from
disk and render it.  This is very convenient for previewing a document
while you're editing it.

You can also pass the name of a directory, and restview will recursively
look for files that end in .txt or .rst and present you with a list.


Changelog
=========

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

- New option: --css.  Accepts a filename or a HTTP/HTTPS URL.

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

