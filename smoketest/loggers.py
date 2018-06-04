from __future__ import unicode_literals

from collections import OrderedDict
import json
import sys
import time

from six import string_types


class Constants(object):
    # Set on startup by decorators in this module
    default_logger_class = None
    available_logger_classes = OrderedDict()

    # Set the first time get_logger is called
    logger_in_use = None

    @classmethod
    def logger_keys(cls):
        return cls.available_logger_classes.keys()

    @classmethod
    def default_logger_key(cls):
        for key, available_class in cls.available_logger_classes.items():
            if available_class == cls.default_logger_class:
                return key

    @classmethod
    def clear(cls):
        cls.default_logger_class = None
        cls.available_logger_classes = OrderedDict()
        cls.logger_in_use = None


def get_logger(options):
    # poor man's singleton/global logger
    if Constants.logger_in_use is not None:
        return Constants.logger_in_use

    class_ = Constants.available_logger_classes.get(
        options.format,
        Constants.default_logger_class,
    )
    Constants.logger_in_use = class_(options)
    return Constants.logger_in_use


def default_logger(class_):
    """Decorator to make a logger subclass the default one.
    """
    assert issubclass(class_, Logger)
    assert class_ in Constants.available_logger_classes.values()
    Constants.default_logger_class = class_
    return class_


def select_with_key(key):
    """Decorator to make a logger subclass selectable by the user with the
    given key.
    """
    def _logger(class_):
        assert isinstance(key, string_types)
        assert issubclass(class_, Logger)
        Constants.available_logger_classes[key] = class_
        return class_
    return _logger


class _Colors(object):
    GREEN = '\033[01;32m'
    RED = '\033[01;31m'
    ENDC = '\033[0m'


def _calculate_hops(response, follow_redirects):
    if response.is_redirect:
        # If we ended on a redirect, we must not be following redirects, and
        # there should be only one hop.
        assert not follow_redirects
        assert not len(response.history)
        hops = 1
    else:
        hops = len(response.history)
    return hops


def _format_headers(headers):
    formatted_headers = []
    for k, v in headers.items():
        formatted_headers.append(u'    {0}: {1}'.format(k, v))
    final_formatted_headers = u'\n' + u'\n'.join(formatted_headers)
    return final_formatted_headers


class Logger(object):
    """Helper class to log successes, failures, and errors, and keep track
    of how many occur.

    In practice this will be instantiated just once and used as a global
    logger.
    """

    def __init__(self, options):
        self.options = options

    def start(self):
        self.log_options()

    def end(self):
        pass

    def end_pass(self):
        self.log_summary()

    def start_pass(self):
        self.start_time = time.time()
        self.success_count = 0
        self.failure_count = 0
        self.error_count = 0

    def log_test_result(self, url, test, result, response, platform, follow_redirects):
        if result:
            self.log_success(
                url,
                test,
                result,
                response,
                platform,
                follow_redirects,
            )
        else:
            self.log_failure(
                url,
                test,
                result,
                response,
                platform,
                follow_redirects,
            )
        sys.stdout.flush()

    def log_options(self):
        """Log the options of the smoketest run.
        """
        raise NotImplementedError

    def log_success(self, url, test, result, response, platform, follow_redirects):
        """Log a successful test.
        """
        raise NotImplementedError

    def log_failure(self, url, test, result, response, platform, follow_redirects):
        """Log a failed test.
        """
        raise NotImplementedError

    def log_error(self, url, error, platform):
        """Log an error that occurred with the given URL.
        """
        raise NotImplementedError

    def log_summary(self):
        """Log a summary of the smoketest run.
        """
        raise NotImplementedError


