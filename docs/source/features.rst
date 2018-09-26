Features
========

Command line options
--------------------

Levels and ports
~~~~~~~~~~~~~~~~

At U.S. News, we develop and test our applications in many different
environments, or `levels`. We distinguish these levels with a simple URL
pattern. If we have a live page at https://www.usnews.com, we might have a
development version of that page at https://www-dev.usnews.com. If you have a
similar setup, you'll find the ``--level`` command line option useful. If you
run smoketest with a ``--level=dev`` argument, it will append "-dev" to the
first part of the domain name of every URL it tests: "www.usnews.com" becomes
"www-dev.usnews.com".

You can override that method of specifying levels by including the
``level_token`` token in URLs. The token defaults to the string:

.. code-block:: yaml

    level_token: '{LEVEL}'

For example:

.. code-block:: yaml

    - https://{LEVEL}.usnews.com/opinion
    - https://www-{LEVEL}.usnews.com/opinion

For the first ``live`` will test https://usnews.com/opinion while for a level
such as ``stag``, it will test https://stag.usnews.com/opinion. The second will
be https://www.usnews.com/opinion and https://www-stag.usnews.com/opinion,
respectively. It tries to intelligently remove extra ".", "-", and "/" as
needed if the level would be omitted in the case of ``live``.

Note that the default level is ``live``, so running smoketest without a level
argument is equivalent to running it with ``--level=live``.

Sometimes you may also want to transform URLs to specify a port; for example
you may want to test http://www.usnews.com:81. You can do this by running
smoketest with a ``--port=81`` argument.

Multi-threaded test running
~~~~~~~~~~~~~~~~~~~~~~~~~~~

If you have lots of URLs to test, you may want to speed things up by running
multiple smoketest threads. You run, say, 11 threads, by running smoketest
with the ``--threads=11`` argument.

The default behavior is to use one thread, but you can define other defaults
on a per-level basis if you create a file called ``settings.yaml`` in the
directory from which you run smoketest. If you want to run 15 threads against
live, add the following to your ``settings.yaml`` file:

.. code-block:: yaml

    default_threads:
        live: 15

You can specify a number of threads besides 1 for all other environments like
so:

.. code-block:: yaml

    default_threads:
        live: 15
        other: 2

Note that there is an example settings file called ``settings.example.yaml``
at the top level of the repository.

Input files
-----------

Smoketest accepts input files in three formats: plaintext (.txt), JSON (.json),
and YAML (.yaml).

Text files are much simpler to write, but can only do HTTP status code and
redirect tests.

JSON and YAML files both allow you to use the full set of features. The
rest of this article will assume you are working with YAML files, but an
equivalent JSON file would perform equivalent tests.

Directives
~~~~~~~~~~

Smoketest input files are made up of lists of ``directives``. There are two
types of directives. ``check`` directives are groups of tests run against one
or more URLs. For example, here is a check directive that tests that two URLs
200:

.. code-block:: yaml

    -   directive: check
        url:
            - https://www.usnews.com/opinion
            - https://www.usnews.com/cartoons
        status: 200

``include`` directives are instructions to include another input
file. Here is an example:

.. code-block:: yaml

    -   directive: include
        filename: another-input-file.json

Notice that you can use an include directive in a YAML file to include a JSON
file, and vice versa. Also note that Smoketest will look for a file relative
to the file including it. So in the above example, it would expect
``another-input-file.json`` to be in the same directory as the file with this
include.

Types of tests
--------------

This section describes the different kinds of tests you can run on one URL's
HTTP response.

HTTP status codes
~~~~~~~~~~~~~~~~~

By default, any check directive tests that the URL returns a 200.  So, the
following YAML tests that https://www.usnews.com 200s.

.. code-block:: yaml

    -   directive: check
        url: https://www.usnews.com

You can explicitly specify a status code with the ``status`` key.

.. code-block:: yaml

    -   directive: check
        url: https://www.usnews.com/fake
        status: 404

You can use an `X` as a wildcard in the status code. For example, the following
test will pass if the URL returns any redirect status code.

.. code-block:: yaml

    -   directive: check
        url: https://www.usnews.com/bruuuce
        status: 3XX

HTML contents
~~~~~~~~~~~~~

You can check that HTML elements on a page match simple text patterns. For
example, you can check that the h1 on this page is exactly what you expect:

.. code-block:: yaml

    -   directive: check
        url: https://www.usnews.com/best-colleges/american-university-1434
        html:
        -
            selector: h1
            equals: American University

The `selector` can be any CSS selector. If the selector matches more than one
element, only the first one will be tested.

You can also check an attribute of an element instead of the element text
by including an `attribute` key, like so:

