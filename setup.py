try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

config = {
    'name': 'Smoketest',
    'description': 'Smoketest is a pretty simple website tester written in Python.',
    'author': 'U.S. News & World Report',
    'url': 'https://github.com/usnews/smoketest',
    'version': '1.0.0',
    'setup_requires': [
        'nose',
        'nosexcover',
    ],
    'install_requires': [
        'PyYAML',
        'cssselect',
        'jsonschema',
        'lxml',
        'requests',
    ],
    'tests_require': [
        'coverage',
        'mock==1.0.1',
    ],
    'test_suite': 'nose.collector',
    'packages': ['smoketest'],
    'entry_points': {
        'console_scripts': [
            'smoketest = smoketest.__init__:main',
        ],
    },
}

setup(**config)
