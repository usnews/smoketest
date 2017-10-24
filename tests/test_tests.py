import json
import os
import time
import unittest

from mock import (
    MagicMock,
    Mock,
)


class TestTestResults(unittest.TestCase):
    """Tests for the TestResult classes
    """

    def setUp(self):
        self.json_schema_filename = 'test-json-schema-{0}.json'.format(
            time.time(),
        )

    def tearDown(self):
        if os.path.exists(self.json_schema_filename):
            os.unlink(self.json_schema_filename)

    def test_redirect_test_result_pass(self):
        from smoketest.tests import RedirectTestResult
        test = Mock()
        response = Mock()
        test.target_code = '30X'
        test.target_location = 'usnews.com'
        test.follow_redirects = False
        response.status_code = '301'
        response.headers = dict(location='usnews.com?_=987654321')

        # Check test result object is truthy
        test_result = RedirectTestResult(test, response)
        self.assertTrue(bool(test_result))

    def test_redirect_test_result_fail_url(self):
        from smoketest.tests import RedirectTestResult
        test = Mock()
        response = Mock()
        test.target_code = '30X'
        test.target_location = 'usnews.com'
        test.follow_redirects = False
        response.status_code = '301'
        response.headers = dict(location='google.com')

        # Check test result object is falsey
        test_result = RedirectTestResult(test, response)
        self.assertFalse(bool(test_result))

    def test_redirect_test_result_fail_status_code(self):
        from smoketest.tests import RedirectTestResult
        test = Mock()
        response = Mock()
        test.target_code = '30X'
        response.status_code = '200'
        response.headers = dict(location=test.target_location)

        # Check test result object is falsey
        test_result = RedirectTestResult(test, response)
        self.assertFalse(bool(test_result))

    def test_redirect_test_result_requires_location_if_30X(self):
        from smoketest.tests import RedirectTestResult
        test = Mock()
        response = Mock()
        test.target_code = '30X'
        test.target_location = 'http://www.usnews.com'
        test.follow_redirects = False
        response.status_code = '301'
        response.headers = {}

        # Check that the test is a fail if 'location' header is missing.
        test_result = RedirectTestResult(test, response)
        self.assertFalse(test_result)

    def test_redirect_test_result_doesnt_require_location_if_non_30X(self):
        from smoketest.tests import RedirectTestResult
        test = Mock()
        response = Mock()
        test.target_code = '30X'
        response.status_code = '200'
        response.headers = {}

        # Check that checking for pass/fail raises exception
        test_result = RedirectTestResult(test, response)
        self.assertFalse(bool(test_result))

    def test_html_test_result_ordinary_success(self):
        from smoketest.tests import (
            HTMLTest,
            TextMatchingMethod,
        )
        html_test = HTMLTest(
            'h1',
            None,
            TextMatchingMethod('endswith', 'ello'),
            'always',
        )
        response = Mock()
        response.text = '<h1>hello</h1>'
        html_test_result = html_test.get_result(
            response
        )
        self.assertTrue(bool(html_test_result))
        self.assertEqual(
            'h1 text was: hello',
            html_test_result.description,
        )

    def test_html_test_result_with_child_tag(self):
        from smoketest.tests import (
            HTMLTest,
            TextMatchingMethod,
        )
        html_test = HTMLTest(
            'h1',
            None,
            TextMatchingMethod('endswith', 'ello'),
            'always',
        )
        response = Mock()
        response.text = '<h1><img src="example.com">hello</h1>'
        html_test_result = html_test.get_result(
            response
        )
        self.assertTrue(bool(html_test_result))
        self.assertEqual(
            'h1 text was: hello',
            html_test_result.description,
        )

    def test_html_test_result_ordinary_failure(self):
        from smoketest.tests import (
            HTMLTest,
            TextMatchingMethod,
        )
        html_test = HTMLTest(
            'h1',
            None,
            TextMatchingMethod('equals', 'ello'),
            'always',
        )
        response = Mock()
        response.text = '<h1>hello</h1>'
        html_test_result = html_test.get_result(
            response
        )
        self.assertFalse(bool(html_test_result))
        self.assertEqual(
            'h1 text was: hello',
            html_test_result.description,
        )

    def test_html_test_result_never_option_and_it_succeeds(self):
        from smoketest.tests import (
            HTMLTest,
        )
        html_test = HTMLTest(
            'h1',
            None,
            None,
            'never',
        )
        response = Mock()
        response.text = ''
        html_test_result = html_test.get_result(
            response
        )
        self.assertTrue(bool(html_test_result))
        self.assertEqual(
            'h1 text was: None',
            html_test_result.description,
        )

    def test_html_test_result_never_option_and_it_fails(self):
        from smoketest.tests import (
            HTMLTest,
        )
        html_test = HTMLTest(
            'h1',
            None,
            None,
            'never',
        )
        response = Mock()
        response.text = '<h1>hello</h1>'
        html_test_result = html_test.get_result(
            response
        )
        self.assertFalse(bool(html_test_result))
        self.assertEqual(
            'h1 text was: hello',
            html_test_result.description,
        )

    def test_html_test_result_empty_html(self):
        from smoketest.tests import (
            HTMLTest,
            TextMatchingMethod,
        )
        html_test = HTMLTest(
            'h1',
            None,
            TextMatchingMethod('equals', 'oodby'),
            'always',
        )
        response = Mock()
        response.text = ''
        html_test_result = html_test.get_result(
            response
        )
        self.assertFalse(bool(html_test_result))
        self.assertEqual(
            'h1 text was: None',
            html_test_result.description,
        )

    def test_json_schema_test_schema_file_does_not_exist(self):
        from smoketest.tests import (
            JSONSchemaTest
        )
        if os.path.exists(self.json_schema_filename):
            os.unlink(self.json_schema_filename)
        response = Mock()
        json_schema_test = JSONSchemaTest(self.json_schema_filename)
        json_schema_test_result = json_schema_test.get_result(
            response
        )
        self.assertFalse(bool(json_schema_test_result))
        self.assertEqual(
            'Schema file {0} not found'.format(self.json_schema_filename),
            json_schema_test_result.description,
        )


    def test_json_schema_test_schema_is_not_valid_json(self):
        from smoketest.tests import (
            JSONSchemaTest
        )
        # Write some garbage to the schema file
        with open(self.json_schema_filename, 'w') as f:
            f.write('GARBAGE')
        response = Mock()
        json_schema_test = JSONSchemaTest(self.json_schema_filename)
        json_schema_test_result = json_schema_test.get_result(
            response
        )
        self.assertFalse(bool(json_schema_test_result))
        self.assertEqual(
            'Schema file {0} was not valid JSON'.format(self.json_schema_filename),
            json_schema_test_result.description,
        )

    def test_json_schema_test_schema_is_not_valid_schema_bad_type(self):
        from smoketest.tests import (
            JSONSchemaTest
        )
        # Write some garbage to the schema file
        with open(self.json_schema_filename, 'w') as f:
            f.write(json.dumps(
                {
                    'type': 'fake',
                }
            ))
        response = Mock()
        response.text = '{}'
        json_schema_test = JSONSchemaTest(self.json_schema_filename)
        json_schema_test_result = json_schema_test.get_result(
            response
        )
        self.assertFalse(bool(json_schema_test_result))
        self.assertTrue(
            json_schema_test_result.description.startswith(
                'Schema file {0} had a problem'.format(
                    self.json_schema_filename
                )
            )
        )

    def test_json_schema_test_schema_is_not_valid_schema_not_even_close(self):
        from smoketest.tests import (
            JSONSchemaTest
        )
        # Write some garbage to the schema file
        with open(self.json_schema_filename, 'w') as f:
            f.write('[]')
        response = Mock()
        response.text = '{}'
        json_schema_test = JSONSchemaTest(self.json_schema_filename)
        json_schema_test_result = json_schema_test.get_result(
            response
        )
        self.assertFalse(bool(json_schema_test_result))
        self.assertTrue(
            json_schema_test_result.description.startswith(
                'Schema file {0} had a problem'.format(
                    self.json_schema_filename
                )
            )
        )

    def test_json_schema_test_non_json_response(self):
        from smoketest.tests import (
            JSONSchemaTest
        )
        with open(self.json_schema_filename, 'w') as f:
            f.write('{}')
        response = Mock()
        response.text = 'GARBAGE'
        json_schema_test = JSONSchemaTest(self.json_schema_filename)
        json_schema_test_result = json_schema_test.get_result(
            response
        )
        self.assertFalse(bool(json_schema_test_result))
        self.assertEqual(
            'Response body was not valid JSON',
            json_schema_test_result.description,
        )

    def test_json_schema_test_response_does_not_follow_schema(self):
        from smoketest.tests import (
            JSONSchemaTest
        )
        with open(self.json_schema_filename, 'w') as f:
            f.write(json.dumps(
                {
                    "type": "object",
                    "properties": {
                        "foo": {
                            "type": "string"
                        }
                    },
                    "required": ["foo"]
                }
            ))

        response = Mock()
        response.text = '{}'
        json_schema_test = JSONSchemaTest(self.json_schema_filename)
        json_schema_test_result = json_schema_test.get_result(
            response
        )
        self.assertFalse(bool(json_schema_test_result))
        self.assertEqual(
            "Response did not obey {0}: u'foo' is a required property".format(
                self.json_schema_filename
            ),
            json_schema_test_result.description,
        )

    def test_json_schema_test_everything_is_good(self):
        from smoketest.tests import (
            JSONSchemaTest
        )
        with open(self.json_schema_filename, 'w') as f:
            f.write(json.dumps(
                {
                    "type": "object",
                    "properties": {
                        "foo": {
                            "type": "string"
                        }
                    },
                    "required": ["foo"]
                }
            ))
        response = Mock()
        response.text = json.dumps({
            'foo': 'bar'
        })
        json_schema_test = JSONSchemaTest(self.json_schema_filename)
        json_schema_test_result = json_schema_test.get_result(
            response
        )
        self.assertTrue(bool(json_schema_test_result))
        self.assertEqual(
            'Response body obeyed {0}'.format(self.json_schema_filename),
            json_schema_test_result.description,
        )

    def test_header_test(self):
        from smoketest.tests import (
            HeaderTest,
        )
        header_test = HeaderTest('X-Some-Header', 'hi')
        response = Mock()
        response.headers = {
            'X-Some-Header': 'bye',
        }
        result = header_test.get_result(response)
        self.assertFalse(result)
        self.assertEqual(
            'X-Some-Header header was bye',
            result.description,
        )


