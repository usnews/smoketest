import unittest


class TestPlatforms(unittest.TestCase):

    def setUp(self):
        # Working around the fact that we need some actual header settings to
        # test the headers, and the other fact that the platforms are set up
        # when the platforms module is first loaded.

        import smoketest.settings
        import smoketest.platforms
        self._old_settings = smoketest.settings._SETTINGS
        smoketest.settings._SETTINGS = {
            'mobile_headers': {
                'X-Is-Mobile': 'yes',
            }
        }
        reload(smoketest.platforms)

    def tearDown(self):
        import smoketest.settings
        import smoketest.platforms
        smoketest.settings._SETTINGS = self._old_settings
        reload(smoketest.platforms)

    def test_mobile_headers(self):
        from smoketest.platforms import Mobile
        self.assertEqual(
            Mobile.headers,
            {
                "X-Is-Mobile": "yes",
            }
        )

    def test_desktop_headers(self):
        from smoketest.platforms import Desktop
        self.assertEqual(
            Desktop.headers,
            {},
        )

    def test_get_platforms_specified(self):
        from smoketest.platforms import (
            Desktop,
            Mobile,
            get_platforms_from_element,
        )
        elem = {
            'platforms': ['mobile', 'desktop'],
        }
        platforms = get_platforms_from_element(elem)
        self.assertEqual(
            platforms,
            [Mobile, Desktop],
        )

    def test_get_platforms_default(self):
        from smoketest.platforms import (
            Desktop,
            get_platforms_from_element,
        )
        elem = {}
        platforms = get_platforms_from_element(elem)
        self.assertEqual(
            platforms,
            [Desktop],
        )
