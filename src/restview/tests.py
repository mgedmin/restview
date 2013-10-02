import doctest
import errno
import os
import socket
import unittest
import webbrowser

try:
    from cStringIO import StringIO
except ImportError:
    from io import StringIO

from mock import Mock, patch

from restview.restviewhttp import (MyRequestHandler, RestViewer,
                                   get_host_name, launch_browser, main)

try:
    unicode
except NameError:
    unicode = str


class MyRequestHandlerForTests(MyRequestHandler):
    def __init__(self):
        self._headers = {}
        self.log = []
        self.server = Mock()
        self.server.renderer.rest_to_html = lambda data, mtime=None: \
            unicode('HTML for %s with AJAX poller for %s' % (data, mtime))
    def send_response(self, status):
        self.status = status
    def send_header(self, header, value):
        self._headers[header] = value
    def end_headers(self):
        self.headers = self._headers
    def send_error(self, status, body):
        self.status = status
        self.error_body = body
    def log_error(self, message, *args):
        if args:
            message = message % args
        self.log.append(message)


class TestMyRequestHandler(unittest.TestCase):

    def _os_walk(self, dirpath):
        dirnames = ['.svn', '.tox', 'subdir', 'mypackage.egg-info']
        filenames = ['a.txt', 'z.rst', 'unrelated.py']
        yield dirpath, dirnames, filenames
        for subdir in dirnames:
            yield os.path.join(dirpath, subdir), [], ['b.txt', 'c.py']

    def _raise_oserror(self, *args):
        raise OSError(errno.ENOENT, "no such file or directory")

    def _raise_socket_error(self, *args):
        raise socket.error("connection reset by peer")

    def test_do_GET(self):
        handler = MyRequestHandlerForTests()
        handler.path = '/a.txt'
        handler.server.renderer.root = '/root/file.txt'
        handler.handle_rest_file = lambda fn: 'HTML for %s' % fn
        handler.wfile = StringIO()
        handler.do_GET()
        self.assertEqual(handler.wfile.getvalue(),
                         'HTML for /root/a.txt')

    def test_do_HEAD(self):
        handler = MyRequestHandlerForTests()
        handler.path = '/a.txt'
        handler.server.renderer.root = '/root/file.txt'
        handler.handle_rest_file = lambda fn: 'HTML for %s' % fn
        handler.wfile = StringIO()
        handler.do_HEAD()
        self.assertEqual(handler.wfile.getvalue(), '')

    def test_do_GET_or_HEAD_root_when_file(self):
        handler = MyRequestHandlerForTests()
        handler.path = '/'
        handler.server.renderer.root = '/root/file.txt'
        handler.server.renderer.command = None
        handler.handle_rest_file = lambda fn: 'HTML for %s' % fn
        with patch('os.path.isdir', lambda dir: False):
            body = handler.do_GET_or_HEAD()
        self.assertEqual(body, 'HTML for /root/file.txt')

    def test_do_GET_or_HEAD_root_when_dir(self):
        handler = MyRequestHandlerForTests()
        handler.path = '/'
        handler.server.renderer.root = '/root/'
        handler.server.renderer.command = None
        handler.handle_dir = lambda fn: 'Files in %s' % fn
        with patch('os.path.isdir', lambda dir: True):
            body = handler.do_GET_or_HEAD()
        self.assertEqual(body, 'Files in /root/')

    def test_do_GET_or_HEAD_root_when_list(self):
        handler = MyRequestHandlerForTests()
        handler.path = '/'
        handler.server.renderer.root = ['/root/', '/root2/']
        handler.server.renderer.command = None
        handler.handle_list = lambda roots: 'Files in %s' % ", ".join(roots)
        body = handler.do_GET_or_HEAD()
        self.assertEqual(body, 'Files in /root/, /root2/')

    def test_do_GET_or_HEAD_root_when_command(self):
        handler = MyRequestHandlerForTests()
        handler.path = '/'
        handler.server.renderer.root = None
        handler.server.renderer.command = 'cat README.rst'
        handler.handle_command = lambda cmd: 'Output of %s' % cmd
        body = handler.do_GET_or_HEAD()
        self.assertEqual(body, 'Output of cat README.rst')

    def test_do_GET_or_HEAD_polling(self):
        handler = MyRequestHandlerForTests()
        handler.path = '/polling?pathname=a.txt&mtime=12345'
        handler.server.renderer.root = '/root/'
        handler.handle_polling = lambda fn, mt: 'Got update for %s since %s' % (fn, mt)
        body = handler.do_GET_or_HEAD()
        self.assertEqual(body, 'Got update for /root/a.txt since 12345')

    def test_do_GET_or_HEAD_polling_of_root(self):
        handler = MyRequestHandlerForTests()
        handler.path = '/polling?pathname=/&mtime=12345'
        handler.server.renderer.root = '/root/a.txt'
        handler.handle_polling = lambda fn, mt: 'Got update for %s since %s' % (fn, mt)
        body = handler.do_GET_or_HEAD()
        self.assertEqual(body, 'Got update for /root/a.txt since 12345')

    def test_do_GET_or_HEAD_prevent_sandbox_climbing_attacks(self):
        handler = MyRequestHandlerForTests()
        handler.path = '/polling?pathname=../../../etc/passwd&mtime=12345'
        handler.server.renderer.root = '/root/a.txt'
        handler.do_GET_or_HEAD()
        self.assertEqual(handler.status, 400)
        self.assertEqual(handler.error_body, "Bad request")

    def test_do_GET_or_HEAD_images(self):
        for filename, ctype in [('a.png', 'image/png'),
                                ('a.gif', 'image/gif'),
                                ('a.jpg', 'image/jpeg'),
                                ('a.jpeg', 'image/jpeg'),
                                ('favicon.ico', 'image/x-icon')]:
            handler = MyRequestHandlerForTests()
            handler.path = '/' + filename
            handler.server.renderer.root = '/root/a.txt'
            handler.server.renderer.favicon_path = '/root/favicon.ico'
            handler.handle_image = lambda fn, ct: '%s (%s)' % (fn, ct)
            body = handler.do_GET_or_HEAD()
            self.assertEqual(body, '/root/%s (%s)' % (filename, ctype))

    def test_do_GET_or_HEAD_rst_files(self):
        for filename in ['a.txt', 'a.rst']:
            handler = MyRequestHandlerForTests()
            handler.path = '/' + filename
            handler.server.renderer.root = '/root/file.txt'
            handler.handle_rest_file = lambda fn: 'HTML for %s' % fn
            body = handler.do_GET_or_HEAD()
            self.assertEqual(body, 'HTML for /root/%s' % filename)

    def test_do_GET_or_HEAD_other_files(self):
        handler = MyRequestHandlerForTests()
        handler.path = '/a.py'
        handler.server.renderer.root = '/root/file.txt'
        handler.do_GET_or_HEAD()
        self.assertEqual(handler.status, 501)
        self.assertEqual(handler.error_body, "File type not supported: /a.py")

    def test_handle_polling(self):
        handler = MyRequestHandlerForTests()
        filename = os.path.join(os.path.dirname(__file__), '__init__.py')
        with patch('time.sleep') as sleep:
            stat = {filename: [Mock(st_mtime=123455), Mock(st_mtime=123456)]}
            with patch('os.stat', lambda fn: stat[fn].pop(0)):
                handler.handle_polling(filename, 123455)
            sleep.assert_called_once_with(0.2)
        self.assertEqual(handler.status, 200)
        self.assertEqual(handler.headers['Cache-Control'],
                         "no-cache, no-store, max-age=0")

    def test_handle_polling_handles_interruptions(self):
        handler = MyRequestHandlerForTests()
        handler.path = '/polling?pathname=__init__.py&mtime=123455'
        handler.send_response = self._raise_socket_error
        filename = os.path.join(os.path.dirname(__file__), '__init__.py')
        stat = {filename: [Mock(st_mtime=123456)]}
        with patch('os.stat', lambda fn: stat[fn].pop(0)):
            handler.handle_polling(filename, 123455)
        self.assertEqual(handler.log,
             ['connection reset by peer (client closed "/polling?pathname=__init__.py&mtime=123455" before acknowledgement)'])

    def test_handle_polling_handles_disappearing_files(self):
        handler = MyRequestHandlerForTests()
        filename = os.path.join(os.path.dirname(__file__), '__init__.py')
        with patch('time.sleep'):
            stat = {filename: [lambda: Mock(st_mtime=123455),
                               self._raise_oserror,
                               lambda: Mock(st_mtime=123456)]}
            with patch('os.stat', lambda fn: stat[fn].pop(0)()):
                handler.handle_polling(filename, 123455)
        self.assertEqual(handler.status, 200)
        self.assertEqual(handler.headers['Cache-Control'],
                         "no-cache, no-store, max-age=0")

    def test_translate_path_when_root_is_a_file(self):
        handler = MyRequestHandlerForTests()
        handler.server.renderer.root = '/root/file.txt'
        handler.path = '/a.txt'
        with patch('os.path.isdir', lambda dir: False):
            self.assertEqual(handler.translate_path(), '/root/a.txt')
            self.assertEqual(handler.translate_path('/file.png'),
                             '/root/file.png')

    def test_translate_path_when_root_is_a_directory(self):
        handler = MyRequestHandlerForTests()
        handler.server.renderer.root = '/root'
        handler.path = '/a.txt'
        with patch('os.path.isdir', lambda dir: True):
            self.assertEqual(handler.translate_path(), '/root/a.txt')
            self.assertEqual(handler.translate_path('/file.txt'),
                             '/root/file.txt')

    def test_translate_path_when_root_is_a_sequence(self):
        handler = MyRequestHandlerForTests()
        handler.server.renderer.root = ['/root', '/root2/file.txt']
        handler.path = '/0/a.txt'
        with patch('os.path.isdir', lambda dir: '.' not in dir):
            self.assertEqual(handler.translate_path(), '/root/a.txt')
            self.assertEqual(handler.translate_path('/1/b.txt'),
                             '/root2/b.txt')

    def test_handle_image(self):
        handler = MyRequestHandlerForTests()
        filename = os.path.join(os.path.dirname(__file__), '__init__.py')
        body = handler.handle_image(filename, 'image/python') # ha ha
        self.assertEqual(handler.status, 200)
        self.assertEqual(handler.headers['Content-Type'],
                         "image/python")
        self.assertEqual(handler.headers['Content-Length'],
                         str(len(body)))
        self.assertTrue(isinstance(body, bytes))

    def test_handle_image_error(self):
        handler = MyRequestHandlerForTests()
        handler.path = '/nosuchfile.png'
        handler.handle_image('nosuchfile.png', 'image/png')
        self.assertEqual(handler.status, 404)
        self.assertEqual(handler.error_body,
                         "File not found: /nosuchfile.png")

    def test_handle_rest_file(self):
        handler = MyRequestHandlerForTests()
        filename = os.path.join(os.path.dirname(__file__), '__init__.py')
        mtime = os.stat(filename).st_mtime
        body = handler.handle_rest_file(filename)
        self.assertEqual(handler.status, 200)
        self.assertEqual(handler.headers['Content-Type'],
                         "text/html; charset=UTF-8")
        self.assertEqual(handler.headers['Content-Length'],
                         str(len(body)))
        self.assertEqual(handler.headers['Cache-Control'],
                         "no-cache, no-store, max-age=0")
        self.assertTrue(body.startswith(b'HTML for'))
        self.assertTrue(body.endswith(('with AJAX poller for %s' % mtime).encode()))

    def test_handle_rest_file_error(self):
        handler = MyRequestHandlerForTests()
        handler.path = '/nosuchfile.txt'
        handler.handle_rest_file('nosuchfile.txt')
        self.assertEqual(handler.status, 404)
        self.assertEqual(handler.error_body,
                         "File not found: /nosuchfile.txt")
        self.assertEqual(handler.log,
             ["[Errno 2] No such file or directory: 'nosuchfile.txt'"])

    def test_handle_command(self):
        handler = MyRequestHandlerForTests()
        with patch('os.popen', lambda cmd: StringIO('data from %s' % cmd)):
            body = handler.handle_command('cat README.rst')
        self.assertEqual(handler.status, 200)
        self.assertEqual(handler.headers['Content-Type'],
                         "text/html; charset=UTF-8")
        self.assertEqual(handler.headers['Content-Length'],
                         str(len(body)))
        self.assertEqual(handler.headers['Cache-Control'],
                         "no-cache, no-store, max-age=0")
        self.assertEqual(body,
                         b'HTML for data from cat README.rst'
                         b' with AJAX poller for None')

    def test_handle_command_error(self):
        handler = MyRequestHandlerForTests()
        with patch('os.popen', self._raise_oserror):
            handler.handle_command('cat README.rst')
        self.assertEqual(handler.status, 500)
        self.assertEqual(handler.error_body,
                         'Command execution failed')
        self.assertEqual(handler.log, ["[Errno 2] no such file or directory"])

    def test_handle_rest_data(self):
        handler = MyRequestHandlerForTests()
        body = handler.handle_rest_data("*Hello*", mtime=1364808683)
        self.assertEqual(handler.status, 200)
        self.assertEqual(handler.headers['Content-Type'],
                         "text/html; charset=UTF-8")
        self.assertEqual(handler.headers['Content-Length'],
                         str(len(body)))
        self.assertEqual(handler.headers['Cache-Control'],
                         "no-cache, no-store, max-age=0")
        self.assertEqual(body,
                         b'HTML for *Hello* with AJAX poller for 1364808683')

    def test_collect_files(self):
        handler = MyRequestHandlerForTests()
        with patch('os.walk', self._os_walk):
            files = handler.collect_files('/path/to/dir')
        self.assertEqual(files, ['a.txt', 'subdir/b.txt', 'z.rst'])

    def test_handle_dir(self):
        handler = MyRequestHandlerForTests()
        handler.collect_files = lambda dir: ['a.txt', 'b/c.txt']
        handler.render_dir_listing = lambda title, files: \
                unicode("<title>%s</title>\n%s" % (
                    title,
                    '\n'.join('%s - %s' % (path, fn) for path, fn in files)))
        body = handler.handle_dir('/path/to/dir')
        self.assertEqual(handler.status, 200)
        self.assertEqual(handler.headers['Content-Type'],
                         "text/html; charset=UTF-8")
        self.assertEqual(handler.headers['Content-Length'],
                         str(len(body)))
        self.assertEqual(body,
                         b"<title>RST files in /path/to/dir</title>\n"
                         b"a.txt - a.txt\n"
                         b"b/c.txt - b/c.txt")

    def test_handle_list(self):
        handler = MyRequestHandlerForTests()
        handler.collect_files = lambda dir: ['a.txt', 'b/c.txt']
        handler.render_dir_listing = lambda title, files: \
                unicode("<title>%s</title>\n%s" % (
                    title,
                    '\n'.join('%s - %s' % (path, fn) for path, fn in files)))
        with patch('os.path.isdir', lambda fn: fn == 'subdir'):
            body = handler.handle_list(['/path/to/file.txt', 'subdir'])
        self.assertEqual(handler.status, 200)
        self.assertEqual(handler.headers['Content-Type'],
                         "text/html; charset=UTF-8")
        self.assertEqual(handler.headers['Content-Length'],
                         str(len(body)))
        self.assertEqual(body,
                         b"<title>RST files</title>\n"
                         b"0/file.txt - /path/to/file.txt\n"
                         b"1/a.txt - subdir/a.txt\n"
                         b"1/b/c.txt - subdir/b/c.txt")


