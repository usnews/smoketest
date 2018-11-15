from __future__ import unicode_literals

import datetime
import inspect
import json
import os
import re
from io import BytesIO
import string
from xml.etree.ElementTree import ParseError
from xml.etree import ElementTree

import jsonschema
import lxml
from lxml.etree import XMLSyntaxError
import lxml.html
from lxml.cssselect import CSSSelector

from smoketest.utils import (
    cached_property,
    transform_url,
    uncachebust,
)

# A list of functions to use to get tests
_PARSERS = []


def get_tests_from_element(elem, options):
    tests = []

    for parser in _PARSERS:
        new_tests = parser(elem, options)
        if new_tests:

            # Allow list-like or singular return
            if hasattr(new_tests, '__iter__'):
                tests.extend(new_tests)
            else:
                tests.append(new_tests)

    return tests


# Dictionary of response: lxml tree
# Making trees out of HTML blocks is relatively expensive so keep a cache
# of them here.
_TREE_CACHE = {}


def get_tree(response):
    try:
        return _TREE_CACHE[response]
    except KeyError:
        try:
            tree = lxml.html.fromstring(response.text)
        except (lxml.etree.XMLSyntaxError, lxml.etree.ParserError):
            tree = None
        _TREE_CACHE[response] = tree
        return tree


class Whens(object):
    Never = 'never'
    Always = 'always'


def select_from_json(json_document, selector):
    here = json.loads(json_document)
    if not selector:
        return here

    # Keep track of how far into the selector we've gotten, so that if an
    # error occurs we can report where.
    selected = []
    for x in selector.split('.'):
        selected.append(x)
        if isinstance(here, dict):
            try:
                here = here[x]
            except KeyError:
                raise KeyError(u'Key {0} not found'.format(
                    '.'.join(selected)
                ))
        elif isinstance(here, list):
            try:
                here = here[int(x)]
            except IndexError:
                raise IndexError(u'Index {0} not found'.format(
                    '.'.join(selected)
                ))
            except ValueError:
                # "x" wasn't an integer
                raise ValueError(u'Array found at {0}'.format(
                    '.'.join(selected)
                ))
        else:
            raise ValueError(
                u'Ran out of containers to select from at {0}'.format(
                    '.'.join(selected)
                ))
    return here


def parser(func):
    """A goofy thing to make adding more tests easier.
    """
    # Check that the programmer is using this correctly.
    argspec = inspect.getargspec(func)
    assert argspec.args == ['elem', 'options']
    assert argspec[1:] == (None, None, None)

    _PARSERS.append(func)
    return func


@parser
def get_status_tests(elem, options):
    # If element has a redirect test on it, just use that since it
    # requires a status anyway.
    if 'redirect' in elem:
        return None

    status = elem.get('status', '200')

    try:
        # Allow status to depend on level
        try:
            code = status[options.level]
        except KeyError:
            code = status.get('other', '200')

    except TypeError:
        code = status

    return [StatusTest(code)]


@parser
def get_redirect_tests(elem, options):
    try:
        redirect = elem['redirect']
    except KeyError:
        return []
    exact = redirect.get('exact', False)
    code = redirect.get('status', '200')
    location = redirect['location']
    follow_redirects = elem.get(
        'follow_redirects',
        False,
    )
    if not exact:
        location = transform_url(
            location,
            port=options.port,
            level=options.level,
            cachebust=False,
        )
    return [RedirectTest(code, location, follow_redirects)]


@parser
def get_html_tests(elem, options):
    all_html_tests = []
    for test in elem.get('html', []):
        html_tests = []
        selector = test['selector']
        attribute = test.get('attribute')
        when = test.get('when', Whens.Always)

        for text_matching_methodname in TextMatchingMethod.available_methods:
            if text_matching_methodname in test:
                text_matching_method = TextMatchingMethod(
                    text_matching_methodname,
                    test[text_matching_methodname],
                )
                html_tests.append(
                    HTMLTest(
                        selector,
                        attribute,
                        text_matching_method,
                        when,
                    ))

        # If there were no text-matching instructions, make sure we end up
        # with at least one test out of this. This is most often going
        # to be a test that an element does not exist.
        if not html_tests:
            html_tests.append(
                HTMLTest(
                    selector,
                    attribute,
                    None,
                    when,
                ))

        all_html_tests.extend(html_tests)

    return all_html_tests