class TestTextMatchingMethod(unittest.TestCase):
    """Tests for the class TextMatchingMethod
    """

    def test_regex(self):
        from smoketest.tests import TextMatchingMethod
        text_matching_method = TextMatchingMethod(
            'regex',
            '^hello$',
        )
        self.assertTrue(text_matching_method('hello'))
        self.assertFalse(text_matching_method('shello'))

    def test_endswith(self):
        from smoketest.tests import TextMatchingMethod
        text_matching_method = TextMatchingMethod(
            'endswith',
            '^hello$',
        )
        self.assertTrue(text_matching_method('asdf ^hello$'))
        self.assertFalse(text_matching_method('hello'))

    def test_startswith(self):
        from smoketest.tests import TextMatchingMethod
        text_matching_method = TextMatchingMethod(
            'startswith',
            '^hello$',
        )
        self.assertTrue(text_matching_method('^hello$ asdf'))
        self.assertFalse(text_matching_method('hello'))

    def test_equals(self):
        from smoketest.tests import TextMatchingMethod
        text_matching_method = TextMatchingMethod(
            'equals',
            '^hello$',
        )
        self.assertTrue(text_matching_method('^hello$'))
        self.assertFalse(text_matching_method('hello'))

    def test_contains(self):
        from smoketest.tests import TextMatchingMethod
        text_matching_method = TextMatchingMethod(
            'contains',
            '^hello$',
        )
        self.assertTrue(text_matching_method('a^hello$b'))
        self.assertFalse(text_matching_method('hello'))


