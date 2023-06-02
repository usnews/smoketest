import datetime
import json
import os
import re
import socket
import sys
from xml.etree import ElementTree

import requests
from requests.exceptions import RequestException
import yaml

from smoketest.loggers import get_logger
from smoketest.platforms import get_platforms_from_element
from smoketest.settings import (
    get_ca_path,
    get_default_request_timeout,
)
from smoketest.utils import (
    transform_url_based_on_options,
    transform_url,
)
from smoketest.tests import (
    get_tests_from_element,
    RedirectTest,
    StatusTest,
)


SITEMAP_NAMESPACE = 'http://www.sitemaps.org/schemas/sitemap/0.9'


def _get_single_url(elem, options):
    do_transforms = True
    # If given a choice of URLs, pick based on level.
    try:
        try:
            url = elem[options.level]
            # If the user wants this particular URL for this level, don't
            # do level transform, cachebusting, etc.
            do_transforms = False
        except KeyError:
            url = elem['other']
    except TypeError:
        # We weren't given a choice at all, just take what's there.
        url = elem

    if do_transforms:
        url = transform_url_based_on_options(url, options)
    return url


def get_urls_from_element(elem, options):
    urls = []
    try:
        # User gives list of urls
        for x in elem['urls']:
            urls.append(_get_single_url(x, options))
    except KeyError:
        # User gives one url
        urls.append(_get_single_url(elem['url'], options))
    return urls


class _SessionError(Exception):

    def __init__(self, message, url):
        super(_SessionError, self).__init__(message)
        self.url = url


# Poor man's mock objects that we use for dry runs.
class _DummySession(object):

    def close(self):
        pass


class _DummyRequest(object):

    def __init__(self):
        self.headers = {}


class _DummyResponse(object):

    def __init__(self):
        self.elapsed = datetime.timedelta(milliseconds=1)
        self.status_code = 200
        self.is_redirect = False
        self.history = ()
        self.headers = {}
        self.request = _DummyRequest()
        self.text = ''


def get_session(elem, options):
    if options.dry_run:
        return _DummySession()

    session = requests.Session()
    if options.user_agent:
        session.headers['User-Agent'] = options.user_agent

    basic_auth_instructions = elem.get('basic_auth_instructions')
    if basic_auth_instructions:
        session.auth = (
            basic_auth_instructions['username'],
            basic_auth_instructions['password'],
        )

    auth_cookie_instructions = elem.get('auth_cookie_instructions')
    if auth_cookie_instructions:
        url = transform_url_based_on_options(
            auth_cookie_instructions['url'],
            options,
        )
        data = auth_cookie_instructions['data']
        try:
            session.post(
                url,
                data=data,
                verify=get_ca_path(),
            )
        except Exception as e:
            raise _SessionError(e.message, url)

        if not bool(session.cookies.values()):
            msg = "Login attempt failed with credentials {0}".format(
                sorted(data.items())
            )
            raise _SessionError(msg, url)

    return session


class CheckDirective(object):
    """
    elem (dict): Configuration that applies specifically to this directive
    options (argparse.Namespace): The parsed command line arguments
    """

    def __init__(self, elem, options):
        self.options = options
        self.elem = elem
        self.timeout = elem.get('timeout', get_default_request_timeout())
        self.urls = get_urls_from_element(elem, options)
        self.tests = get_tests_from_element(elem, options)
        self.logger = get_logger(self.options)
        self.platforms = get_platforms_from_element(elem)
        self.follow_redirects = elem.get(
            'follow_redirects', False
        )

    def get_response(self, url, extra_headers):
        if self.options.dry_run:
            response = _DummyResponse()
            return response

        response = self.session.get(
            url,
            verify=get_ca_path(),
            allow_redirects=self.follow_redirects,
            timeout=self.timeout,
            headers=extra_headers,
        )
        return response

    def run(self):
        try:
            self.session = get_session(self.elem, self.options)
        except _SessionError as e:
            # This probably means some credentials were bad or a login URL is
            # unavailable. Just log the error and use a dumb session instead.
            self.logger.log_error(e.url, e, None)
            self.session = requests.Session()

        self.failed = False
        # Use a set for de-duplication
        failed_urls_ = set()
        for platform in self.platforms:
            # Union time
            failed_urls_ |= self._run_for_platform(platform)

        # Set urls to a list of only failed URLs in case passes > 1
        self.urls = list(failed_urls_)
        self.session.close()

    def _run_for_platform(self, platform):
        extra_headers = platform.headers
        # Use a set for de-duplication
        failed_urls = set()
        for url in self.urls:
            try:
                response = self.get_response(url, extra_headers)
            except (RequestException, socket.timeout) as e:
                self.logger.log_error(url, e, platform)
                failed_urls.add(url)
                self.failed = True
                continue

            for test in self.tests:
                if self.options.dry_run:
                    result = test.get_always_passing_result(response)
                else:
                    result = test.get_result(response)
                self.logger.log_test_result(url, test, result, response, platform, self.follow_redirects)
                if not result:
                    failed_urls.add(url)
                    self.failed = True
        return failed_urls

    @property
    def directives(self):
        return [self, ]