def doctest_MyRequestHandler_render_dir_listing():
    """Test for MyRequestHandler.render_dir_listing

        >>> handler = MyRequestHandlerForTests()
        >>> print(handler.render_dir_listing('Files in .', [
        ...     ('1/README.rst', 'README.rst'),
        ...     ('2/CHANGES.rst', 'CHANGES.rst'),
        ... ]))
        <!DOCTYPE html>
        <html>
        <head>
        <title>Files in .</title>
        </head>
        <body>
        <h1>Files in .</h1>
        <ul>
          <li><a href="1/README.rst">README.rst</a></li>
          <li><a href="2/CHANGES.rst">CHANGES.rst</a></li>
        </ul>
        </body>
        </html>
        <BLANKLINE>

    """


def doctest_RestViewer_rest_to_html():
    """Test for RestViewer.rest_to_html

        >>> viewer = RestViewer('.')
        >>> print(viewer.rest_to_html('''
        ... example
        ... -------
        ...
        ... This is a doctest:
        ...
        ...     >>> 2 + 2
        ...
        ... This is a local file reference: README.rst
        ...
        ... This is a reference: `README.rst <http://example.com/README.rst>`_
        ...
        ... This is an email: marius@gedmin.as
        ...
        ... This is a literal block::
        ...
        ...     See CHANGES.rst, mkay?
        ...
        ... This is an inline literal: ``README.txt``.
        ... ''', settings={'cloak_email_addresses': True}).strip())
        <?xml version="1.0" encoding="utf-8" ?>
        <!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
        <html xmlns="http://www.w3.org/1999/xhtml" xml:lang="en" lang="en">
        <head>
        <meta http-equiv="Content-Type" content="text/html; charset=utf-8" />
        ...
        <title>example</title>
        <style type="text/css">
        <BLANKLINE>
        /*
         * Stylesheet for ReStructuredText by Marius Gedminas.
         * (I didn't like the default one)
        ...
        </style>
        <style type="text/css">
        ...
        </style>
        </head>
        <body>
        <div class="document" id="example">
        <h1 class="title">example</h1>
        <BLANKLINE>
        <p>This is a doctest:</p>
        <blockquote>
        <pre class="doctest-block">
        <span class="gp">&gt;&gt;&gt; </span><span class="mi">2</span> <span class="o">+</span> <span class="mi">2</span>
        <BLANKLINE>
        </pre>
        </blockquote>
        <p>This is a local file reference: <a href="README.rst">README.rst</a></p>
        <p>This is a reference: <a class="reference external" href="http://example.com/README.rst">README.rst</a></p>
        <p>This is an email: <a class="reference external" href="mailto:marius&#37;&#52;&#48;gedmin&#46;as">marius<span>&#64;</span>gedmin<span>&#46;</span>as</a></p>
        <p>This is a literal block:</p>
        <pre class="literal-block">
        See <a href="CHANGES.rst">CHANGES.rst</a>, mkay?
        </pre>
        <p>This is an inline literal: <tt class="docutils literal"><a href="README.txt">README.txt</a></tt>.</p>
        </div>
        </body>
        </html>

    """


