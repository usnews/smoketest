import unittest


class TestUtilities(unittest.TestCase):

    def test_chunkify(self):
        from smoketest.utils import chunkify

        # ordinary case where 2 < n < len(seq)
        self.assertEqual(
            chunkify(range(10), 3),
            [[0, 1, 2, ], [3, 4, 5, ], [6, 7, 8, 9, ]]
        )

        # n = 1 case
        self.assertEqual(
            chunkify(range(10), 1),
            [range(10)],
        )

        # n == len(seq) case
        self.assertEqual(
            chunkify(range(10), 10),
            map(lambda x: [x], range(10)),
        )

        # n > len(seq) case
        self.assertEqual(
            chunkify(range(1), 2),
            [[], [0]],
        )

    def test_uncachebust_no_cachebuster(self):
        from smoketest.utils import uncachebust
        expected = 'usnews.com?b=2&a=1&c='
        actual = uncachebust('usnews.com?b=2&a=1&c=')
        self.assertEqual(expected, actual)

    def test_uncachebust_with_cachebuster(self):
        from smoketest.utils import uncachebust
        expected = 'usnews.com?b=2&a=1&c='
        actual = uncachebust('usnews.com?_=123&b=2&a=1&c=')
        self.assertEqual(expected, actual)


class TestTransformUrlBasedOnOptions(unittest.TestCase):

    def test_cachebusting(self):
        from smoketest.utils import transform_url_based_on_options
        from collections import namedtuple
        import re
        Options = namedtuple('Options', ('scheme', 'level', 'port', 'cachebust'))
        url = 'http://www.usnews.com'
        cachebust_pattern = re.compile(r'\?_=\d+$')

        options = Options(None, 'stag', None, True)
        transformed = transform_url_based_on_options(url, options)
        self.assertTrue(cachebust_pattern.search(transformed))

        options = Options(None, 'stag', None, False)
        transformed = transform_url_based_on_options(url, options)
        self.assertFalse(cachebust_pattern.search(transformed))

    def test_level(self):
        from smoketest.utils import transform_url_based_on_options
        from collections import namedtuple
        Options = namedtuple('Options', ('scheme', 'level', 'port', 'cachebust'))
        url = 'http://www.usnews.com'

        options = Options(None, 'live', None, False)
        transformed = transform_url_based_on_options(url, options)
        self.assertEqual(transformed, url)

        options = Options(None, 'stag', None, False)
        transformed = transform_url_based_on_options(url, options)
        self.assertEqual(transformed, 'http://www-stag.usnews.com')

    def test_custom_level(self):
        from smoketest.utils import transform_url_based_on_options
        from collections import namedtuple
        Options = namedtuple('Options', ('scheme', 'level', 'port', 'cachebust'))
        url = 'http://www-{LEVEL}.usnews.com'

        options = Options(None, 'live', None, False)
        transformed = transform_url_based_on_options(url, options)
        self.assertEqual(transformed, 'http://www.usnews.com')

        options = Options(None, 'stag', None, False)
        transformed = transform_url_based_on_options(url, options)
        self.assertEqual(transformed, 'http://www-stag.usnews.com')

        url = 'http://{LEVEL}.usnews.com'

        options = Options(None, 'live', None, False)
        transformed = transform_url_based_on_options(url, options)
        self.assertEqual(transformed, 'http://usnews.com')

        options = Options(None, 'stag', None, False)
        transformed = transform_url_based_on_options(url, options)
        self.assertEqual(transformed, 'http://stag.usnews.com')

        url = 'http://{LEVEL}-www.usnews.com'

        options = Options(None, 'live', None, False)
        transformed = transform_url_based_on_options(url, options)
        self.assertEqual(transformed, 'http://www.usnews.com')

        options = Options(None, 'stag', None, False)
        transformed = transform_url_based_on_options(url, options)
        self.assertEqual(transformed, 'http://stag-www.usnews.com')

        url = 'http://www.usnews.com/{LEVEL}/'

        options = Options(None, 'live', None, False)
        transformed = transform_url_based_on_options(url, options)
        self.assertEqual(transformed, 'http://www.usnews.com/')

        options = Options(None, 'stag', None, False)
        transformed = transform_url_based_on_options(url, options)
        self.assertEqual(transformed, 'http://www.usnews.com/stag/')

    def test_port(self):
        from smoketest.utils import transform_url_based_on_options
        from collections import namedtuple
        Options = namedtuple('Options', ('scheme', 'level', 'port', 'cachebust'))
        url = 'http://www.usnews.com'

        options = Options(None, 'live', None, False)
        transformed = transform_url_based_on_options(url, options)
        self.assertEqual(transformed, url)

        options = Options(None, 'live', 8999, False)
        transformed = transform_url_based_on_options(url, options)
        self.assertEqual(transformed, 'http://www.usnews.com:8999')

    def test_scheme(self):
        from smoketest.utils import transform_url_based_on_options
        from collections import namedtuple
        Options = namedtuple('Options', ('scheme', 'level', 'port', 'cachebust'))
        url = 'http://www.usnews.com'

        options = Options('https', 'live', None, False)
        transformed = transform_url_based_on_options(url, options)
        self.assertEqual(transformed, 'https://www.usnews.com')

        options = Options('https', 'stag', None, False)
        transformed = transform_url_based_on_options(url, options)
        self.assertEqual(transformed, 'https://www-stag.usnews.com')