@parser
def get_json_tests(elem, options):
    all_json_tests = []
    for test in elem.get('json', []):
        json_tests = []
        selector = test['selector']

        for text_matching_methodname in TextMatchingMethod.available_methods:
            if text_matching_methodname in test:
                text_matching_method = TextMatchingMethod(
                    text_matching_methodname,
                    test[text_matching_methodname],
                )
                json_tests.append(
                    JSONTest(
                        selector,
                        text_matching_method,
                    )
                )

        all_json_tests.extend(json_tests)

    return all_json_tests


@parser
def get_response_time_test(elem, options):
    if 'response_time' in elem:
        response_time_delta = datetime.timedelta(
            seconds=float(elem['response_time'])
        )
        return ResponseTimeTest(response_time_delta)


@parser
def get_xml_tests(elem, options):
    tests = []
    if 'xml' in elem:
        if 'root' in elem['xml']:
            tests.append(XMLRootTest(elem['xml']['root']))
        if 'dtd_filename' in elem['xml']:
            tests.append(DTDTest(elem['xml']['dtd_filename']))
    return tests


@parser
def get_json_schema_tests(elem, options):
    tests = []
    if 'json_schema' in elem:
        if 'schema_filename' in elem['json_schema']:
            test = JSONSchemaTest(elem['json_schema']['schema_filename'])
            tests.append(test)
    return tests


@parser
def get_header_tests(elem, options):
    all_header_tests = []
    for test in elem.get('headers', []):
        header_tests = []
        header = test['header']

        for text_matching_methodname in TextMatchingMethod.available_methods:
            if text_matching_methodname in test:
                text_matching_method = TextMatchingMethod(
                    text_matching_methodname,
                    test[text_matching_methodname],
                )
                header_tests.append(
                    HeaderTest(
                        header,
                        text_matching_method,
                    )
                )

        all_header_tests.extend(header_tests)

    return all_header_tests


class TextMatchingMethod(object):
    """Wraps supported text matching methods so other stuff can be agnostic
    about it.
    """

    available_methods = (
        'regex', 'startswith', 'endswith', 'equals', 'contains',
    )

    def __init__(self, methodname, text_to_match):
        assert methodname in self.available_methods
        self.methodname = methodname
        if text_to_match:
            # Apply HTML whitespace transform
            text_to_match = re.sub(
                '[' + string.whitespace + u'\xa0' + ']+', ' ',
                text_to_match.strip())
        self.text_to_match = text_to_match

    def __call__(self, text_to_test):
        if text_to_test:
            # Apply HTML whitespace transform
            text_to_test = re.sub(
                '[' + string.whitespace + u'\xa0' + ']+', ' ',
                text_to_test.strip())
        if self.methodname == 'regex':
            match = re.search(self.text_to_match, text_to_test)
        elif self.methodname == 'startswith':
            match = text_to_test.startswith(self.text_to_match)
        elif self.methodname == 'endswith':
            match = text_to_test.endswith(self.text_to_match)
        elif self.methodname == 'contains':
            match = self.text_to_match in text_to_test
        else:
            assert self.methodname == 'equals'
            match = (text_to_test == self.text_to_match)
        return match

    @property
    def description(self):
        if self.methodname == 'regex':
            description = u'matches the regex {0}'.format(self.text_to_match)
        else:
            description = u'{0} {1}'.format(self.methodname, self.text_to_match)
        return description


class TestResult(object):

    def __init__(self, test, response):
        self.test = test
        self.response = response

    @property
    def description(self):
        """Description of what happened.

        This should report the features of the response that the test actually
        cares about, and use the past tense.

        Examples:
        status code was 200
        header X-Brightspot-Endpoint was None
        """
        raise NotImplementedError

    def __nonzero__(self):
        """Boolean for whether the test passed or failed.
        """
        raise NotImplementedError

    def __bool__(self):
        return self.__nonzero__()


class AlwaysPassingTestResult(TestResult):

    @property
    def description(self):
        return 'everything good because this is the result that always passes'

    def __nonzero__(self):
        return True


