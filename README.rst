=========
Smoketest
=========

Smoketest is a pretty simple website tester written in Python.

Features
========

* Test aspects of HTTP responses:

  * Check status codes

  * Check redirect locations

  * Check HTTP header values

  * Check that HTML elements match string patterns

  * Check that JSON values match string patterns

  * Check that an XML response obeys a DTD

  * Check that response time is below a threshold

* Run tests against URLs behind basic or cookie-based authentication
* Run tests against desktop and mobile versions of pages
* Multithreaded test-running
* Pretty output to your shell
* Detailed JSON output
* Easy to expand input files to include new tests

Requirements
============

Smoketest requires Python 2.7 or 3.4 and above.

Installation
============

You should probably install into a Python virtual environment with a supported
Python version. To start with a fresh one, do::

    virtualenv venv
    source venv/bin/activate

You can install with pip, or you can clone this repository and do::

    python setup.py install

Usage
=====

After installing, use the smoketest script::

    smoketest [options] [input files]

For the complete list of current options, do::

    smoketest -h

Examples
--------

Let's test that the page https://www.usnews.com returns a 200
status code, and that https://www.usnews.com/fake returns a 404.

First, make an input file called ``tests.txt`` that looks like so::

    200 https://www.usnews.com
    404 https://www.usnews.com/fake

Now we can test these pages by doing::

    smoketest --verbosity=3 tests.txt

We see some output like this::

    url: https://www.usnews.com/fake?_=1493408753708
    test: status code is 404
    result: status code was 404
    passed: True
    time: 0:00:00.121320
    platform: desktop
    hops: 0

    url: https://www.usnews.com/?_=1493408753708
    test: status code is 200
    result: status code was 200
    passed: True
    time: 0:00:01.836115
    platform: desktop
    hops: 0

Notice that a cachebusting query parameter is appended to the URLs
automatically.

To transform the URLs to test a different environment, use the ``--level``
and ``--port`` options. For example, by doing::

    smoketest --level=sand2 --port=8010 tests.txt

We hit these URLs::

    https://www-sand2.usnews.com:8010/fake?_=1493408753708
    https://www-sand2.usnews.com:8010/?_=1493408753708

For more examples see the complete documentation under the ``docs/`` directory.

Running tests
=============

To run the unit tests, make sure you have `tox <http://tox.readthedocs.io/en/latest/install.html>`_ installed, then do::

    tox

Building HTML documentation
===========================

To build the documentation as HTML, do::

    ./bin/build_docs

Now you have HTML documentation in the `docs/build/html/` directory.

To force a particular version of Python for the virtualenv used for building
the documentation, create virtualenv (however you'd like, Python 3.6 example
below) at `sphinx_venv/` at the project root and install Sphinx::

    python3.6 -m venv sphinx_venv
    sphinx_venv/bin/pip install Sphinx

and then run `bin/build_docs` as above.
