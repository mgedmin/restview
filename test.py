#!/usr/bin/python
import unittest
import doctest

def test_suite():
    return doctest.DocTestSuite('restview.restviewhttp')

if __name__ == '__main__':
    import sys, os
    sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))
    unittest.main(defaultTest='test_suite')