class HTMLTestResult(TestResult):

    @property
    def description(self):
        return u'{0} {1} was: {2}'.format(
            self.test.selector,
            self.test.attr or 'text',
            self._string_to_test,
        )

    def __nonzero__(self):
        element_should_be_present = (self.test.when == Whens.Always)
        element_is_present = (self._element is not None)
        if element_should_be_present and not element_is_present:
            return False
        if not element_should_be_present:
            if element_is_present:
                return False
            else:
                return True

        assert element_should_be_present
        if self._string_to_test is None:
            return False

        match = self.test.text_matching_method(self._string_to_test)
        return bool(match)

    @cached_property
    def _element(self):
        tree = get_tree(self.response)
        if tree is None:
            return None
        selector = CSSSelector(self.test.selector)
        elements = selector(tree) or [None]
        return elements[0]

    @cached_property
    def _string_to_test(self):
        element = self._element
        if element is None:
            return None

        if self.test.text:
            try:
                # .text_content() returns the text content of the element,
                # including the text content of its children, with no markup.
                # See https://lxml.de/lxmlhtml.html#html-element-methods
                string_to_test = element.text_content()
            except AttributeError:
                string_to_test = None
        else:
            string_to_test = element.get(
                self.test.attr
            )

        if string_to_test:
            # We never care about the whitespace around text in HTML, and it
            # causes false positives, so remove it.
            string_to_test = re.sub(
                '[' + string.whitespace + u'\xa0' + ']+', ' ',
                string_to_test.strip())

        return string_to_test


class JSONTestResult(TestResult):

    @property
    def description(self):
        try:
            string_to_test = self._get_string_to_test()
        except (KeyError, IndexError, ValueError) as e:
            return u'Error trying to find {0}: {1}'.format(
                self.test.selector,
                str(e),
            )
        else:
            return u'{0} was {1}'.format(
                self.test.selector,
                string_to_test,
            )

    def __nonzero__(self):
        try:
            string_to_test = self._get_string_to_test()
        except (KeyError, IndexError, ValueError):
            return False
        match = self.test.text_matching_method(string_to_test)
        return bool(match)

    def _get_string_to_test(self):
        return select_from_json(
            self.response.text,
            self.test.selector
        )


class StatusTestResult(TestResult):

    @property
    def description(self):
        return "status code was %s" % self.response.status_code

    def __nonzero__(self):
        wished = [i.upper() for i in list(str(self.test.target_code))]
        seen = list(str(self.response.status_code))
        if 'X' in wished:
            seen = list(map(lambda i_v: 'X' if wished[i_v[0]] == 'X' else i_v[1],
                        enumerate(seen)))
        return wished == seen


class RedirectTestResult(StatusTestResult):

    @property
    def description(self):
        return "status code was {0} and {1}location was {2}".format(
            self.response.status_code,
            'final ' if self.test.follow_redirects else '',
            self._actual_location or 'not present',
        )

    def __nonzero__(self):

        # If we're following intermediate redirects, this will check the
        # status of the final location.
        status_ok = super(RedirectTestResult, self).__nonzero__()
        # If it's not even the right status just return False
        if not status_ok:
            return status_ok

        wished_location = self.test.target_location
        location_ok = wished_location == self._actual_location
        return status_ok and location_ok

    @property
    def _actual_location(self):
        if self.test.follow_redirects:
            # If we're following intermediate redirects, check the final
            # location.
            location = uncachebust(self.response.url)
        else:
            header = self.response.headers.get('location')
            if header:
                # Some of our redirects throw away the cachebuster, which is fine,
                # so remove it here.
                location = uncachebust(header)
            else:
                location = None
        return location


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


class XMLRootTestResult(TestResult):

    @property
    def description(self):
        return "tk"

    def __nonzero__(self):
        try:
            root = ElementTree.fromstring(self.response.text.encode("UTF-8"))
            if root.tag == self.test.root:
                return True
            else:
                return False
        except ParseError:
            return False


class DTDTestResult(TestResult):

    def __init__(self, *args, **kwargs):
        super(DTDTestResult, self).__init__(*args, **kwargs)
        self._error = None

    @property
    def description(self):
        if self._error:
            return "Response body did not obey {0}: {1}".format(
                self.test.dtd_filename,
                str(self._error),
            )
        return "Response body obeyed %s" % self.test.dtd_filename

    def __nonzero__(self):
        xmlschema = lxml.etree.DTD(self.test.dtd_filename)
        s = BytesIO(self.response.text.encode("UTF-8"))
        try:
            response_doc = lxml.etree.parse(s)
        except XMLSyntaxError as e:
            self._error = e
            return False
        try:
            xmlschema.assertValid(response_doc)
            return True
        except lxml.etree.DocumentInvalid as e:
            self._error = e
            return False


