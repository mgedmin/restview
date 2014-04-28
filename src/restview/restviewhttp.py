#!/usr/bin/python
"""
HTTP-based ReStructuredText viewer.

Usage:
    restview [options] filename.rst [...]
or
    restview [options] directory [...]
or
    restview [options] -e "command"
or
    restview [options] --long-description
or
    restview --help

Needs docutils and a web browser. Will syntax-highlight code or doctest blocks
(needs pygments).
"""
from __future__ import print_function

import os
import re
import sys
import time
import socket
import optparse
import threading
import subprocess
import webbrowser

try:
    import BaseHTTPServer
except ImportError:
    import http.server as BaseHTTPServer

try:
    import SocketServer
except ImportError:
    import socketserver as SocketServer

try:
    from html import escape
except ImportError:
    from cgi import escape

try:
    from urllib import unquote
except ImportError:
    from urllib.parse import unquote

try:
    from urlparse import parse_qs
except ImportError:
    from urllib.parse import parse_qs

import docutils.core
import docutils.writers.html4css1
import pygments
from pygments import lexers, formatters


try:
    unicode
except NameError:
    unicode = str


__version__ = "2.0.4"


class MyRequestHandler(BaseHTTPServer.BaseHTTPRequestHandler):
    """HTTP request handler that renders ReStructuredText on the fly."""

    server_version = "restviewhttp/" + __version__

    def do_GET(self):
        content = self.do_GET_or_HEAD()
        if content:
            self.wfile.write(content)

    def do_HEAD(self):
        self.do_GET_or_HEAD()

    def do_GET_or_HEAD(self):
        self.path = unquote(self.path)
        if '..' in self.path:
            self.send_error(400, "Bad request") # no hacking!
            return
        root = self.server.renderer.root
        command = self.server.renderer.command
        if self.path == '/':
            if command:
                return self.handle_command(command)
            elif isinstance(root, str):
                if os.path.isdir(root):
                    return self.handle_dir(root)
                else:
                    return self.handle_rest_file(root)
            else:
                return self.handle_list(root)
        elif self.path.startswith('/polling?'):
            query = parse_qs(self.path.partition('?')[-1])
            pathname = query['pathname'][0]
            if pathname == '/' and isinstance(root, str):
                pathname = root
            else:
                pathname = self.translate_path(pathname)
            old_mtime = int(query['mtime'][0])
            return self.handle_polling(pathname, old_mtime)
        elif self.path == '/favicon.ico':
            return self.handle_image(self.server.renderer.favicon_path,
                                     'image/x-icon')
        elif self.path.endswith('.gif'):
            return self.handle_image(self.translate_path(), 'image/gif')
        elif self.path.endswith('.png'):
            return self.handle_image(self.translate_path(), 'image/png')
        elif self.path.endswith('.jpg') or self.path.endswith('.jpeg'):
            return self.handle_image(self.translate_path(), 'image/jpeg')
        elif self.path.endswith('.txt') or self.path.endswith('.rst'):
            return self.handle_rest_file(self.translate_path())
        else:
            self.send_error(501, "File type not supported: %s" % self.path)

    def handle_polling(self, path, old_mtime):
        # TODO: use inotify if available
        while True:
            try:
                mtime = int(os.stat(path).st_mtime)
            except OSError:
                # Sometimes when you save a file in a text editor it stops
                # existing for a brief moment.
                # See https://github.com/mgedmin/restview/issues/11
                time.sleep(0.1)
                continue
            # we lose precision by using int(), but I'm nervous of
            # round-tripping floating point numbers through HTML and
            # comparing them for equality
            if mtime != old_mtime:
                try:
                    self.send_response(200)
                    self.send_header("Cache-Control", "no-cache, no-store, max-age=0")
                    self.end_headers()
                except Exception as e:
                    self.log_error('%s (client closed "%s" before acknowledgement)', e, self.path)
                finally:
                    return
            time.sleep(0.2)

    def translate_path(self, path=None):
        root = self.server.renderer.root
        if path is None:
            path = self.path
        path = path.lstrip('/')
        if not isinstance(root, str):
            idx, path = path.split('/', 1)
            root = root[int(idx)]
        if not os.path.isdir(root):
            root = os.path.dirname(root)
        return os.path.join(root, path)

    def handle_image(self, filename, ctype):
        try:
            with open(filename, 'rb') as f:
                data = f.read()
        except IOError:
            self.send_error(404, "File not found: %s" % self.path)
        else:
            self.send_response(200)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            return data

    def handle_rest_file(self, filename):
        try:
            with open(filename) as f:
                mtime = os.fstat(f.fileno()).st_mtime
                return self.handle_rest_data(f.read(), mtime=mtime)
        except IOError as e:
            self.log_error("%s", e)
            self.send_error(404, "File not found: %s" % self.path)

    def handle_command(self, command):
        try:
            p = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE)
            stdout, stderr = p.communicate()
            if p.returncode != 0:
                self.log_error("'%s' terminated with %s", command, p.returncode)
            if stderr or not stdout:
                return self.handle_error(command, p.returncode, stderr)
            else:
                return self.handle_rest_data(stdout)
        except OSError as e:
            self.log_error("%s", e)
            self.send_error(500, "Command execution failed")

    def handle_rest_data(self, data, mtime=None):
        html = self.server.renderer.rest_to_html(data, mtime=mtime)
        if isinstance(html, unicode):
            html = html.encode('UTF-8')
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=UTF-8")
        self.send_header("Content-Length", str(len(html)))
        self.send_header("Cache-Control", "no-cache, no-store, max-age=0")
        self.end_headers()
        return html

    def handle_error(self, command, retcode, stderr):
        html = self.server.renderer.render_exception(
            title=command,
            error='Returned error code %s' % retcode,
            source=stderr or '(no output)')
        if isinstance(html, unicode):
            html = html.encode('UTF-8')
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=UTF-8")
        self.send_header("Content-Length", str(len(html)))
        self.send_header("Cache-Control", "no-cache, no-store, max-age=0")
        self.end_headers()
        return html

    def collect_files(self, dirname):
        if not dirname.endswith(os.path.sep):
            dirname += os.path.sep
        files = []
        for dirpath, dirnames, filenames in os.walk(dirname):
            dirnames[:] = [dn for dn in dirnames
                           if not dn.startswith('.')
                           and not dn.endswith('.egg-info')]
            for fn in filenames:
                if fn.endswith('.txt') or fn.endswith('.rst'):
                    prefix = dirpath[len(dirname):]
                    files.append(os.path.join(prefix, fn))
        files.sort(key=str.lower)
        return files

    def handle_dir(self, dirname):
        files = [(fn.replace(os.path.sep, '/'), fn) for fn in self.collect_files(dirname)]
        html = self.render_dir_listing("RST files in %s" % os.path.abspath(dirname), files)
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
                files.extend([('%s/%s' % (idx, f.replace(os.path.sep, '/')),
                               os.path.join(fn, f))
                              for f in self.collect_files(fn)])
            else:
                files.append(('%s/%s' % (idx, os.path.basename(fn)),
                              fn))
        html = self.render_dir_listing("RST files", files)
        if isinstance(html, unicode):
            html = html.encode('UTF-8')
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=UTF-8")
        self.send_header("Content-Length", str(len(html)))
        self.end_headers()
        return html

    def render_dir_listing(self, title, files):
        files = ''.join([FILE_TEMPLATE.replace('$href', escape(href))
                                      .replace('$file', escape(fn))
                         for href, fn in files])
        return (DIR_TEMPLATE.replace('$title', escape(title))
                            .replace('$files', files))


