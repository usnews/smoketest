from collections import namedtuple

from smoketest.settings import get_mobile_headers


Platform = namedtuple(
    'Platform',
    [
        'name',
        'headers',
    ],
)


Desktop = Platform(name='desktop', headers={})
Mobile = Platform(name='mobile', headers=get_mobile_headers())


def get_platforms_from_element(elem):
    requested_platforms = elem.get(
        'platforms',
        ['desktop'],
    )
    platforms = []
    for name in requested_platforms:
        # This lookup is a little sketch.
        platforms.append(globals()[name.title()])
    return platforms
