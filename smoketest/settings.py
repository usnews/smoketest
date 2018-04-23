import os

import yaml

_SETTINGS = None


def _get_settings():
    global _SETTINGS
    if _SETTINGS is None:
        filepath = os.path.join(
            os.getcwd(),
            'settings.yaml',
        )
        if os.path.isfile(filepath):
            with open(filepath) as f:
                _SETTINGS = yaml.load(f) or {}
        else:
            _SETTINGS = {}
    return _SETTINGS


def get_default_threads(level):
    thread_settings = _get_settings().get('default_threads')
    if thread_settings:
        try:
            threads = thread_settings[level]
        except KeyError:
            threads = thread_settings.get('other', 1)
    else:
        threads = 1
    return threads


def get_default_user_agent():
    fallback = 'Smoketest (http://www.usnews.com)'
    return _get_settings().get(
        'default_user_agent',
        fallback,
    )


def get_special_cases_url_transforms():
    return _get_settings().get('special_cases_url_transforms', {})


def get_mobile_headers():
    return _get_settings().get('mobile_headers', {})


def get_plugin_names():
    return _get_settings().get('plugins', [])


def get_ca_path():
    return _get_settings().get('ca_path', False)


def get_default_request_timeout():
    # Use 30.0 seconds as a fallback
    return _get_settings().get('timeout', 30.0)


def get_level_token():
    return _get_settings().get('level_token', '{LEVEL}')