class TestParsers(unittest.TestCase):
    """Tests for the parser functions
    """

    def test_status_default(self):
        from smoketest.tests import (
            get_status_tests,
            StatusTest,
        )
        elem = {}
        options = Mock()
        tests = get_status_tests(elem, options)
        self.assertIsInstance(tests[0], StatusTest)
        self.assertEqual(tests[0].target_code, '200')

    def test_status_explicit(self):
        from smoketest.tests import (
            get_status_tests,
            StatusTest,
        )
        elem = {'status': '404'}
        options = Mock()
        tests = get_status_tests(elem, options)
        self.assertIsInstance(tests[0], StatusTest)
        self.assertEqual(tests[0].target_code, '404')

    def test_environment_dependent_test(self):
        from smoketest.tests import get_status_tests

        # Test with explicit default
        elem = {
            "status": {
                "live": "30X",
                "other": "404",
            }
        }
        options = Mock()
        options.level = 'live'
        tests = get_status_tests(elem, options)
        self.assertEqual(tests[0].target_code, "30X")

        options.level = 'stag'
        tests = get_status_tests(elem, options)
        self.assertEqual(tests[0].target_code, "404")

        # Test with implicit default (200)
        elem = {
            "status": {
                "live": "30X",
            }
        }
        options.level = 'stag'
        tests = get_status_tests(elem, options)
        self.assertEqual(tests[0].target_code, "200")

    def test_redirect_test(self):
        from smoketest.tests import (
            get_redirect_tests,
            RedirectTest,
        )
        elem = {
            "redirect": {
                "status": "30X",
                "location": "usnews.com",
            },
        }
        options = Mock()
        options.port = None
        options.level = None
        options.cachebust = True
        tests = get_redirect_tests(elem, options)
        self.assertIsInstance(tests[0], RedirectTest)
        self.assertEqual(tests[0].target_code, "30X")
        self.assertEqual(tests[0].target_location, "usnews.com")

    def test_html_test_regex_attribute(self):
        from smoketest.tests import (
            get_html_tests,
            HTMLTest,
        )
        elem = {
            'html': [{
                'selector': 'h1',
                'attribute': 'attr',
                'regex': 'r',
            }]
        }
        options = Mock()
        tests = get_html_tests(elem, options)
        self.assertEqual(1, len(tests))
        test = tests[0]
        self.assertIs(HTMLTest, test.__class__)
        self.assertEqual('h1', test.selector)
        self.assertEqual('attr', test.attr)
        self.assertEqual('regex', test.text_matching_method.methodname)
        self.assertEqual('r', test.text_matching_method.text_to_match)
        self.assertEquals('h1 attr matches the regex r', test.description)
        self.assertEqual('always', test.when)
        self.assertFalse(test.text)

    def test_html_test_simple_equals(self):
        from smoketest.tests import (
            get_html_tests,
            HTMLTest,
        )
        elem = {
            'html': [{
                'selector': 'h1',
                'equals': 'r',
            }]
        }
        options = Mock()
        tests = get_html_tests(elem, options)
        self.assertEqual(1, len(tests))
        test = tests[0]
        self.assertIs(HTMLTest, test.__class__)
        self.assertEqual('h1', test.selector)
        self.assertIs(None, test.attr)
        self.assertEqual('equals', test.text_matching_method.methodname)
        self.assertEqual('r', test.text_matching_method.text_to_match)
        self.assertEquals('h1 text equals r', test.description)
        self.assertEqual('always', test.when)
        self.assertTrue(test.text)

    def test_html_test_never_exists(self):
        from smoketest.tests import (
            get_html_tests,
            HTMLTest,
        )
        elem = {
            'html': [{
                'selector': 'h1',
                'when': 'never',
            }]
        }
        options = Mock()
        tests = get_html_tests(elem, options)
        self.assertEqual(1, len(tests))
        test = tests[0]
        self.assertIs(HTMLTest, test.__class__)
        self.assertEqual('h1', test.selector)
        self.assertIs(None, test.attr)
        self.assertIs(None, test.text_matching_method)
        self.assertEquals('h1 is not present', test.description)
        self.assertEqual('never', test.when)

    def test_parser_decorator(self):
        # Define a custom parser
        from smoketest.tests import (
            get_tests_from_element,
            parser,
        )
        mymock = MagicMock()

        @parser
        def my_parser(elem, options):
            mymock.call(elem, options)

        # Check that get_tests function uses the custom parser
        elem = {}
        options = Mock()
        get_tests_from_element(elem, options)
        mymock.call.assert_called_once_with(elem, options)

    def test_get_header_tests(self):
        from smoketest.tests import (
            get_header_tests,
        )
        elem = {
            'headers': [
                {
                    'header': 'X-Some-Header',
                    'equals': 'hi',
                },
            ]
        }
        options = Mock()
        header_tests = get_header_tests(elem, options)
        self.assertEqual(1, len(header_tests))
        self.assertEqual('X-Some-Header', header_tests[0].header)
        self.assertEqual('hi', header_tests[0].value)


