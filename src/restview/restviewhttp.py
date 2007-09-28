#!/usr/bin/python
"""
HTTP-based ReStructuredText viewer.

Usage:
    restviewhttp [options] filename.rst
or
    restviewhttp [options] directory
or
    restviewhttp --help

Needs docutils and a web browser.  Will syntax highlight if you have pygments
installed.
"""

import os
import re
import sys
import socket
import optparse
import webbrowser
import BaseHTTPServer
import docutils.core
import docutils.writers.html4css1

try:
    import pygments
    import pygments.lexers
    import pygments.formatters
except ImportError:
    pygments = None


__version__ = "0.0.5a"


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
        elif self.path.endswith('.jpg'):
            return self.handle_image(self.translate_path(), 'image/jpeg')
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
            self.send_header("Content-Type", ctype)
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
            if isinstance(html, unicode):
                html = html.encode('UTF-8')
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=UTF-8")
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
        if isinstance(html, unicode):
            html = html.encode('UTF-8')
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=UTF-8")
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
        if pygments is not None:
            writer.translator_class = SyntaxHighlightingHTMLTranslator
        docutils.core.publish_string(rest_input, writer=writer,
                                     settings_overrides={
                                        'stylesheet': self.css_path,
                                        'stylesheet_path': None,
                                        'embed_stylesheet': True})
        return writer.output


class SyntaxHighlightingHTMLTranslator(docutils.writers.html4css1.HTMLTranslator):

    in_doctest = False

    def visit_doctest_block(self, node):
        docutils.writers.html4css1.HTMLTranslator.visit_doctest_block(self, node)
        self.in_doctest = True

    def depart_doctest_block(self, node):
        docutils.writers.html4css1.HTMLTranslator.depart_doctest_block(self, node)
        self.in_doctest = False

    def visit_Text(self, node):
        if self.in_doctest:
            text = node.astext()
            lexer = pygments.lexers.PythonConsoleLexer()
            # noclasses forces inline styles, which is suboptimal
            # figure out a way to include formatter.get_style_defs() into
            # our CSS
            formatter = pygments.formatters.HtmlFormatter(nowrap=True,
                                                          noclasses=True)
            self.body.append(pygments.highlight(text, lexer, formatter))
        else:
            text = node.astext()
            encoded = self.encode(text)
            if self.in_mailto and self.settings.cloak_email_addresses:
                encoded = self.cloak_email(encoded)
            self.body.append(encoded)

    def encode(self, text):
        encoded = docutils.writers.html4css1.HTMLTranslator.encode(self, text)
        encoded = self.link_local_files(encoded)
        return encoded

    def link_local_files(self, text):
        """Replace filenames with hyperlinks."""
        text = re.sub("([-_a-zA-Z0-9]+[.]txt)", r'<a href="\1">\1</a>', text)
        return text


def parse_address(addr):
    """Parse a socket address.

        >>> parse_address('1234')
        ('localhost', 1234)

        >>> parse_address('example.com:1234')
        ('example.com', 1234)

        >>> parse_address('*:1234')
        ('', 1234)

        >>> try: parse_address('notanumber')
        ... except ValueError, e: print e
        Invalid address: notanumber

        >>> try: parse_address('la:la:la')
        ... except ValueError, e: print e
        Invalid address: la:la:la

    """
    if ':' in addr:
        try:
            host, port = addr.split(':')
        except ValueError:
            raise ValueError('Invalid address: %s' % addr)
    else:
        host, port = 'localhost', addr
    if host == '*':
        host = '' # any
    try:
        return (host, int(port))
    except ValueError:
        raise ValueError('Invalid address: %s' % addr)


def get_host_name(listen_on):
    """Convert a listening interface name to a host name."""
    if listen_on == '':
        return socket.gethostname()
    else:
        return socket.gethostbyaddr(listen_on)[0]


def main():
    progname = os.path.basename(sys.argv[0])
    parser = optparse.OptionParser("%prog [options] filename-or-directory",
                    description="Serve ReStructuredText files over HTTP.",
                    prog=progname)
    parser.add_option('-l', '--listen',
                      help='listen on a given port (or interface:port,'
                           ' e.g. *:8080) [default: random port on localhost]',
                      default=None)
    parser.add_option('-b', '--browser',
                      help='open a web browser [default: only if -l'
                           ' was not specified]',
                      action='store_true', default=None)
    opts, args = parser.parse_args(sys.argv[1:])
    if len(args) != 1:
        parser.error("exactly one argument expected")
    if opts.browser is None:
        opts.browser = opts.listen is None
    server = RestViewer(args[0])
    if opts.listen:
        try:
            server.local_address = parse_address(opts.listen)
        except ValueError, e:
            sys.exit(str(e))
    host = get_host_name(server.local_address[0])
    port = server.listen()
    url = 'http://%s:%d/' % (host, port)
    print "Listening on %s" % url
    if opts.browser:
        webbrowser.open(url)
    try:
        server.serve()
    except KeyboardInterrupt:
        pass


if __name__ == '__main__':
    main()

