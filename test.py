#!/usr/bin/python
import unittest
import doctest

def test_suite():
    return doctest.DocTestSuite('restview.restviewhttp')

if __name__ == '__main__':
    import sys, os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))
    unittest.main(defaultTest='test_suite')