DIR_TEMPLATE = """\
<!DOCTYPE html>
<html>
<head>
<title>$title</title>
</head>
<body>
<h1>$title</h1>
<ul>
$files</ul>
</body>
</html>
"""

FILE_TEMPLATE = """\
  <li><a href="$href">$file</a></li>
"""

AJAX_STR = """
<script type="text/javascript">
var xmlHttp = null;
window.onload = function () {
    setTimeout(function () {
        if (window.XMLHttpRequest) {
            xmlHttp = new XMLHttpRequest();
        } else if (window.ActiveXObject) {
            xmlHttp = new ActiveXObject('Microsoft.XMLHTTP');
        }
        xmlHttp.onreadystatechange = function () {
            if (xmlHttp.readyState == 4 && xmlHttp.status == '200') {
                window.location.reload(true);
            }
        }
        xmlHttp.open('HEAD', '/polling?pathname=' + location.pathname + '&mtime=%d', true);
        xmlHttp.send(null);
    }, 0);
}
window.onbeforeunload = function () {
    xmlHttp.abort();
}
</script>
"""

ERROR_TEMPLATE = """\
<!DOCTYPE html>
<html>
<head>
<title>$title</title>
<style type="text/css">
pre.error {
    border-left: 3px double red;
    margin-left: 19px;
    padding-left: 19px;
    padding-top: 10px;
    padding-bottom: 10px;
    color: red;
}
</style>
</head>
<body>
<h1>$title</h1>
<pre class="error">
$error
</pre>
<pre>
$source
</pre>
</body>
</html>
"""