@default_logger
@select_with_key('shell')
class _ShellLogger(Logger):

    _verbose_templates = {
        2:
        u"\n".join([
            "",
            "url: {0}",
            "test: {1}",
            "result: {2}",
            "passed: {3}",
            "platform: {4}",
            "",
        ]),
        3:
        u"\n".join([
            "",
            "url: {0}",
            "test: {1}",
            "result: {2}",
            "passed: {3}",
            "time: {4}",
            "platform: {5}",
            "hops: {6}",
            "",
        ]),
        4:
        u"\n".join([
            "",
            "url: {0}",
            "test: {1}",
            "result: {2}",
            "passed: {3}",
            "time: {4}",
            "platform: {5}",
            "hops: {6}",
            "request headers: {7}",
            "response headers: {8}",
            "body: {9}",
            "",
        ]),
    }

    def log_options(self):
        pass

    def log_success(self, url, test, result, response, platform, follow_redirects):
        test_desc = test.description
        result_desc = result.description
        elapsed = response.elapsed
        hops = _calculate_hops(response, follow_redirects)
        request_headers = _format_headers(response.request.headers)
        response_headers = _format_headers(response.headers)

        self.success_count += 1
        if self.options.quiet or not self.options.verbosity:
            message = None

        # succinct
        elif self.options.verbosity == 1:
            message = '.'

        # verbose - actually same as succint
        elif self.options.verbosity == 2:
            message = '.'

        # super verbose
        elif self.options.verbosity == 3:
            message = self._verbose_templates[3].format(
                url, test_desc, result_desc, True, elapsed, platform.name,
                hops)

        # super duper verbose
        # calling response.text can be expensive, so only do so if needed
        else:
            message = self._verbose_templates[4].format(
                url, test_desc, result_desc, True, elapsed, platform.name,
                hops, request_headers, response_headers, response.text)

        self._write_in_color(message, _Colors.GREEN)

    def log_failure(self, url, test, result, response, platform, follow_redirects):
        test_desc = test.description
        result_desc = result.description
        elapsed = response.elapsed
        platform_name = platform.name if platform else None
        hops = _calculate_hops(response, follow_redirects)
        request_headers = _format_headers(response.request.headers)
        response_headers = _format_headers(response.headers)

        self.failure_count += 1
        # succinct
        if self.options.quiet or not self.options.verbosity:
            message = "\n[FAILED: {0}]\n".format(url)

        # verbose
        elif self.options.verbosity == 2:
            message = self._verbose_templates[2].format(
                url, test_desc, result_desc, False, platform_name)

        # super verbose
        elif self.options.verbosity == 3:
            message = self._verbose_templates[3].format(
                url, test_desc, result_desc, False, elapsed, platform_name,
                hops)

        # super duper verbose
        # calling response.text can be expensive, so only do so if needed
        else:
            message = self._verbose_templates[4].format(
                url, test_desc, result_desc, False, elapsed, platform_name,
                hops, request_headers, response_headers, response.text)

        self._write_in_color(message, _Colors.RED)

    def log_error(self, url, error, platform):
        platform_name = platform.name if platform else None
        self.error_count += 1
        message = "\n[ERRORED{0}{1}: {2} {3}]\n".format(
            ' on ' if platform_name else '',
            platform_name if platform_name else '',
            url,
            str(error)
        )
        self._write_in_color(message, _Colors.RED)
        sys.stdout.flush()

    def log_summary(self):
        summary = [
            '',
            'Elapsed time: {0}'.format(time.time() - self.start_time),
            'Number of successes: {0}'.format(self.success_count),
            'Number of failures: {0}'.format(self.failure_count),
            'Number of errors: {0}'.format(self.error_count),
            '',
        ]
        sys.stdout.write('\n'.join(summary))

    def _write_in_color(self, message, color):
        if message:
            full_message = ''.join([
                color,
                message,
                _Colors.ENDC,
            ])
            sys.stdout.write(full_message)


@select_with_key('json')
class _JsonLogger(Logger):
    # TODO: Flesh out verbosity more

    def start(self):
        self._output = OrderedDict([
            ('configuration', None),
            ('results', [])
        ])
        self.log_options()

    def end(self):
        output = json.dumps(self._output, sort_keys=False,
                            indent=4, separators=(',', ': '))
        sys.stdout.write(output)
        sys.stdout.write('\n')
        sys.stdout.flush()

    def end_pass(self):
        self.log_summary()

    def log_options(self):
        self._output['configuration'] = vars(self.options)

    def log_success(self, url, test, result, response, platform, follow_redirects):
        test_desc = test.description
        result_desc = result.description
        elapsed = response.elapsed
        hops = _calculate_hops(response, follow_redirects)

        self.success_count += 1

        data = OrderedDict()

        if self.options.verbosity >= 3:
            data.update(OrderedDict([
                ('url', url),
                ('platform', platform.name),
                ('passed', True),
                ('expected_result', test_desc),
                ('returned_result', result_desc),
                ('hops', hops),
                ('time', str(elapsed)),
            ]))

        if self.options.verbosity >= 4:
            data.update(OrderedDict([
                ('request_headers', json.dumps(dict(response.request.headers))),
                ('response_headers', json.dumps(dict(response.headers))),
                ('body', response.text),
            ]))

        if data:
            self._output['results'][self.pass_]['urls'].append(data)

    def log_failure(self, url, test, result, response, platform, follow_redirects):
        test_desc = test.description
        result_desc = result.description
        elapsed = response.elapsed
        hops = _calculate_hops(response, follow_redirects)

        self.failure_count += 1

        data = OrderedDict([
            ('url', url),
            ('platform', platform.name),
            ('passed', False),
        ])

        if self.options.verbosity >= 3:
            data.update(OrderedDict([
                ('expected_result', test_desc),
                ('returned_result', result_desc),
                ('hops', hops),
                ('time', str(elapsed)),
            ]))

        if self.options.verbosity >= 4:
            data.update(OrderedDict([
                ('request_headers', json.dumps(dict(response.request.headers))),
                ('response_headers', json.dumps(dict(response.headers))),
                ('body', response.text),
            ]))

        self._output['results'][self.pass_]['urls'].append(data)

    def log_error(self, url, error, platform):
        self.error_count += 1
        self._output['results'][self.pass_]['urls'].append(OrderedDict([
            ('url', url),
            ('platform', platform.name if platform else platform),
            ('result', str(error)),
        ]))

    def log_summary(self):
        data = {
            'Elapsed time': '{0}'.format(time.time() - self.start_time),
            'Number of successes': '{0}'.format(self.success_count),
            'Number of failures': '{0}'.format(self.failure_count),
            'Number of errors': '{0}'.format(self.error_count),
        }
        self._output['results'][self.pass_]['summary'] = data

    def start_pass(self):
        super(_JsonLogger, self).start_pass()
        self._output['results'].append(
            OrderedDict([
                ('summary', None),
                ('urls', []),
            ]))
        self.pass_ = len(self._output['results']) - 1

    def _log(self, data):
        self._output.append(data)
