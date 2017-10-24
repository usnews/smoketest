import unittest

from mock import Mock


class TestLoggers(unittest.TestCase):
    """Tests related to loggers.
    """

    def test_default_logger_decorator(self):
        # Create a custom logger
        from smoketest.loggers import (
            Constants,
            Logger,
            default_logger,
            get_logger,
            select_with_key,
        )
        Constants.clear()

        @default_logger
        @select_with_key('mylogger')
        class MyLogger(Logger):
            pass

        # Check that get_logger function gives us the new default
        options = Mock()
        logger = get_logger(options)
        self.assertIsInstance(logger, MyLogger)

    def test_select_with_key_decorator(self):
        # Create a custom logger
        from smoketest.loggers import (
            Constants,
            Logger,
            get_logger,
            select_with_key,
        )
        Constants.clear()
        key = 'mylogger'

        @select_with_key(key)
        class MyLogger(Logger):
            pass

        # Try getting it with get_logger
        options = Mock()
        options.format = key
        logger = get_logger(options)
        self.assertIsInstance(logger, MyLogger)
