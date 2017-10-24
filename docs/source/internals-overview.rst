Program overview
================

The basic flow of the program is as follows:

1. User calls main from a shell and specifies an input file
    a. Parse input file into directives
    b. Set up logging and threading
    c. Run each directive
        i.   GET a URL
        ii.  Check whether the response meets expectations
             like status code, redirect target, meta tag content, etc.
        iii. Log what happened
    d. Summarize what happened

Some more detail:

Input files are defined using JSON or YAML. The top groupings are "directives"
which represent high level tasks or collection of tasks like:

    * Do a bunch of tests on one URL (check directive, see below)
    * Fetch more directives from some other file
    * Do the same test on multiple URLs

Plaintext input files are also supported for doing status and redirect
tests on lists of URLs.

The core directive is the check directive. Check directives contain one or more
"tests" to perform on a URL or set of URLs. A test is something that is either
True or False about the HTTP response, such as whether the status code is 200
or whether a particular tag had a particular value.

The initial passes through the input files work to translate all specified
directives into a collection of check directives. Each check directive is then
processed in turn and/or by thread if multithreading is used. Processing means
running through the collection of tests that each check directive contains and
reporting whether they pass or fail.