class ThreadingHTTPServer(SocketServer.ThreadingMixIn, BaseHTTPServer.HTTPServer):
    daemon_threads = True


class RestViewer(object):
    """Web server that renders ReStructuredText on the fly."""

    server_class = ThreadingHTTPServer
    handler_class = MyRequestHandler

    local_address = ('localhost', 0)

    # only set one of these two:
    css_url = None
    css_path = os.path.join(os.path.dirname(os.path.realpath(__file__)),
                            'default.css')

    favicon_path = os.path.join(os.path.dirname(os.path.realpath(__file__)),
                                'favicon.ico')

    strict = False

    def __init__(self, root, command=None):
        self.root = root
        self.command = command

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

    def close(self):
        self.server.server_close()

    def rest_to_html(self, rest_input, settings=None, mtime=None):
        """Render ReStructuredText."""
        writer = docutils.writers.html4css1.Writer()
        if pygments is not None:
            writer.translator_class = SyntaxHighlightingHTMLTranslator
        if self.css_url:
            settings_overrides = {'stylesheet': self.css_url,
                                  'stylesheet_path': None,
                                  'embed_stylesheet': False}
        elif self.css_path:
            settings_overrides = {'stylesheet': self.css_path,
                                  'stylesheet_path': None,
                                  'embed_stylesheet': True}
        else:
            settings_overrides = {}
        settings_overrides['syntax_highlight'] = 'short'
        if self.strict:
            settings_overrides['halt_level'] = 1

        if settings:
            settings_overrides.update(settings)

        try:
            docutils.core.publish_string(rest_input, writer=writer,
                                         settings_overrides=settings_overrides)
        except Exception as e:
            html = self.render_exception(e.__class__.__name__, str(e), rest_input)
        else:
            html = writer.output
        return self.inject_ajax(html, mtime=mtime)

    def render_exception(self, title, error, source):
        return (ERROR_TEMPLATE.replace('$title', escape(title))
                              .replace('$error', escape(error))
                              .replace('$source', escape(source)))

    def inject_ajax(self, markup, mtime=None):
        if mtime is not None:
            return markup.replace('</body>', (AJAX_STR % mtime) + '</body>')
        else:
            return markup


