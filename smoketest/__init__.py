import imp
import io
from time import sleep
import sys

import argparse

from smoketest.directives import (
    InputFileError,
    generate_directives_from_file,
)
from smoketest.loggers import (
    Constants as LoggingConstants,
    get_logger,
)
from smoketest.settings import (
    get_default_threads,
    get_default_user_agent,
    get_plugin_names,
)
from smoketest.threads import (
    alive_threads,
    get_threads_and_stop_event,
)


def load_plugins():
    for plugin_name in get_plugin_names():
        f, path, desc = imp.find_module(plugin_name, ['plugins'])
        imp.load_module(plugin_name, f, path, desc)


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        'input_filenames', nargs='+'
    )

    # Environment-related settings
    parser.add_argument(
        '-s', '--scheme',
        dest='scheme',
        default=None,
        help='Transform URLs to use a particular scheme (e.g. http)'
    )
    parser.add_argument(
        '-l', '--level',
        dest='level',
        default='live',
        help='Transform live-site URLs to target a particular server (e.g., dev, stag)'
    )
    parser.add_argument(
        '-p', '--port',
        dest='port',
        type=int,
        help='Transform live-site URLs to target a particular port (e.g., 8080)'
    )

    # Miscellaneous settings
    parser.add_argument(
        '-t', '--threads',
        dest='threads', type=int,
        help='Number of threads to use'
    )
    parser.add_argument(
        '-u', '--user-agent',
        dest='user_agent',
        default=get_default_user_agent(),
        help='Custom User-Agent header'
    )
    parser.add_argument(
        '--no-cachebust',
        action='store_false', dest='cachebust', default=True,
        help='Disable cachebusting',
    )
    parser.add_argument(
        '--dry-run',
        action='store_true', dest='dry_run',
        help="Don't actually make any requests"
    )

    # Logging-related settings
    parser.add_argument(
        '-q', '--quiet', action='store_true',
        help='Be less verbose'
    )
    parser.add_argument(
        '-v', '--verbose',
        action='count', dest='verbosity',
        help='Be more verbose; can be used multiple times'
    )
    parser.add_argument(
        '--verbosity',
        dest='verbosity', type=int,
        help='Set verbosity; --verbosity=1 is the same as -v'
    )
    parser.add_argument(
        '-o', '--output',
        dest='output', default='', type=str,
        help='Output to file'
    )
    parser.add_argument(
        '-f', '--format',
        dest='format', default=LoggingConstants.default_logger_key(), type=str,
        help='Output format; choices: {0}; default: {1}'.format(
            ', '.join(LoggingConstants.logger_keys()),
            LoggingConstants.default_logger_key()
        )
    )
    parser.add_argument(
        '--passes',
        dest='passes', default=1, type=int,
        help='Number of passes'
    )
    parser.add_argument(
        '--delay-between-passes',
        dest='delay_between_passes', default=0, type=int,
        help='Number of seconds to wait between passes; default: 0'
    )

    args = parser.parse_args()
    args.threads = args.threads or get_default_threads(args.level)
    return args


def main():
    load_plugins()
    args = parse_args()

    if args.output:
        sys.stdout = io.open(args.output, 'w')

    directives = []
    for filename in args.input_filenames:
        try:
            directives.extend(generate_directives_from_file(filename, args))
        except InputFileError as e:
            print('Smoketest had a problem with the input file "{0}":'.format(
                e.filename
            ))
            print(e)
            sys.exit(1)

    logger = get_logger(args)
    logger.start()
    failed = True
    for pass_ in range(args.passes):
        if pass_:
            sleep(args.delay_between_passes)
        logger.start_pass()
        threads, stop_event = get_threads_and_stop_event(
            directives,
            args.threads,
        )

        # Start the tests
        for thread in threads:
            thread.start()

        # Wait for tests to finish
        try:
            # Using threading.active_count() > 1 here causes a problem where a
            # keyboard interrupt sometimes results in the program hanging...
            # not sure why.
            while any(alive_threads(threads)):
                pass
        except KeyboardInterrupt:
            # Write to console even if output is going to file
            sys.__stdout__.write('\nWaiting for {0} thread{1} to stop...'.format(
                len(threads),
                '' if len(threads) == 1 else 's',
            ))
            sys.__stdout__.flush()
            stop_event.set()
            while any(alive_threads(threads)):
                for thread in threads:
                    thread.join(0.1)
            sys.__stdout__.write('\nSmoketest cancelled by user.\n')
            sys.__stdout__.flush()
            break

        logger.end_pass()

        directives = [d for d in directives if getattr(d, 'failed', True)]
        if not directives:
            failed = False
            break

    logger.end()

    sys.exit(1) if failed else sys.exit(0)


if __name__ == '__main__':
    main()
