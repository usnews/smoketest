import functools
import time
from urlparse import (
    parse_qsl,
    urlsplit,
    urlunsplit,
)
from urllib import urlencode

from smoketest.settings import (
    get_special_cases_url_transforms,
    get_level_token,
)

CACHEBUST_KEY = '_'


def transform_url_based_on_options(url, options):
    return transform_url(
        url,
        scheme=options.scheme,
        port=options.port,
        level=options.level,
        cachebust=options.cachebust,
    )


def transform_url(url, scheme=None, port=None, level=None, cachebust=None):
    parts = list(urlsplit(url))
    if scheme:
        parts[0] = scheme
    if port:
        parts = port_transform(parts, port)
    if level:
        parts = level_transform(parts, level)
    if cachebust:
        parts = cachebust_transform(parts)
    url = urlunsplit(parts)
    url = special_cases_transforms(url)
    return url


def level_transform(parts, level):
    """Transform the first subdomain according to our habits, normally.
    www.usnews.com => www-level.usnews.com

    Can also be used for a more general replacements, see the docs:
    {LEVEL}www.usnews.com => level-www.usnews.com
    """
    level_token = get_level_token()

    if level_token and level_token in parts[1] + parts[2]:
        host, path = parts[1], parts[2]
        if level == 'live':
            level = ''

        if host:
            host = host.replace(level_token, level)
            host = host.replace('..', '.').replace('-.', '.')
            if host[0] in ('-', '.'):
                host = host[1:]
        if path:
            if level == '' and level_token + '/' in path:
                path = path.replace(level_token + '/', level)
            else:
                path = path.replace(level_token, level)
        parts[1] = host
        parts[2] = path
    elif level == 'live':
        return parts
    else:
        try:
            subdomain, subdomain2, remaining = parts[1].split('.', 2)
        except ValueError:
            # no subdomain to modify
            return parts
        parts[1] = '.'.join(['{0}-{1}'.format(subdomain, level),
                            subdomain2,
                            remaining])
    return parts


def port_transform(parts, port):
    netloc, _, _ = parts[1].partition(":")
    parts[1] = ''.join([netloc, ":", str(port)])
    return parts


def cachebust_transform(parts):
    buster = int(round(time.time() * 1000))
    # Make sure path is at least / for python 2.6 and below
    if not parts[2]:
        parts[2] = '/'
    # Query piece
    if parts[3]:
        parts[3] += '&'
    parts[3] += '{0}={1}'.format(CACHEBUST_KEY, buster)
    return parts


def special_cases_transforms(url):
    """Apply special cases URL replacements dictated by settings.
    """
    for x, y in get_special_cases_url_transforms().items():
        url = url.replace(x, y)
    return url


def uncachebust(url):
    parts = urlsplit(url)
    new_parts = list(parts)

    parsed_qs = parse_qsl(parts.query, True)  # Keep blank values
    parsed_qs_without_cachebuster = filter(
        lambda x: x[0] != CACHEBUST_KEY,
        parsed_qs)
    new_parts[3] = urlencode(parsed_qs_without_cachebuster)
    return urlunsplit(new_parts)


def chunkify(seq, n):
    """Split seq into n roughly equally sized lists.

    http://stackoverflow.com/questions/2130016/splitting-a-list-of-arbitrary-size-into-only-roughly-n-equal-parts
    """
    avg = len(seq) / float(n)
    out = []
    last = 0.0

    while last < len(seq):
        out.append(seq[int(last):int(last + avg)])
        last += avg

    return out


#http://code.activestate.com/recipes/576563-cached-property/
def cached_property(fun):
    """A memoize decorator for class properties."""
    @functools.wraps(fun)
    def get(self):
        try:
            return self._cache[fun]
        except AttributeError:
            self._cache = {}
        except KeyError:
            pass
        ret = self._cache[fun] = fun(self)
        return ret
    return property(get)