def doctest_RestViewer_rest_to_html_css_url():
    """Test for RestViewer.rest_to_html

    XXX: this shows pygments styles inlined *after* the external css, which
    means it's hard to override them!

        >>> viewer = RestViewer('.')
        >>> viewer.css_url = 'http://example.com/my.css'
        >>> print(viewer.rest_to_html('''
        ... Some text
        ... ''').strip())
        <?xml version="1.0" encoding="utf-8" ?>
        <!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
        <html xmlns="http://www.w3.org/1999/xhtml" xml:lang="en" lang="en">
        <head>
        <meta http-equiv="Content-Type" content="text/html; charset=utf-8" />
        ...
        <title></title>
        <link rel="stylesheet" href="http://example.com/my.css" type="text/css" />
        <style type="text/css">
        ...
        </style>
        </head>
        <body>
        <div class="document">
        <BLANKLINE>
        <BLANKLINE>
        <p>Some text</p>
        </div>
        </body>
        </html>

    """


def doctest_RestViewer_rest_to_html_strict_and_error_handling():
    """Test for RestViewer.rest_to_html

        >>> stderr_patcher = patch('sys.stderr', StringIO())
        >>> stderr = stderr_patcher.start()

        >>> viewer = RestViewer('.')
        >>> viewer.css_path = viewer.css_url = None
        >>> viewer.strict = True
        >>> print(viewer.rest_to_html('''
        ... Some text with an `error
        ... ''').strip())
        <!DOCTYPE html>
        <html>
        <head>
        <title>SystemMessage</title>
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
        <h1>SystemMessage</h1>
        <pre class="error">
        &lt;string&gt;:2: (WARNING/2) Inline interpreted text or phrase reference start-string without end-string.
        </pre>
        <pre>
        <BLANKLINE>
        Some text with an `error
        <BLANKLINE>
        </pre>
        </body>
        </html>

        >>> stderr_patcher.stop()

    """


