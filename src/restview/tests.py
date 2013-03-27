import doctest
import unittest


def test_suite():
    return doctest.DocTestSuite('restview.restviewhttp')


if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