class IncludeDirective(object):
    """A bunch of directives from another file.

    This assumes the filename will "just work", so either make it absolute,
    or run the program from an appropriate place.
    """
    def __init__(self, elem, options):
        self.filename = elem['filename']
        self.options = options

    def run(self):
        pass

    @property
    def directives(self):
        return generate_directives_from_file(self.filename, self.options)


def generate_directives_from_file(filename, options):
    return FileParser(filename, options).generate_directives()


class InputFileError(Exception):

    def __init__(self, filename, error):
        self.filename = filename
        self.error = error

    def __str__(self):
        return self.error


class FileParser(object):
    """Parses an input file into directives

    Supported file types:
        txt
        json
        yaml (or yml)
        xml (sitemaps only)
    """

    _visited_files = set()
    _directive_map = {
        'check': CheckDirective,
        'include': IncludeDirective,
    }

    def __init__(self, filename, options):
        self.filename = filename
        self.options = options

    def generate_directives(self):
        # protect against circular references
        if self.filename in self._visited_files:
            message = "Skipping {0}, someone's already done that".format(
                self.filename
            )
            sys.stderr.write(message)
            sys.stderr.flush()
            return []
        self._visited_files.add(self.filename)

        # dispatch on type
        parts = self.filename.rpartition('.')
        if parts[0]:
            filetype = parts[-1]
            if filetype in ['json', 'yaml', 'yml']:
                return self._generate_directives_from_json_or_yaml()
            elif filetype == 'xml':
                return self._generate_directives_from_xml()
            else:
                return self._generate_directives_from_dumb_list()
        else:
            return self._generate_directives_from_dumb_list()

    def _generate_directives_from_json_or_yaml(self):
        # Load input
        try:
            with open(self.filename, 'r') as file_:
                if self.filename.endswith('json'):
                    try:
                        input_ = json.load(file_)
                    except ValueError as e:
                        # This happens if the JSON was invalid.
                        raise InputFileError(self.filename, str(e))
                else:
                    try:
                        input_ = yaml.safe_load(file_)
                    except yaml.error.YAMLError as e:
                        raise InputFileError(self.filename, str(e))
        except IOError as e:
            # This happens if the file doesn't exist.
            raise InputFileError(self.filename, str(e))

        # Parse input
        directives = []
        for elem in input_:
            try:
                directive_type = elem['directive']
                only_levels = elem.get('only_levels', [])
                if only_levels:
                    if not isinstance(only_levels, list):
                        m = u'Only levels should be a list, not {0}'.format(
                            type(only_levels)
                        )
                        raise Exception(m)
                    if not any(re.match(regex, self.options.level) for regex in only_levels):
                        continue
            except TypeError:
                # elem isn't like a dict? probably a plain string
                directive_type = 'check'
                elem = {
                    'directive': directive_type,
                    'urls': (elem,),
                }
            except KeyError:
                continue

            directive_type = self._directive_map[directive_type]
            if directive_type is IncludeDirective:
                self._absolutize_element_filename(elem)

            directive = directive_type(elem, self.options)
            directives += directive.directives

        for directive in directives:
            yield directive

    def _generate_directives_from_xml(self):
        # Load input
        if not self.filename.startswith('http'):
            try:
                with open(self.filename, 'r') as file_:
                    try:
                        tree = ElementTree.parse(file_)
                        root = tree.getroot()
                    except ElementTree.ParseError as e:
                        # This happens if the XML couldn't be parsed
                        raise InputFileError(self.filename, str(e))
            except IOError as e:
                # This happens if the file doesn't exist
                raise InputFileError(self.filename, str(e))
        else:
            # Fetch remote sitemap and parse it
            url = self.filename
            response = requests.get(url)
            if response.status_code != 200:
                raise InputFileError(self.filename, 'URL returned {} response'.format(response.status_code))
            try:
                root = ElementTree.fromstring(response.text)
            except ElementTree.ParseError as e:
                raise InputFileError(self.filename, 'Could not parse response to XML. Error: {0}'.format(str(e)))

        # Check whether it's a sitemap
        if root.tag == '{' + SITEMAP_NAMESPACE + '}urlset':
            return self._generate_directives_from_xml_sitemap(root)
        elif root.tag == '{' + SITEMAP_NAMESPACE + '}sitemapindex':
            return self._generate_directives_from_xml_sitemap_index(root)
        else:
            raise InputFileError(self.filename, 'XML input must be a sitemap')

    def _generate_directives_from_xml_sitemap_index(self, root):
        """A minimal sitemap index looks something like:

        <sitemapindex>
            <sitemap>
                <loc>https://www.example.com</loc>
            </sitemap>
        </sitemapindex>
        """
        directive_type = self._directive_map['check']
        directives = []

        # Generate directives
        for loc in root.iterfind('./ns:sitemap/ns:loc', {
            'ns': SITEMAP_NAMESPACE
        }):
            elem = {
                'directive': 'check',
                'follow_redirects': False,
                'url': loc.text,
            }

            directive = directive_type(elem, self.options)
            directives += directive.directives

        for directive in directives:
            yield directive


    def _generate_directives_from_xml_sitemap(self, root):
        """A minimal sitemap looks something like:

        <?xml version="1.0" encoding="utf-8"?>
        <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
            <url>
                <loc>https://www.example.com</loc>
            </url>
        </urlset>
        """
        directive_type = self._directive_map['check']
        directives = []

        # Generate directives
        for loc in root.iterfind('./ns:url/ns:loc', {
            'ns': SITEMAP_NAMESPACE
        }):
            elem = {
                'directive': 'check',
                'follow_redirects': False,
                'url': loc.text,
            }

            directive = directive_type(elem, self.options)
            directives += directive.directives

        for directive in directives:
            yield directive

    def _generate_directives_from_dumb_list(self):
        directives = []
        try:
            with open(self.filename, 'r') as f:
                for line in f:
                    directive = self._get_directive_from_dumb_list_line(line)
                    if directive:
                        directives.extend(directive.directives)
        except IOError as e:
            # This happens if the file doesn't exist.
            raise InputFileError(self.filename, str(e))

        for directive in directives:
            yield directive

    def _get_directive_from_dumb_list_line(self, line):
        # poorman's comment cleanup
        cleaned = line.partition("#")[0].strip()
        if cleaned:
            redirect_to = None
            redirect_to_indicator = '->'
            if cleaned[0].isdigit() and redirect_to_indicator not in cleaned:
                status, url = cleaned.split()

            # Accommodate lines of this nature:
            # 30X http://www.usnews.com/congress/platts-todd -> http://www.usnews.com/topics/people/todd_russell_platts'
            elif redirect_to_indicator in cleaned:
                assert cleaned[0] == '3'
                split = cleaned.split()
                assert split[2] == redirect_to_indicator
                status = split[0]
                url = split[1]
                redirect_to = split[3]
            else:
                status = '200'
                url = cleaned

            # Accommodate lines like:
            # 30X_live http://premium.usnews.com/best-colleges/myfit
            # If we're testing against live, use the status given, otherwise 200.
            if status.endswith('_live'):
                if self.options.level == 'live':
                    status = status.replace('_live', '')
                else:
                    status = '200'

            elem = {"url": url}
            directive = CheckDirective(elem, self.options)
            if redirect_to:
                transformed_redirect_to = transform_url(
                    redirect_to,
                    scheme=self.options.scheme,
                    port=self.options.port,
                    level=self.options.level,
                    cachebust=False,
                )
                directive.tests = [RedirectTest(status, transformed_redirect_to, False)]
            else:
                directive.tests = [StatusTest(status)]
            return directive

        # Accommodate lines like:
        # #include static.txt
        elif line.startswith('#include'):
            elem = {"filename": line.split()[1]}
            self._absolutize_element_filename(elem)
            directive = IncludeDirective(elem, self.options)
            return directive

    def _absolutize_element_filename(self, elem):
        if elem['filename'].startswith('http'):
            return
        # This assumes element's filename is relative to the test file.
        if not os.path.isabs(elem['filename']):
            elem['filename'] = os.path.join(
                os.getcwd(),
                os.path.dirname(self.filename),
                elem['filename'],
            )
        return elem
