#!/usr/bin/python
"""
Gtk+ ReStructuredText viewer.

Usage:
    restview  filename.rst

Needs PyGtk, gnome-python-extras and docutils.
"""

import os
import sys
import gtk
import urllib
import gtkmozembed
import docutils.core
import docutils.writers.html4css1


def path2fileurl(filename):
    pathname = os.path.abspath(filename)
    return 'file://' + urllib.pathname2url(pathname)


class RestViewer:

    default_title = "(untitled)"

    def __init__(self):
        self.moz = gtkmozembed.MozEmbed()
        self.win = gtk.Window()
        self.win.set_default_size(800, 600)
        self.win.add(self.moz)
        self.win.show_all()
        self.win.connect("destroy", gtk.main_quit)
        self.moz.connect("title", self.update_title)

    def update_title(self, mozwidget):
        title = self.moz.get_title()
        if not title:
            title = self.default_title
        self.win.set_title(title + " - ReST Viewer")

    def render_html_data(self, html_data, baseurl='file:///'):
        self.moz.render_data(html_data, long(len(html_data)), baseurl,
                             'text/html')

    def render_rest_data(self, rest_data, baseurl='file:///'):
        html_data = self.rest_to_html(rest_data)
        self.render_html_data(html_data, baseurl)

    def render_rest_file(self, filename):
        self.default_title = os.path.basename(filename)
        baseurl = path2fileurl(filename)
        self.render_rest_data(file(filename).read(), baseurl)

    def rest_to_html(self, rest_input):
        writer = docutils.writers.html4css1.Writer()
        docutils.core.publish_string(rest_input, writer=writer)
        return writer.output


if __name__ == '__main__':
    g = RestViewer()
    g.render_rest_file(sys.argv[1])
    gtk.main()