def doctest_RestViewer_get_markup():
    """Test for RestViewer.get_markup

        >>> viewer = RestViewer('.')
        >>> print(viewer.get_markup('''
        ... <html>
        ... <head>
        ... <title>Title</title>
        ... </head>
        ... <body>
        ... <p>Some body text</p>
        ... </body>
        ... </html>
        ... ''').strip())
        <html>
        <head>
        <title>Title</title>
        </head>
        <body>
        <p>Some body text</p>
        </body>
        </html>

    """


def doctest_RestViewer_get_markup_adds_ajax():
    """Test for RestViewer.get_markup

        >>> viewer = RestViewer('.')
        >>> print(viewer.get_markup('''
        ... <html>
        ... <head>
        ... <title>Title</title>
        ... </head>
        ... <body>
        ... <p>Some body text</p>
        ... </body>
        ... </html>
        ... ''', mtime=1364808683).strip())
        <html>
        <head>
        <title>Title</title>
        </head>
        <body>
        <p>Some body text</p>
        <BLANKLINE>
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
                xmlHttp.open('HEAD', '/polling?pathname=' + location.pathname + '&mtime=1364808683', true);
                xmlHttp.send(null);
            }, 0);
        }
        window.onbeforeunload = function () {
            xmlHttp.abort();
        }
        </script>
        </body>
        </html>

    """


