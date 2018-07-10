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
        'six',
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
    'classifiers': [
        'License :: OSI Approved :: MIT License',
        'Operating System :: Unix',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Topic :: Internet',
        'Topic :: Internet :: WWW/HTTP',
        'Topic :: Software Development',
        'Topic :: Software Development :: Testing',
        'Topic :: Software Development :: Testing :: Traffic Generation',
    ],
}

setup(**config)