class TestSelectFromJsonifiable(unittest.TestCase):

    def test_empty_json_empty_selector(self):
        from smoketest.tests import select_from_json
        json_string = '""'
        selector = ''
        result = select_from_json(json_string, selector)
        expected = ''
        self.assertEqual(result, expected)

    def test_true_json_empty_selector(self):
        from smoketest.tests import select_from_json
        json_string = 'true'
        selector = ''
        result = select_from_json(json_string, selector)
        expected = True
        self.assertEqual(result, expected)

    def test_object_empty_selector(self):
        from smoketest.tests import select_from_json
        json_string = """
            {"foo": "hi!"}
        """
        selector = ''
        result = select_from_json(json_string, selector)
        expected = {'foo': 'hi!'}
        self.assertEqual(result, expected)

    def test_object_unnested_selector(self):
        from smoketest.tests import select_from_json
        json_string = """
            {"foo": "hi!"}
        """
        selector = 'foo'
        result = select_from_json(json_string, selector)
        expected = 'hi!'
        self.assertEqual(result, expected)

    def test_object_nested_selector(self):
        from smoketest.tests import select_from_json
        json_string = """
            {
                "foo": {
                    "bar": "hi!"
                }
            }
        """
        selector = 'foo.bar'
        result = select_from_json(json_string, selector)
        expected = 'hi!'
        self.assertEqual(result, expected)

    def test_array_unnested_selector(self):
        from smoketest.tests import select_from_json
        json_string = """
            [
                "foo",
                true,
                "hi!",
                null,
                false
            ]
        """
        selector = '2'
        result = select_from_json(json_string, selector)
        expected = 'hi!'
        self.assertEqual(result, expected)

    def test_array_nested_selector(self):
        from smoketest.tests import select_from_json
        json_string = """
            [
                "foo",
                true,
                [
                    "hi!",
                    "bar"
                ],
                null,
                false
            ]
        """
        selector = '2.0'
        result = select_from_json(json_string, selector)
        expected = 'hi!'
        self.assertEqual(result, expected)

    def test_object_and_array_nesting(self):
        from smoketest.tests import select_from_json
        json_string = """
            {
                "nope": 0,
                "foo": [
                    null,
                    {
                        "no!": "never",
                        "bar": [
                            {
                                "bad": "bye!",
                                "baz": "hi!"
                            },
                            false
                        ]
                    }
                ]
            }
        """
        selector = 'foo.1.bar.0.baz'
        result = select_from_json(json_string, selector)
        expected = 'hi!'
        self.assertEqual(result, expected)

    # Error cases
    def test_invalid_json(self):
        from smoketest.tests import select_from_json
        json_string = 'bad'
        selector = ''
        try:
            select_from_json(json_string, selector)
        except Exception as e:
            self.assertIsInstance(e, ValueError)
            self.assertEqual(e.message, 'No JSON object could be decoded')
        else:
            assert False, 'No exception was raised!'

    def test_non_integer_for_list(self):
        from smoketest.tests import select_from_json
        json_string = """
            [false]
        """
        selector = 'foo'
        try:
            select_from_json(json_string, selector)
        except Exception as e:
            self.assertIsInstance(e, ValueError)
            self.assertEqual(e.message, 'Array found at foo')
        else:
            assert False, 'No exception was raised!'

    def test_out_of_range_index_for_list(self):
        from smoketest.tests import select_from_json
        json_string = """
            [false]
        """
        selector = '1'
        try:
            select_from_json(json_string, selector)
        except Exception as e:
            self.assertIsInstance(e, IndexError)
            self.assertEqual(e.message, 'Index 1 not found')
        else:
            assert False, 'No exception was raised!'

    def test_non_existent_key_for_object(self):
        from smoketest.tests import select_from_json
        json_string = """
            {"foo": "bar"}
        """
        selector = 'baz'
        try:
            select_from_json(json_string, selector)
        except Exception as e:
            self.assertIsInstance(e, KeyError)
            self.assertEqual(e.message, 'Key baz not found')
        else:
            assert False, 'No exception was raised!'