.. code-block:: yaml

    -   directive: check
        url: https://www.usnews.com/best-colleges/american-university-1434
        html:
        -
            selector: meta[name='site']
            attribute: content
            equals: Best Colleges

There are a number of other text-matching patterns available besides `equals`.
Here is the complete list:

    * `equals`
    * `startswith`
    * `endswith`
    * `contains`
    * `regex`

Finally, you can test that a tag does not appear on a page like this:

.. code-block:: yaml

    -   directive: check
        url: https://www.usnews.com/best-colleges/american-university-1434
        html:
        -
            selector: meta[name='og:title']
            when: never

HTTP response headers
~~~~~~~~~~~~~~~~~~~~~

You can test that particular HTTP response headers match what you expect by
adding a `headers` list to a check directive. For example:

.. code-block:: yaml

    -   directive: check
        url: https://www.usnews.com/news/best-countries
        headers:
        -
            header: Content-Type
            equals: text/html; charset=UTF-8
        -
            header: Server
            equals: Apache

XML contents
~~~~~~~~~~~~

For URLs that return XML, the simplest test you can do is check that the root
element is what you expect. Here's an example for an RSS feed:

.. code-block:: yaml

    -   directive: check
        url: https://www.usnews.com/topics/series/picks/rss
        xml:
            root: rss

A more thorough test is to check that the XML conforms to a DTD schema. You
can provide a DTD file like so:

.. code-block:: yaml

    -   directive: check
        url: https://www.usnews.com/topics/series/picks/rss
        xml:
            dtd_filename: my-schema.dtd

When smoketest finds this directive, it will look for a file in the current
working directory named ``my-schema.dtd``. If this file does not exist
or is not a valid DTD, the test will fail but the smoketest run will
continue. Note that you can also give an absolute path to the schema file.

JSON schema compliance
~~~~~~~~~~~~~~~~~~~~~~

You can check that a URL returns a JSON body that adheres to a JSON schema.
The JSON schema must follow the specification described at
https://json-schema.org/.

Here is an example of how to configure such a test with YAML:

.. code-block:: yaml

    -   directive: check
        url: https://health.usnews.com/doctors/doximity/info/2227740
        json_schema:
            schema_filename: doctors-schema.json

When smoketest finds this directive, it will look for a file in the current
working directory named ``doctors-schema.json``. If this file does not exist
or is not a valid JSON schema, the test will fail but the smoketest run will
continue. Note that you can also give an absolute path to the schema file.

Authentication
--------------

Sometimes you want to test URLs that require credentials to get at their
contents. If the authentication mechanism is HTTP basic auth, you can
include a username and password like so:

.. code-block:: yaml

    -   directive: check
        url: https://www.usnews.com
        basic_auth_instructions:
            username: myusername
            password: mypassword

If the authentication mechanism requires you to log in on a separate login
page and acquire a cookie, you can provide instructions for that like so:

.. code-block:: yaml

    -   directive: check
        url: https://premium.usnews.com/best-colleges/myfit
        auth_cookie_instructions:
            url: https://secure.usnews.com/member/login
            data:
                username: myusername
                password: mypassword

In this case, if your username and password are rejected, and the auth URL
returns no cookie, you'll get an error like this:

::
    [ERRORED: https://secure.usnews.com/member/login?_=1456432001185 Login attempt failed with credentials [('password', 'mypassword'), ('username', 'myusername')]]

    [FAILED: https://premium.usnews.com/best-colleges/myfit?_=1456432001179]

Note that in the cookie case, the `data` provided will be serialized and 
POSTed as is, so you can change the keys as necessary. For example, you might
be testing an application with a login form that uses a field called `email`
instead of `username`, in which case you would do something like this:

.. code-block:: yaml

    -   directive: check
        url: https://premium.usnews.com/best-colleges/myfit
        auth_cookie_instructions:
            url: https://secure.usnews.com/member/login
            data:
                email: myusername
                password: mypassword

Testing mobile
--------------

If you're testing an adaptive webpage that distinguishes mobile from desktop
by looking at HTTP headers, you can test either or both versions of a page.

You'll need to create a file called ``settings.yaml`` in the directory where
you run smoketest that defines the headers to use for mobile. Here's an
example:

.. code-block:: yaml

    mobile_headers:
        X-Device-Characteristics: is_mobile=true

Now, you can define directives to run tests against mobile versions of pages
like this:

.. code-block:: yaml

    -   directive: check
        url: https://www.usnews.com
        platforms:
        -   mobile
        -   desktop

    -   directive: check
        url: https://www.usnews.com/news
        platforms:
        -   mobile