def doctest_RestViewer_get_markup_command_output():
    """Test for RestViewer.get_markup

        >>> viewer = RestViewer('.', command='python setup.py --long-description')
        >>> print(viewer.get_markup('''
        ... <html>
        ... <head>
        ... <title>restview</title>
        ... </head>
        ... <body>
        ... <p>Some body text</p>
        ... </body>
        ... </html>
        ... ''').strip())
        <html>
        <head>
        <title>restview -e "python setup.py --long-description"</title>
        </head>
        <body>
        <p>Some body text</p>
        </body>
        </html>

    """


class TestRestViewer(unittest.TestCase):

    def test_serve(self):
        viewer = RestViewer('.')
        viewer.server = Mock()
        viewer.serve()
        viewer.server.serve_forever.assert_called_once()


class TestGlobals(unittest.TestCase):

    def test_get_host_name(self):
        with patch('socket.gethostname', lambda: 'myhostname.local'):
            self.assertEqual(get_host_name(''), 'myhostname.local')
            self.assertEqual(get_host_name('0.0.0.0'), 'myhostname.local')
            self.assertEqual(get_host_name('localhost'), 'localhost')

    def test_launch_browser(self):
        with patch('threading.Thread') as Thread:
            launch_browser('http://example.com')
            Thread.assert_called_once_with(target=webbrowser.open,
                                           args=('http://example.com',))
            Thread.return_value.setDaemon.assert_called_once_with(True)
            Thread.return_value.start.assert_called_once()


