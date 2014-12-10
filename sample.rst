================================
Sample ReStructuredText document
================================

This is a sample ReStructuredText document.

.. contents::

Lists
-----

Here we have a numbered list

1. Four
2. Five
3. Six

and a regular list

- One
- Two
- Three

and a definition list

one
    The first number.

two
    Also a number

three
    You get the idea!

and finally a field list

:One: is a field
:Two: is also a field


Command-line help
-----------------

Usage: restview [options] [files...]

-h, --help          show help
--long-description  extract and display the long_description field from setup.py

Preformatted text
-----------------

Here's some Python code::

    def uniq(seq):
        """Drop duplicate elements from the sequence.

        Does not preserve the order.
        """
        return sorted(set(seq))

also with syntax highlighting:

.. code:: python

    def uniq(seq):
        """Drop duplicate elements from the sequence.

        Does not preserve the order.
        """
        return sorted(set(seq))

oh and some doctests that demonstrate the ``uniq()`` function:

    >>> uniq([1, 2, 3, 2, 1])
    [1, 2, 3]

    >>> uniq([3, 2, 1])
    [1, 2, 3]

The alignment is kept the same for all of them, including simple
quoted blocks

    Like this one.


Footnotes
---------

Some very important [*]_ text.

.. [*] not really that important.


Tables
------

+----------------+--------------------------------------+
|                | Truth                                |
+                +------------------+-------------------+
|                | H0               | Ha                |
+-----------+----+------------------+-------------------+
| Judgement | H0 | Confidence       | Error             |
|           |    | :math:`1-\alpha` | :math:`\beta`     |
+           +----+------------------+-------------------+
|           | Ha | Error            | Power             |
|           |    | :math:`\alpha`   | :math:`1-\beta`   |
+-----------+----+------------------+-------------------+


Transitions
-----------

Some text.

----------------------

Some more text.


ReStructuredText errors
-----------------------

How can we live without demonstrating the :doc:`errors`?
