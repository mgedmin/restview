#!/usr/bin/python
import unittest
import doctest

def test_suite():
    return doctest.DocTestSuite('restviewhttp')

if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