class SyntaxHighlightingHTMLTranslator(docutils.writers.html4css1.HTMLTranslator):

    in_doctest = False
    in_text = False
    in_reference = False
    formatter_styles = formatters.HtmlFormatter(style='colorful').get_style_defs('pre')

    def __init__(self, document):
        docutils.writers.html4css1.HTMLTranslator.__init__(self, document)
        self.body_prefix[:0] = ['<style type="text/css">\n', self.formatter_styles, '\n</style>\n']

    def visit_doctest_block(self, node):
        docutils.writers.html4css1.HTMLTranslator.visit_doctest_block(self, node)
        self.in_doctest = True

    def depart_doctest_block(self, node):
        docutils.writers.html4css1.HTMLTranslator.depart_doctest_block(self, node)
        self.in_doctest = False

    def visit_Text(self, node):
        if self.in_doctest:
            text = node.astext()
            lexer = lexers.PythonConsoleLexer()
            formatter = formatters.HtmlFormatter(nowrap=True)
            self.body.append(pygments.highlight(text, lexer, formatter))
        else:
            text = node.astext()
            self.in_text = True
            encoded = self.encode(text)
            self.in_text = False
            if self.in_mailto and self.settings.cloak_email_addresses:
                encoded = self.cloak_email(encoded)
            self.body.append(encoded)

    def visit_literal(self, node):
        self.in_text = True
        try:
            docutils.writers.html4css1.HTMLTranslator.visit_literal(self, node)
        finally:
            self.in_text = False

    def visit_reference(self, node):
        self.in_reference = True
        docutils.writers.html4css1.HTMLTranslator.visit_reference(self, node)

    def depart_reference(self, node):
        docutils.writers.html4css1.HTMLTranslator.depart_reference(self, node)
        self.in_reference = False

    def encode(self, text):
        encoded = docutils.writers.html4css1.HTMLTranslator.encode(self, text)
        if self.in_text and not self.in_reference:
            encoded = self.link_local_files(encoded)
        return encoded

    @staticmethod
    def link_local_files(text):
        """Replace filenames with hyperlinks.

            >>> link_local_files = SyntaxHighlightingHTMLTranslator.link_local_files
            >>> link_local_files('e.g. see README.txt for more info')
            'e.g. see <a href="README.txt">README.txt</a> for more info'
            >>> link_local_files('e.g. see docs/HACKING.rst for more info')
            'e.g. see <a href="docs/HACKING.rst">docs/HACKING.rst</a> for more info'
            >>> link_local_files('what about http://example.com/README.txt ?')
            'what about http://example.com/README.txt ?'

        """
        # jwz was right...
        return re.sub(r"(^|\s)([-_a-zA-Z0-9/]+[.](txt|rst))",
                      r'\1<a href="\2">\2</a>', text)


def parse_address(addr):
    """Parse a socket address.

        >>> parse_address('1234')
        ('localhost', 1234)

        >>> parse_address('example.com:1234')
        ('example.com', 1234)

        >>> parse_address('*:1234')
        ('', 1234)

        >>> try: parse_address('notanumber')
        ... except ValueError as e: print(e)
        Invalid address: notanumber

        >>> try: parse_address('la:la:la')
        ... except ValueError as e: print(e)
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
    if listen_on == '' or ip_addr == b'\0\0\0\0':
        return socket.gethostname()
    else:
        return listen_on


def launch_browser(url):
    """Launch the web browser for a given URL.

    Does not block.
    """
    # Do it in the background as it may block
    t = threading.Thread(target=webbrowser.open, args=(url,))
    t.setDaemon(True)
    t.start()


def main():
    progname = os.path.basename(sys.argv[0])
    parser = optparse.OptionParser("%prog [options] filename-or-directory [...]",
                    description="Serve ReStructuredText files over HTTP.",
                    prog=progname)
    parser.add_option('-l', '--listen', metavar='PORT',
                      help='listen on a given port (or interface:port,'
                           ' e.g. *:8080) [default: random port on localhost]',
                      default=None)
    parser.add_option('-b', '--browser',
                      help='open a web browser [default: only if -l'
                           ' was not specified]',
                      action='store_true', default=None)
    parser.add_option('-e', '--execute', metavar='COMMAND',
                      help='run a command to produce ReStructuredText',
                      default=None)
    parser.add_option('--long-description',
                      help='run "python setup.py --long-description" to produce ReStructuredText',
                      action='store_const', dest='execute',
                      const='python setup.py --long-description')
    parser.add_option('--css', metavar='URL-or-FILENAME',
                      help='use the specified stylesheet',
                      action='store', dest='css_path', default=None)
    parser.add_option('--strict',
                      help='halt at the slightest problem',
                      action='store_true', default=False)
    opts, args = parser.parse_args(sys.argv[1:])
    if not args and not opts.execute:
        parser.error("at least one argument expected")
    if args and opts.execute:
        parser.error("specify a command (-e) or a file/directory, but not both")
    if opts.browser is None:
        opts.browser = opts.listen is None
    if opts.execute:
        server = RestViewer('.', command=opts.execute)
    elif len(args) == 1:
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

    server.strict = opts.strict

    if opts.listen:
        try:
            server.local_address = parse_address(opts.listen)
        except ValueError as e:
            parser.error(str(e))
    host = get_host_name(server.local_address[0])
    port = server.listen()
    try:
        url = 'http://%s:%d/' % (host, port)
        print("Listening on %s" % url)
        if opts.browser:
            launch_browser(url)
        server.serve()
    except KeyboardInterrupt:
        pass
    finally:
        server.close()


if __name__ == '__main__':
    main()

