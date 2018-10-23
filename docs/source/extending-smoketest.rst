Extending Smoketest
===================

If there's something related to HTTP responses you want to test, and smoketest
can't yet do it, you're totally encouraged to add that functionality. The place
you'll most likely be writing new code is smoketest/tests.py.

Tutorial: Writing a response time test
--------------------------------------

Say, for example, we want to add a new test that checks whether a URL loaded
in under *n* seconds.

First, let's decide on the input format we want to be able to use. Some JSON
like this makes sense to include in an input file to say that
https://www.usnews.com should load in 5 seconds or less:

.. code-block:: javascript

    [
        {
            "directive": "check",
            "url": "https://www.usnews.com",
            "response_time": "5.0"
        }
    ]

Now we need to write some code so that smoketest can turn this JSON into a
test that it understands. There are three things to do:

1. Write a test class. This is a simple class that describes what the test is
   and stores the data relevant to the test.

.. code-block:: python

    class ResponseTimeTest(AbstractTest):

        def __init__(self, response_time):
            self.response_time = response_time

        @property
        def description(self):
            return "Response time is {0} seconds or less".format(self.response_time)


2. Write a test result class. This is an object that can tell from a response
   whether or not the test passed.

.. code-block:: python

    class ResponseTimeTestResult(TestResult):

        # This is handled by the superclass, but included here for clarity.
        def __init__(self, test, response):
            self.test = test
            self.response = response

        @property
        def description(self):
            return "Response time was {0} seconds".format(self.response.elapsed)

        def __nonzero__(self):
            return self.response.elapsed <= self.test.response_time

3. Write a function to take the JSON dictionary from above and turn it into a
   ResponseTimeTest object.

.. code-block:: python

   # The parser decorator lets smoketest know to call this function and find
   # the new tests. All functions with this decorator should take two arguments:
   # a JSON element and an options namespace.
   @parser
   def get_response_time_test(elem, options):
       if 'response_time' in elem:
           response_time_delta = datetime.timedelta(seconds=float(elem['response_time']))
           return ResponseTimeTest(response_time_delta)


That's all there is to it. If we run smoketest against the input above we'll
get output like this:

::

    url: https://www.usnews.com/?_=1493410168139
    test: status code is 200
    result: status code was 200
    passed: True
    time: 0:00:02.343515
    platform: desktop
    hops: 0

    url: https://www.usnews.com/?_=1493410168139
    test: Response time is 0:00:05 seconds or less
    result: Response time was 0:00:02.343515 seconds
    passed: True
    time: 0:00:02.343515
    platform: desktop
    hops: 0


Unit tests
----------

Install `tox <https://tox.readthedocs.io/en/latest/install.html>`_, then run unit tests like this::

    $ tox

Add unit tests for new code as you see fit.
