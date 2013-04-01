import doctest
import unittest
import webbrowser

try:
    from cStringIO import StringIO
except ImportError:
    from io import StringIO

from mock import Mock, patch

from restview.restviewhttp import (MyRequestHandler, RestViewer,
                                   get_host_name, launch_browser, main)


class MyRequestHandlerForTests(MyRequestHandler):
    def __init__(self):
        pass


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
        <BLANKLINE>
        <script type="text/javascript">
        ...
        </script>
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
        <BLANKLINE>
        <script type="text/javascript">
        ...
        </script>
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
        <BLANKLINE>
        <script type="text/javascript">
        ...
        </script>
        </body>
        </html>

        >>> stderr_patcher.stop()

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
                            else:
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
             ' but not both')

    def test_all_is_well(self):
        self.run_main('.', serve_called=True, browser_launched=True)

##  def test_multiple_files(self): # XXX: broken at the moment!
##      self.run_main('README.rst', 'CHANGES.rst', serve_called=True,
##                    browser_launched=True)

    def test_command(self):
        self.run_main('--long-description',
                      serve_called=True, browser_launched=True)

    def test_specify_listen_address(self):
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
        unittest.makeSuite(TestRestViewer),
        unittest.makeSuite(TestGlobals),
        unittest.makeSuite(TestMain),
        doctest.DocTestSuite(optionflags=doctest.ELLIPSIS|doctest.REPORT_NDIFF),
        doctest.DocTestSuite('restview.restviewhttp'),
    ])


if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