class TestMain(unittest.TestCase):

    def _serve(self):
        self._serve_called = True
        raise KeyboardInterrupt()

    def run_main(self, *args, **kw):
        expected_exit_code = kw.pop('rc', 0)
        serve_called = kw.pop('serve_called', False)
        browser_launched = kw.pop('browser_launched', False)
        if kw: # pragma: nocover
            raise TypeError("unexpected keyword arguments: %s"
                            % ", ".join(sorted(kw)))
        self._serve_called = False
        with patch('sys.argv', ['restview'] + list(args)):
            with patch('sys.stdout', StringIO()) as stdout:
                with patch('sys.stderr', StringIO()) as stderr:
                    with patch('restview.restviewhttp.launch_browser') as launch_browser:
                        with patch.object(RestViewer, 'serve', self._serve):
                            try:
                                main()
                            except SystemExit as e:
                                self.assertEqual(e.args[0], expected_exit_code)
                            else: # pragma: nocover
                                if not serve_called:
                                    self.fail("main() did not raise SystemExit")
                            if serve_called:
                                self.assertTrue(self._serve_called)
                            if browser_launched:
                                launch_browser.assert_called_once()
                            return stdout.getvalue(), stderr.getvalue()

    def test_help(self):
        stdout, stderr = self.run_main('--help')
        self.assertTrue('restview [options] filename-or-directory' in stdout,
                        stdout)

    def test_error_when_no_arguments(self):
        stdout, stderr = self.run_main(rc=2)
        self.assertEqual(stderr.splitlines()[-1],
             'restview: error: at least one argument expected')

    def test_error_when_both_command_and_file_specified(self):
        stdout, stderr = self.run_main('-e', 'cat README.rst', 'CHANGES.rst',
                                       rc=2)
        self.assertEqual(stderr.splitlines()[-1],
             'restview: error: specify a command (-e) or a file/directory,'
             ' but not both',
             stderr)

    def test_all_is_well(self):
        self.run_main('.', serve_called=True, browser_launched=True)

    def test_multiple_files(self):
        self.run_main('README.rst', 'CHANGES.rst', serve_called=True,
                      browser_launched=True)

    def test_command(self):
        self.run_main('--long-description',
                      serve_called=True, browser_launched=True)

    def test_specify_listen_address(self):
        with patch.object(RestViewer, 'listen'):
            with patch.object(RestViewer, 'close'):
                self.run_main('-l', '0.0.0.0:8080', '.',
                            serve_called=True, browser_launched=True)

    def test_specify_invalid_listen_address(self):
        stdout, stderr = self.run_main('-l', 'nonsense', '.', rc=2)
        self.assertEqual(stderr.splitlines()[-1],
             'restview: error: Invalid address: nonsense')

    def test_custom_css_url(self):
        self.run_main('.', '--css', 'http://example.com/my.css',
                      serve_called=True, browser_launched=True)

    def test_custom_css_file(self):
        self.run_main('.', '--css', 'my.css',
                      serve_called=True, browser_launched=True)


def test_suite():
    return unittest.TestSuite([
        unittest.makeSuite(TestMyRequestHandler),
        unittest.makeSuite(TestRestViewer),
        unittest.makeSuite(TestGlobals),
        unittest.makeSuite(TestMain),
        doctest.DocTestSuite(optionflags=doctest.ELLIPSIS|doctest.REPORT_NDIFF),
        doctest.DocTestSuite('restview.restviewhttp'),
    ])


if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
