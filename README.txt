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

