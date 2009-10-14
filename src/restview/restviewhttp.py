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
import threading
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


__version__ = "1.1.2"


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
        root = self.server.renderer.root
        if self.path == '/':
            if isinstance(root, str):
                if os.path.isdir(root):
                    return self.handle_dir(root)
                else:
                    return self.handle_rest_file(root)
            else:
                return self.handle_list(root)
        elif '..' in self.path:
            self.send_error(404, "File not found") # no hacking!
        elif self.path.endswith('.png'):
            return self.handle_image(self.translate_path(), 'image/png')
        elif self.path.endswith('.jpg'):
            return self.handle_image(self.translate_path(), 'image/jpeg')
        elif self.path.endswith('.txt') or self.path.endswith('.rst'):
            return self.handle_rest_file(self.translate_path())
        else:
            self.send_error(404, "File not found: %s" % self.path)

    def translate_path(self):
        root = self.server.renderer.root
        path = self.path.lstrip('/')
        if not isinstance(root, str):
            idx, path = path.split('/', 1)
            root = root[int(idx)]
        if not os.path.isdir(root):
            root = os.path.dirname(root)
        return os.path.join(root, path)

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

    def collect_files(self, dirname):
        if not dirname.endswith('/'):
            dirname += '/'
        files = []
        for dirpath, dirnames, filenames in os.walk(dirname):
            dirnames[:] = [dn for dn in dirnames
                           if dn != '.svn' and not dn.endswith('.egg-info')]
            for fn in filenames:
                if fn.endswith('.txt') or fn.endswith('.rst'):
                    prefix = dirpath[len(dirname):]
                    files.append(os.path.join(prefix, fn))
        files.sort()
        return files

    def handle_dir(self, dirname):
        files = [(fn, fn) for fn in self.collect_files(dirname)]
        html = self.render_dir_listing('RST files in %s' % dirname, files)
        if isinstance(html, unicode):
            html = html.encode('UTF-8')
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=UTF-8")
        self.send_header("Content-Length", str(len(html)))
        self.end_headers()
        return html

    def handle_list(self, list_of_files_or_dirs):
        files = []
        for idx, fn in enumerate(list_of_files_or_dirs):
            if os.path.isdir(fn):
                files.extend([(os.path.join(str(idx), f),
                               os.path.join(fn, f))
                               for f in self.collect_files(fn)])
            else:
                files.append((os.path.join(str(idx), os.path.basename(fn)),
                              fn))
        html = self.render_dir_listing('RST files', files)
        if isinstance(html, unicode):
            html = html.encode('UTF-8')
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=UTF-8")
        self.send_header("Content-Length", str(len(html)))
        self.end_headers()
        return html

    def render_dir_listing(self, title, files):
        files = ''.join([FILE_TEMPLATE.replace('$href', href)
                                      .replace('$file', fn)
                         for href, fn in files])
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
  <li><a href="$href">$file</a></li>\
"""


class RestViewer(object):
    """Web server that renders ReStructuredText on the fly."""

    server_class = BaseHTTPServer.HTTPServer
    handler_class = MyRequestHandler

    local_address = ('localhost', 0)

    # only set one of those
    css_url = None
    css_path = os.path.join(os.path.dirname(os.path.realpath(__file__)),
                            'default.css')

    def __init__(self, root):
        self.root = root

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
        if self.css_url:
            settings_overrides={'stylesheet': self.css_url,
                                'stylesheet_path': None,
                                'embed_stylesheet': False}
        elif self.css_path:
            settings_overrides={'stylesheet': self.css_path,
                                'stylesheet_path': None,
                                'embed_stylesheet': True}
        docutils.core.publish_string(rest_input, writer=writer,
                                     settings_overrides=settings_overrides)
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
    """Convert a listening interface name to a host name.

    The important part is to convert 0.0.0.0 to the system hostname, everything
    else can be left as is.
    """
    try:
        ip_addr = socket.inet_aton(listen_on)
    except socket.error: # probably a hostname or ''
        ip_addr = None
    if listen_on == '' or ip_addr == '\0\0\0\0':
        return socket.gethostname()
    else:
        return listen_on


def main():
    progname = os.path.basename(sys.argv[0])
    parser = optparse.OptionParser("%prog [options] filename-or-directory [...]",
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
    parser.add_option('--css',
                      help='use the specified stylesheet',
                      action='store', dest='css_path', default=None)
    opts, args = parser.parse_args(sys.argv[1:])
    if not args:
        parser.error("at least one argument expected")
    if opts.browser is None:
        opts.browser = opts.listen is None
    if len(args) == 1:
        server = RestViewer(args[0])
    else:
        server = RestViewer(args)
    if opts.css_path:
        if (opts.css_path.startswith('http://') or
            opts.css_path.startswith('https://')):
            server.css_url = opts.css_path
            server.css_path = None
        else:
            server.css_path = opts.css_path
            server.css_url = None
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
        # launch the web browser in the background as it may block
        t = threading.Thread(target=webbrowser.open, args=(url,))
        t.setDaemon(True)
        t.start()
    try:
        server.serve()
    except KeyboardInterrupt:
        pass


if __name__ == '__main__':
    main()

