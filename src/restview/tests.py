import doctest
import unittest

from mock import patch

from restview.restviewhttp import RestViewer, get_host_name


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
        </head>
        <body>
        <div class="document" id="example">
        <h1 class="title">example</h1>
        <BLANKLINE>
        <p>This is a doctest:</p>
        <blockquote>
        <pre class="doctest-block">
        <span style="color: #000080; font-weight: bold">&gt;&gt;&gt; </span><span style="color: #666666">2</span> <span style="color: #666666">+</span> <span style="color: #666666">2</span>
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

class TestGlobals(unittest.TestCase):

    def test_get_host_name(self):
        with patch('socket.gethostname', lambda: 'myhostname.local'):
            self.assertEqual(get_host_name(''), 'myhostname.local')
            self.assertEqual(get_host_name('0.0.0.0'), 'myhostname.local')
            self.assertEqual(get_host_name('localhost'), 'localhost')


def test_suite():
    return unittest.TestSuite([
        unittest.makeSuite(TestGlobals),
        doctest.DocTestSuite(optionflags=doctest.ELLIPSIS|doctest.REPORT_NDIFF),
        doctest.DocTestSuite('restview.restviewhttp'),
    ])


if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
