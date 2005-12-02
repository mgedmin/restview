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


        actions = gtk.ActionGroup("Actions")
        actions.add_actions([
                    # action, stockid, label[, accelerator, tooltip, action]
                    ("FileMenu", None, "_File"),
                    ("ViewMenu", None, "_View"),
                    ("ViewMenu", None, "_View"),
                    ("Quit", gtk.STOCK_QUIT, "_Quit", "<control>Q",
                        "Quit",
                        lambda action: gtk.main_quit()),
                    ("Reload", gtk.STOCK_REFRESH, "_Reload", "<control>R",
                        "Reload",
                        self.on_refresh),
                ])

        ui = gtk.UIManager()
        ui.insert_action_group(actions, 0)
        self.win.add_accel_group(ui.get_accel_group())
        ui.add_ui_from_string("""
            <ui>
              <menubar name='MenuBar'>
                <menu action='FileMenu'>
                  <menuitem action='Quit'/>
                </menu>
                <menu action='ViewMenu'>
                  <menuitem action='Reload'/>
                </menu>
              </menubar>
            </ui>
        """)
        main_menu = ui.get_widget("/MenuBar")
        vbox.pack_start(main_menu, False)

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

