"""
HTTP-based ReStructuredText viewer.
"""
import argparse
import fnmatch
import http.server
import os
import re
import socket
import socketserver
import subprocess
import sys
import threading
import time
import webbrowser
from html import escape
from urllib.parse import parse_qs, unquote

import docutils.core
import docutils.writers.html4css1
import pygments
import readme_renderer.rst as readme_rst
from pygments import formatters, lexers


__version__ = '3.0.2'


# If restview is ever packaged for Debian, this'll likely be changed to
# point to /usr/share/restview
DATA_PATH = os.path.dirname(os.path.realpath(__file__))


class MyRequestHandler(http.server.BaseHTTPRequestHandler):
    """HTTP request handler that renders ReStructuredText on the fly."""

    server_version = "restviewhttp/" + __version__

    def do_GET(self):
        content = self.do_GET_or_HEAD()
        if content:
            self.wfile.write(content)

    def do_HEAD(self):
        self.do_GET_or_HEAD()

    def do_GET_or_HEAD(self):
        host = self.headers.get('Host', '').split(':', 1)[0]
        if not any(fnmatch.fnmatch(host, pat)
                   for pat in self.server.renderer.allowed_hosts):
            # Protect against DNS rebinding attacks
            # (https://en.wikipedia.org/wiki/DNS_rebinding)
            self.log_error("Rejecting unknown Host header: %r", host)
            self.send_error(400, "Host header not in allowed list")
            return
        self.path = unquote(self.path)
        if '..' in self.path:
            self.send_error(400, "Bad request") # no hacking!
            return
        root = self.server.renderer.root
        command = self.server.renderer.command
        watch = self.server.renderer.watch
        if self.path == '/':
            if command:
                return self.handle_command(command, watch)
            elif isinstance(root, str):
                if os.path.isdir(root):
                    return self.handle_dir(root)
                else:
                    return self.handle_rest_file(root, watch)
            else:
                return self.handle_list(root)
        elif self.path.startswith('/polling?'):
            query = parse_qs(self.path.partition('?')[-1])
            pathname = query['pathname'][0]
            if pathname == '/' and command:
                pathnames = []
            elif pathname == '/' and isinstance(root, str):
                pathnames = [root]
            else:
                pathnames = [self.translate_path(pathname)]
            if watch:
                pathnames += watch
            old_mtime = query['mtime'][0]
            return self.handle_polling(pathnames, old_mtime)
        elif self.path == '/favicon.ico':
            return self.handle_image(self.server.renderer.favicon_path,
                                     'image/x-icon')
        elif self.path.endswith('.gif'):
            return self.handle_image(self.translate_path(), 'image/gif')
        elif self.path.endswith('.png'):
            return self.handle_image(self.translate_path(), 'image/png')
        elif self.path.endswith('.jpg') or self.path.endswith('.jpeg'):
            return self.handle_image(self.translate_path(), 'image/jpeg')
        elif self.path.endswith('.svg'):
            return self.handle_image(self.translate_path(), 'image/svg+xml')
        elif self.path.endswith('.txt') or self.path.endswith('.rst'):
            return self.handle_rest_file(self.translate_path(), watch)
        else:
            self.send_error(501, "File type not supported: %s" % self.path)

    def get_latest_mtime(self, filenames, latest_mtime=None):
        for path in filenames:
            try:
                mtime = os.stat(path).st_mtime
            except OSError:
                pass
            else:
                if latest_mtime is None or mtime > latest_mtime:
                    latest_mtime = mtime
        return latest_mtime

    def handle_polling(self, paths, old_mtime):
        # TODO: use inotify if available
        while True:
            mtime = self.get_latest_mtime(paths)
            if mtime is None:
                # Sometimes when you save a file in a text editor it stops
                # existing for a brief moment.
                # See https://github.com/mgedmin/restview/issues/11
                time.sleep(0.1)
                continue
            # Compare as strings: the JS treats our value as a cookie
            if str(mtime) != str(old_mtime):
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

    def handle_rest_file(self, filename, watch=None):
        try:
            with open(filename, 'rb') as f:
                mtime = os.fstat(f.fileno()).st_mtime
                if watch:
                    mtime = self.get_latest_mtime(watch, mtime)
                return self.handle_rest_data(f.read(), mtime=mtime, filename=filename)
        except IOError as e:
            self.log_error("%s", e)
            self.send_error(404, "File not found: %s" % self.path)

    def handle_command(self, command, watch=None):
        try:
            mtime = self.get_latest_mtime(watch) if watch else None
            p = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE)
            stdout, stderr = p.communicate()
            if p.returncode != 0:
                self.log_error("'%s' terminated with %s", command, p.returncode)
            if stderr:
                self.log_error("stderr from '%s':\n%s", command, stderr)
            if not stdout:
                return self.handle_error(command, p.returncode, stderr, mtime=mtime)
            else:
                return self.handle_rest_data(stdout, mtime=mtime)
        except OSError as e:
            self.log_error("%s", e)
            self.send_error(500, "Command execution failed")

    def handle_rest_data(self, data, mtime=None, filename=None):
        html = self.server.renderer.rest_to_html(data, mtime=mtime,
                                                 filename=filename)
        if isinstance(html, str):
            html = html.encode('UTF-8')
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=UTF-8")
        self.send_header("Content-Length", str(len(html)))
        self.send_header("Cache-Control", "no-cache, no-store, max-age=0")
        if mtime is not None:
            self.send_header("X-Restview-Mtime", str(mtime))
        self.end_headers()
        return html

    def handle_error(self, command, retcode, stderr, mtime=None):
        html = self.server.renderer.render_exception(
            title=command,
            error='Process returned error code %s.' % retcode,
            source=stderr or '(no output)',
            mtime=mtime)
        if isinstance(html, str):
            html = html.encode('UTF-8')
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=UTF-8")
        self.send_header("Content-Length", str(len(html)))
        self.send_header("Cache-Control", "no-cache, no-store, max-age=0")
        if mtime is not None:
            self.send_header("X-Restview-Mtime", str(mtime))
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
        if isinstance(html, str):
            html = html.encode('UTF-8', 'replace')
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
        if isinstance(html, str):
            html = html.encode('UTF-8', 'replace')
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
var mtime = '%s';
var poll = null;
window.onload = function () {
    setTimeout(function () {
        poll = new XMLHttpRequest();
        poll.onreadystatechange = function () {
            if (this.readyState == 4 && this.status == 200) {
                var reload = new XMLHttpRequest();
                reload.onreadystatechange = function () {
                    if (this.readyState == 4 && this.status == 200) {
                        document.title = this.responseXML.title;
                        document.body.innerHTML = this.responseXML.body.innerHTML;
                        var old_styles = document.getElementsByTagName('style');
                        var new_styles = this.responseXML.getElementsByTagName('style');
                        for (var i = old_styles.length - 1; i >= 0; i--) {
                            old_styles[i].remove();
                        }
                        // convert HTMLCollection to an array so that
                        // items don't disappear from under us when I append
                        // them to a different DOM tree
                        new_styles = [].slice.call(new_styles);
                        for (var i = 0; i < new_styles.length; i++) {
                            document.head.appendChild(new_styles[i]);
                        }
                        mtime = this.getResponseHeader('X-Restview-Mtime');
                        if (mtime) {
                            poll.open('HEAD', '/polling?pathname=' + location.pathname + '&mtime=' + mtime, true);
                            poll.send();
                        }
                    }
                }
                reload.open('GET', location.pathname, true);
                reload.responseType = 'document';
                reload.send();
            }
        }
        poll.open('HEAD', '/polling?pathname=' + location.pathname + '&mtime=' + mtime, true);
        poll.send(null);
    }, 0);
}
window.onbeforeunload = function () {
    poll.abort();
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
    border-left: 1ex solid red;
    padding-left: 1.5em;
    padding-top: 1em;
    padding-bottom: 1em;
    color: red;
    background: #fff8f8;
}
pre > .highlight {
    display: block;
    color: red;
    background: #fff8f8;
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


class ThreadingHTTPServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True


class RestViewer(object):
    """Web server that renders ReStructuredText on the fly."""

    server_class = ThreadingHTTPServer
    handler_class = MyRequestHandler

    local_address = ('localhost', 0)
    allowed_hosts = ['localhost', '127.0.0.1']

    # Comma-separated list of URLs, full filenames, or filenames in the
    # default search path (if you want to refer to docutils default
    # stylesheets html4css1.css or math.css, or restview's default
    # stylesheets restview.css and oldrestview.css).
    stylesheets = 'html4css1.css,restview.css'

    favicon_path = os.path.join(DATA_PATH, 'favicon.ico')

    report_level = None
    halt_level = None
    pypi_strict = False

    def __init__(self, root, command=None, watch=None):
        self.root = root
        self.command = command
        self.watch = watch

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

    def rest_to_html(self, rest_input, settings=None, mtime=None, filename=None):
        """Render ReStructuredText."""
        writer = docutils.writers.html4css1.Writer()
        if pygments is not None:
            writer.translator_class = SyntaxHighlightingHTMLTranslator
        if self.stylesheets:
            stylesheet_dirs = writer.default_stylesheet_dirs + [DATA_PATH]
            if '//' not in self.stylesheets:
                settings_overrides = {'stylesheet': None,
                                      'stylesheet_path': self.stylesheets,
                                      'stylesheet_dirs': stylesheet_dirs,
                                      'embed_stylesheet': True}
            else:
                # docutils can't embed http:// or https:// URLs
                settings_overrides = {'stylesheet': self.stylesheets,
                                      'stylesheet_path': None,
                                      'stylesheet_dirs': stylesheet_dirs,
                                      'embed_stylesheet': False}
        else:
            settings_overrides = {}
        settings_overrides['syntax_highlight'] = 'short'
        if self.pypi_strict:
            settings_overrides.update(readme_rst.SETTINGS)
        if self.halt_level is not None:
            settings_overrides['halt_level'] = self.halt_level
        if self.report_level is not None:
            settings_overrides['report_level'] = self.report_level

        if settings:  # hook for unit tests
            settings_overrides.update(settings)

        try:
            docutils.core.publish_string(rest_input, writer=writer,
                                         source_path=filename,
                                         settings_overrides=settings_overrides)
            if self.pypi_strict:
                clean_body = readme_rst.clean(''.join(writer.body))
                if clean_body is None:
                    # Unfortunately the real error was caught and discared,
                    # without even logging :/
                    raise ValueError("Output cleaning failed")
                writer.body = [clean_body]
                writer.output = writer.apply_template()
        except Exception as e:
            line = self.extract_line_info(e, filename)
            html = self.render_exception(e.__class__.__name__, str(e), rest_input, mtime=mtime, line=line)
        else:
            html = writer.output
        return self.inject_ajax(html, mtime=mtime)

    @staticmethod
    def extract_line_info(exception, source_path):
        # Docutils constructs a nice system_message object that has
        # attributes like 'source' and 'line', but then it flattens
        # that out into a string passed to the exception constructor.
        msg = str(exception)
        source_path = str(source_path)  # handle None like docutils
        if msg.startswith(source_path + ':'):
            lineno = msg[len(source_path) + 1:].partition(':')[0]
            if lineno.isdigit():
                return int(lineno)
        return None

    @staticmethod
    def highlight_line(source, lineno):
        source = escape(source)
        if not lineno:
            return source
        lines = source.splitlines(True)
        if not 1 <= lineno <= len(lines):
            return source
        idx = lineno - 1
        return ''.join(
            lines[:idx]
            + ['<span class="highlight">%s</span>' % lines[idx]]
            + lines[idx + 1:]
        )

    def render_exception(self, title, error, source, line=None, mtime=None):
        # NB: source is a bytestring (see issue #16 for the reason)
        # UTF-8 is not necessarily the right thing to use here, but
        # garbage is better than a crash, right?
        source = source.decode('UTF-8', 'replace')
        html = (ERROR_TEMPLATE.replace('$title', escape(title))
                              .replace('$error', escape(error))
                              .replace('$source', self.highlight_line(source, line)))
        return self.inject_ajax(html, mtime=mtime)

    def inject_ajax(self, markup, mtime=None):
        if mtime is not None:
            return markup.replace('</body>', (AJAX_STR % mtime) + '</body>')
        else:
            return markup


class SyntaxHighlightingHTMLTranslator(readme_rst.ReadMeHTMLTranslator):
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
    parser = argparse.ArgumentParser(
                    usage="%(prog)s [options] root [...]",
                    description="Serve ReStructuredText files over HTTP.",
                    prog="restview")
    parser.add_argument('root',
                        help='filename or directory to serve documents from',
                        nargs='*')
    parser.add_argument('--version', action='version', version=__version__)
    parser.add_argument('-l', '--listen', metavar='PORT',
                        help='listen on a given port (or interface:port,'
                             ' e.g. *:8080) [default: random port on localhost]',
                        default=None)
    parser.add_argument('--allowed-hosts', metavar='HOSTS',
                        help='allowed values for the Host header (default:'
                             ' localhost only, unless you specify -l *:port,'
                             ' in which case any Host: is accepted by default)',
                        default=None)
    parser.add_argument('-b', '--browser',
                        help='open a web browser [default: only if -l'
                             ' was not specified]',
                        action='store_true', default=None)
    parser.add_argument('-B', '--no-browser',
                        help="don't open a web browser",
                        action='store_false', dest='browser')
    parser.add_argument('-e', '--execute', metavar='COMMAND',
                        help='run a command to produce ReStructuredText',
                        default=None)
    parser.add_argument('-w', '--watch', metavar='FILENAME', action='append',
                        help='reload the page when a file changes (use with'
                             ' --execute); can be specified multiple times',
                        default=[])
    parser.add_argument('--long-description',
                        help='run "python setup.py --long-description" to produce'
                             ' ReStructuredText; also enables --pypi-strict'
                             ' and watches the usual long description sources'
                             ' (setup.py, README.rst, CHANGES.rst)',
                        action='store_true')
    parser.add_argument('--css', metavar='URL|FILENAME',
                        help='use the specified stylesheet; can be specified'
                             ' multiple times [default: %s]'
                             % RestViewer.stylesheets,
                        action='append', dest='stylesheets', default=[])
    parser.add_argument(
        '--report-level',
        help='''set the "report_level" option of docutils; restview
            will report system messages at or above this level (1=info,
            2=warnings, 3=errors, 4=severe)''',
        type=int, default=2)
    halt_level_group = parser.add_mutually_exclusive_group()
    halt_level_group.add_argument(
        '--halt-level',
        help='''set the "halt_level" option of docutils; restview
            will stop processing the document when a system message
            at or above this level (1=info, 2=warnings, 3=errors,
            4=severe) is logged''',
        type=int, default=None)
    halt_level_group.add_argument(
        '--strict',
        help='halt at the slightest problem; equivalent to --halt-level=2',
        action='store_const', dest='halt_level', const=2)
    parser.add_argument(
        '--pypi-strict',
        help='enable additional restrictions that PyPI performs',
        action='store_true', default=False)
    opts = parser.parse_args(sys.argv[1:])
    args = opts.root
    if opts.long_description:
        opts.execute = 'python setup.py --long-description'
        opts.watch += ['setup.py', 'README.rst', 'CHANGES.rst']
        opts.pypi_strict = True
    if not args and not opts.execute:
        parser.error("at least one argument expected")
    if args and opts.execute:
        parser.error("specify a command (-e) or a file/directory, but not both")
    if opts.browser is None:
        opts.browser = opts.listen is None
    if opts.execute:
        server = RestViewer('.', command=opts.execute, watch=opts.watch)
    elif len(args) == 1:
        server = RestViewer(args[0], watch=opts.watch)
    else:
        server = RestViewer(args, watch=opts.watch)
    if opts.stylesheets:
        server.stylesheets = ','.join(opts.stylesheets)
    server.report_level = opts.report_level
    server.halt_level = opts.halt_level
    server.pypi_strict = opts.pypi_strict

    if opts.listen:
        try:
            server.local_address = parse_address(opts.listen)
        except ValueError as e:
            parser.error(str(e))
    if opts.allowed_hosts:
        server.allowed_hosts = opts.allowed_hosts.replace(',', ' ').split()
    elif server.local_address[0] in ('*', '0', '0.0.0.0'):
        server.allowed_hosts = ['*']
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