class JSONSchemaTestResult(TestResult):

    def __init__(self, *args, **kwargs):
        super(JSONSchemaTestResult, self).__init__(*args, **kwargs)
        self._description = None

    @property
    def description(self):
        return self._description

    def __nonzero__(self):
        if not os.path.exists(self.test.schema_filename):
            self._description = 'Schema file {0} not found'.format(
                self.test.schema_filename
            )
            return False

        with open(self.test.schema_filename) as f:
            try:
                schema = json.load(f)
            except ValueError:
                self._description = 'Schema file {0} was not valid JSON'.format(
                    self.test.schema_filename
                )
                return False

        try:
            json_response = json.loads(self.response.text)
        except ValueError:
            self._description = 'Response body was not valid JSON'
            return False

        try:
            jsonschema.validate(json_response, schema)
        except jsonschema.exceptions.ValidationError as e:
            self._description = 'Response did not obey {0}: {1}'.format(
                self.test.schema_filename,
                e.args[0],
            )
            return False
        except (jsonschema.exceptions.SchemaError, AttributeError) as e:
            # I really wish that jsonschema wrapped all possible schema errors,
            # but it seems like it does not, so we're catching AttributeError
            # too to catch some more schema problems.
            self._description = 'Schema file {0} had a problem: {1}'.format(
                self.test.schema_filename,
                e.args[0],
            )
            return False

        self._description = 'Response body obeyed {0}'.format(
            self.test.schema_filename
        )
        return True


class HeaderTestResult(TestResult):

    @property
    def description(self):
        header = self.test.header
        header_value = self._get_header_value_from_response()
        if header_value is None:
            description = u'{0} header was not present'.format(header)
        else:
            description = u'{0} header was {1}'.format(header, header_value)
        return description

    def __nonzero__(self):
        actual_value = self._get_header_value_from_response()
        if actual_value is None:
            return False
        match = self.test.text_matching_method(actual_value)
        return bool(match)

    def _get_header_value_from_response(self):
        return self.response.headers.get(self.test.header)


class AbstractTest(object):

    def get_result(self, response):
        # If I'm a StatusTest, return a StatusTestResult
        return globals()[self.__class__.__name__+'Result'](self, response)

    def get_always_passing_result(self, response):
        return AlwaysPassingTestResult(self, response)


class StatusTest(AbstractTest):
    def __init__(self, target_code):
        self.target_code = target_code

    @property
    def description(self):
        return "status code is %s" % self.target_code


class RedirectTest(StatusTest):

    def __init__(self, target_code, target_location, follow_redirects):
        self.target_code = target_code
        self.target_location = target_location
        self.follow_redirects = follow_redirects

    @property
    def description(self):
        return "status code is {0} and {1}location is {2}".format(
            self.target_code,
            'final ' if self.follow_redirects else '',
            self.target_location,
        )


class ResponseTimeTest(AbstractTest):

    def __init__(self, response_time):
        self.response_time = response_time

    @property
    def description(self):
        return "Response time is {0} seconds or less".format(self.response_time)


class XMLRootTest(AbstractTest):

    def __init__(self, root):
        self.root = root

    @property
    def description(self):
        return "XML root is %s" % self.root


class DTDTest(AbstractTest):

    def __init__(self, dtd_filename):
        self.dtd_filename = dtd_filename

    @property
    def description(self):
        return "Response body obeys %s" % self.dtd_filename


class HTMLTest(AbstractTest):

    def __init__(self, selector, attr, text_matching_method, when):
        self.selector = selector
        self.attr = attr
        self.text_matching_method = text_matching_method
        self.when = when

        # If not given an attribute, check the tag text.
        if self.attr is None:
            self.text = True
        else:
            self.text = False

    @property
    def description(self):
        if self.when == Whens.Never:
            return '{0} is not present'.format(
                self.selector
            )
        else:
            return "{0} {1} {2}".format(
                self.selector,
                self.attr or 'text',
                self.text_matching_method.description,
            )


class JSONTest(AbstractTest):

    def __init__(self, selector, text_matching_method):
        self.selector = selector
        self.text_matching_method = text_matching_method

    @property
    def description(self):
        return "{0} {1}".format(
            self.selector,
            self.text_matching_method.description,
        )


class JSONSchemaTest(AbstractTest):

    def __init__(self, schema_filename):
        self.schema_filename = schema_filename

    @property
    def description(self):
        return 'Response body obeys %s' % self.schema_filename


class HeaderTest(AbstractTest):

    def __init__(self, header, text_matching_method):
        self.header = header
        self.text_matching_method = text_matching_method

    @property
    def description(self):
        return u'{0} header {1}'.format(
            self.header,
            self.text_matching_method.description,
        )
