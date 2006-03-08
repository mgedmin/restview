#!/usr/bin/python
"""
HTTP-based ReStructuredText viewer.

Usage:
    restviewhttp filename.rst
or
    restviewhttp directory

Needs docutils and a web browser.
"""

import os
import sys
import webbrowser
import BaseHTTPServer
import docutils.core
import docutils.writers.html4css1

__version__ = "0.0.1"


class MyRequestHandler(BaseHTTPServer.BaseHTTPRequestHandler):
    """HTTP request handler that renders ReStructuredText on the fly."""

    server_version = "restviewhttp/" + __version__

    def do_GET(self):
        content = self.do_GET_or_HEAD()
        if content:
            self.wfile.write(content)

    def do_HEAD(self):
        content = self.do_GET_or_HEAD()

    def do_GET_or_HEAD(self):
        if self.path == '/':
            if os.path.isdir(self.server.renderer.filename):
                return self.handle_dir(self.server.renderer.filename)
            else:
                return self.handle_rest_file(self.server.renderer.filename)
        elif '..' in self.path:
            self.send_error(404, "File not found") # no hacking!
        elif self.path.endswith('.png'):
            return self.handle_image(self.translate_path(), 'image/png')
        elif self.path.endswith('.txt') or self.path.endswith('.rst'):
            return self.handle_rest_file(self.translate_path())
        else:
            self.send_error(404, "File not found")

    def translate_path(self):
        basedir = self.server.renderer.filename
        if not os.path.isdir(basedir):
            basedir = os.path.dirname(basedir)
        return os.path.join(basedir, self.path.lstrip('/'))

    def handle_image(self, filename, ctype):
        try:
            data = file(filename, 'rb').read()
        except IOError:
            self.send_error(404, "File not found")
        else:
            self.send_response(200)
            self.send_header("Content-type", ctype)
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            return data

    def handle_rest_file(self, filename):
        try:
            html = self.server.renderer.render_rest_file(filename)
        except IOError, e:
            self.log_error("%s" % e)
            self.send_error(404, "File not found")
        else:
            self.send_response(200)
            self.send_header("Content-type", "text/html; charset=UTF-8")
            self.send_header("Content-Length", str(len(html)))
            self.end_headers()
            return html

    def handle_dir(self, dirname):
        if not dirname.endswith('/'):
            dirname += '/'
        files = []
        for dirpath, dirnames, filenames in os.walk(dirname):
            if '.svn' in dirnames:
                dirnames.remove('.svn')
            for fn in filenames:
                if fn.endswith('.txt') or fn.endswith('.rst'):
                    prefix = dirpath[len(dirname):]
                    files.append(os.path.join(prefix, fn))
        files.sort()
        html = self.render_dir_listing('RST files in %s' % dirname, files)
        self.send_response(200)
        self.send_header("Content-type", "text/html; charset=UTF-8")
        self.send_header("Content-Length", str(len(html)))
        self.end_headers()
        return html

    def render_dir_listing(self, title, files):
        files = ''.join([FILE_TEMPLATE.replace('$file', fn) for fn in files])
        return DIR_TEMPLATE.replace('$title', title).replace('$files', files)


DIR_TEMPLATE = """\
<html>
<head><title>$title</title></head>
<body>
<h1>$title</h1>
<ul>
  $files
</ul>
</body>
</html>
"""

FILE_TEMPLATE = """\
  <li><a href="$file">$file</a></li>\
"""


class RestViewer(object):
    """Web server that renders ReStructuredText on the fly."""

    server_class = BaseHTTPServer.HTTPServer
    handler_class = MyRequestHandler

    local_address = ('localhost', 0)

    css_path = os.path.join(os.path.dirname(os.path.realpath(__file__)),
                            'default.css')

    def __init__(self, filename):
        self.filename = filename

    def listen(self):
        """Start listening on a TCP port.

        Returns the port number.
        """
        self.server = self.server_class(self.local_address, self.handler_class)
        self.server.renderer = self
        return self.server.socket.getsockname()[1]

    def serve(self):
        """Wait for HTTP requests and serve them.

        This function does not return.
        """
        self.server.serve_forever()

    def render_rest_file(self, filename):
        """Render ReStructuredText from a file."""
        return self.rest_to_html(file(filename).read())

    def rest_to_html(self, rest_input):
        """Render ReStructuredText."""
        writer = docutils.writers.html4css1.Writer()
        docutils.core.publish_string(rest_input, writer=writer,
                                     settings_overrides={
                                        'stylesheet': self.css_path,
                                        'stylesheet_path': None,
                                        'embed_stylesheet': True})
        return writer.output


def main():
    if len(sys.argv) < 2:
        print >> sys.stderr, "Usage: %s pathname" % sys.argv[0]
    server = RestViewer(sys.argv[1])
    port = server.listen()
    url = 'http://localhost:%d/' % port
    print "Listening on %s" % url
    webbrowser.open(url)
    try:
        server.serve()
    except KeyboardInterrupt:
        pass


if __name__ == '__main__':
    main()

