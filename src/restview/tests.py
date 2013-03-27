import doctest
import unittest

from mock import patch

from restview.restviewhttp import get_host_name


class TestGlobals(unittest.TestCase):

    def test_get_host_name(self):
        with patch('socket.gethostname', lambda: 'myhostname.local'):
            self.assertEqual(get_host_name(''), 'myhostname.local')
            self.assertEqual(get_host_name('0.0.0.0'), 'myhostname.local')
            self.assertEqual(get_host_name('localhost'), 'localhost')


def test_suite():
    return unittest.TestSuite([
        unittest.makeSuite(TestGlobals),
        doctest.DocTestSuite('restview.restviewhttp'),
    ])


if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
