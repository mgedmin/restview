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
import gtk.gdk
import urllib
import gtkmozembed
import docutils.core
import docutils.writers.html4css1


def path2fileurl(filename):
    pathname = os.path.abspath(filename)
    return 'file://' + urllib.pathname2url(pathname)


class RestViewer:

    default_title = "(untitled)"
    css_path = os.path.join(os.path.dirname(__file__), 'default.css')

    def __init__(self):
        self._build_ui()
        self.filename = None

    def _build_ui(self):
        # TODO: use glade
        self.win = gtk.Window()
        self.win.set_default_size(800, 600)
        vbox = gtk.VBox()
        self.win.add(vbox)

        main_menu = gtk.MenuBar()
        vbox.pack_start(main_menu, False)

        file_menu = gtk.MenuItem("_File")
        main_menu.add(file_menu)
        menu = gtk.Menu()
        file_menu.set_submenu(menu)
        exit = gtk.MenuItem("E_xit")
        exit.connect("activate", lambda *args: gtk.main_quit())
        menu.add(exit)

        view_menu = gtk.MenuItem("_View")
        main_menu.add(view_menu)
        menu = gtk.Menu()
        view_menu.set_submenu(menu)
        refresh = gtk.MenuItem("_Refresh")
        refresh.connect("activate", self.on_refresh)
        menu.add(refresh)

        self.moz = gtkmozembed.MozEmbed()
        vbox.pack_start(self.moz)
        self.moz.connect("title", self.update_title)

        self.win.show_all()
        self.win.connect("destroy", gtk.main_quit)

    def on_refresh(self, *args):
        if self.filename:
            self.render_rest_file(self.filename)

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
        self.filename = filename

    def rest_to_html(self, rest_input):
        writer = docutils.writers.html4css1.Writer()
        docutils.core.publish_string(rest_input, writer=writer,
                                     settings_overrides={
                                        'stylesheet': self.css_path,
                                        'embed_stylesheet': True})
        return writer.output


if __name__ == '__main__':
    g = RestViewer()
    if len(sys.argv) > 1:
        g.render_rest_file(sys.argv[1])
    gtk.main()

