"""Client for working with Cloudigrade's API.

This module provides a flexible API client for talking with the cloudigrade
server, allowing the user to customize how return codes are handled depending
on the context.

"""
import logging
import os
from json import JSONDecodeError
from pprint import pformat
from urllib.parse import urljoin, urlunparse

import requests
from requests.auth import AuthBase
from requests.exceptions import HTTPError

from integrade import config, exceptions
from integrade.exceptions import MissingConfigurationError
from integrade.tests.constants import (
    QA_URL, STAGE_URL
)
from integrade.tests.utils import (
    get_credentials
)

AUTHORIZATION_HEADER = 'Authorization'
logger = logging.getLogger(__name__)


def raise_error_for_status(response):
    """Generate an error message and raise HTTPError for bad return codes.

    :raises: ``requests.exceptions.HTTPError`` if the response status code is
        in the 4XX or 5XX range.
    """
    if 400 <= response.status_code <= 599:
        error_msgs = (
            '\n============================================================\n'
            '\nThe request you made received a status code that indicates\n'
            'an error was encountered. Details about the request and the\n'
            'response are below.\n'
            '\n============================================================\n'
        )

        try:
            response_message = 'json_error_message : {}'.format(
                pformat(response.json()))
        except JSONDecodeError:
            response_message = 'text_error_message : {}'.format(
                pformat(response.text))

        error_headers = response.request.headers.copy()
        if error_headers.get(AUTHORIZATION_HEADER) is not None:
            error_headers[AUTHORIZATION_HEADER] = '*' * 8
        error_msgs += '\n\n'.join(
            [
                'request path : {}'.format(pformat(
                    response.request.path_url)),
                'request body : {}'.format(pformat(
                    response.request.body)),
                'request headers : {}'.format(pformat(
                    error_headers)),
                'response code : {}'.format(response.status_code),
                '{error_message}'.format(error_message=response_message)
            ]
        )
        error_msgs += (
            '\n============================================================\n'
        )
        raise HTTPError(error_msgs)


def echo_handler(response):
    """Immediately return ``response``."""
    return response


def code_handler(response):
    """Check the response status code, and return the response.

    :raises: ``requests.exceptions.HTTPError`` if the response status code is
        in the 4XX or 5XX range.
    """
    raise_error_for_status(response)
    return response


def json_handler(response):
    """Like ``code_handler``, but also return a JSON-decoded response body.

    Do what :func:`integrade.api.code_handler` does. In addition, decode the
    response body as JSON and return the result.
    """
    raise_error_for_status(response)
    return response.json()


class TokenAuth(AuthBase):
    """A class that enables token authentication with the Requests library.

    For more information, see the Requests documentation on `custom
    authentication
    <http://docs.python-requests.org/en/latest/user/advanced/#custom-authentication>`_.
    """

    def __init__(self, token, header_format='Token'):
        """Require token variable."""
        self.token = token
        self.header_format = header_format

    def __call__(self, request):
        """Modify header and return request."""
        request.headers['Authorization'] = ' '.join((
            self.header_format,
            self.token,
        ))
        return request


class Client(object):
    """A client for interacting with the cloudigrade API.

    This class is a wrapper around the ``requests.api`` module provided by
    `Requests`_. Each of the functions from that module are exposed as methods
    here, and each of the arguments accepted by Requests' functions are also
    accepted by these methods. The difference between this class and the
    `Requests`_ functions lies in its configurable request and response
    handling mechanisms.

    All requests made via this client use the base URL of the Cloudigrade
    server provided in your the environment variable $CLOUDIGRADE_BASE_URL.

    Additionally, we need an authorizatoin token. At the moment this must be
    provided to us via $CLOUDIGRADE_TOKEN. This is likely to change as the API
    develops.

    You can override this base url by assigning a new value to the url
    field.

    Example::
        >>> from integrade import api
        >>> client = api.Client()
        >>> # I can now make requests to the Cloudigrade server
        >>> # using relative paths, because the base url
        >>> # was set using information from my enviroment.
        >>>
        >>> client.get()
        >>>
        >>> # now if I want to do something else,
        >>> # I can change the base url
        >>> client.url = 'https://www.whatever.com'

    .. _Requests: http://docs.python-requests.org/en/master/
    """

    def __init__(self, response_handler=None, url=None, authenticate=True,
                 token=None):
        """Initialize this object, collecting base URL from config file.

        If no response handler is specified, use the `code_handler` which will
        raise an exception for 'bad' return codes.

        If no URL is specified, then the url will be built from the
        environment variables $CLOUDIGRADE_BASE_URL and $USE_HTTPS values (see
        integrade/config.py).
        """
        self.token = token
        self.url = url
        cfg = config.get_config()
        self.verify = cfg.get('ssl-verify', False)

        if not self.url:
            hostname = cfg.get('base_url')

            if not hostname:
                raise exceptions.BaseUrlNotFound(
                    'Make sure you have $CLOUDIGRADE_BASE_URL set in in'
                    ' your environment.'
                )

            scheme = cfg.get('scheme')
            self.url = urlunparse(
                (
                    scheme,
                    hostname,
                    'api/{}/'.format(cfg.get('api_version')),
                    '', '', ''
                ))

        if response_handler is None:
            self.response_handler = code_handler
        else:
            self.response_handler = response_handler

        if authenticate:
            if not self.token:
                self.token = cfg.get('superuser_token')
            if not self.token:
                raise exceptions.TokenNotFound(
                    'No token was found to authenticate with the server. Make '
                    'sure you have $CLOUDIGRADE_TOKEN set in in your '
                    'environment.'
                )

    def default_headers(self):
        """Build the headers for our request to the server."""
        if self.token:
            return {AUTHORIZATION_HEADER: 'Token {}'.format(self.token)}
        return {}

    def delete(self, endpoint, **kwargs):
        """Send an HTTP DELETE request."""
        url = urljoin(self.url, endpoint)
        return self.request('DELETE', url, **kwargs)

    def get(self, endpoint='', **kwargs):
        """Send an HTTP GET request."""
        url = urljoin(self.url, endpoint)
        return self.request('GET', url, **kwargs)

    def options(self, endpoint, **kwargs):
        """Send an HTTP OPTIONS request."""
        url = urljoin(self.url, endpoint)
        return self.request('OPTIONS', url, **kwargs)

    def head(self, endpoint, **kwargs):
        """Send an HTTP HEAD request."""
        url = urljoin(self.url, endpoint)
        return self.request('HEAD', url, **kwargs)

    def patch(self, endpoint, payload, **kwargs):
        """Send an HTTP PATCH request."""
        url = urljoin(self.url, endpoint)
        return self.request('PATCH', url, json=payload, **kwargs)

    def post(self, endpoint, payload, **kwargs):
        """Send an HTTP POST request."""
        url = urljoin(self.url, endpoint)
        return self.request('POST', url, json=payload, **kwargs)

    def put(self, endpoint, payload, **kwargs):
        """Send an HTTP PUT request."""
        url = urljoin(self.url, endpoint)
        return self.request('PUT', url, json=payload, **kwargs)

    def request(self, method, url, **kwargs):
        """Send an HTTP request.

        Arguments passed directly in to this method override (but do not
        overwrite!) arguments specified in ``self.request_kwargs``.
        """
        # The `self.request_kwargs` dict should *always* have a "url" argument.
        # This is enforced by `self.__init__`. This allows us to call the
        # `requests.request` function and satisfy its signature:
        #
        #     request(method, url, **kwargs)
        #
        headers = self.default_headers()
        headers.update(kwargs.get('headers', {}))
        kwargs['headers'] = headers
        kwargs.setdefault('verify', self.verify)
        return self.response_handler(requests.request(method, url, **kwargs))


class ClientV2(object):
    """A lightweight client for interacting with the cloudigrade API V2.

    This class is a wrapper around the ``requests.api`` module provided by
    `Requests`_.

    .. _Requests: http://docs.python-requests.org/en/master/
    """

    def __init__(self, url=None, response_handler=None, auth=None,
                 env=None, branch=None):
        """Initialize this object, collecting base URL."""
        self.url = url
        cfg = config.get_config()
        self.verify = cfg.get('ssl-verify', False)
        self.auth = auth if auth is not None else get_credentials()
        self.env = env
        if branch is None:
            self.branch = os.environ.get('BRANCH_NAME')
        else:
            self.branch = branch
        if not self.branch:
            raise MissingConfigurationError(
                'BRANCH_NAME is missing.'
            )
        if response_handler is None:
            self.response_handler = code_handler
        else:
            self.response_handler = response_handler
        self._guess_v2_environment()

    def _guess_v2_environment(self):
        if self.branch == 'master':
            if self.url is None:
                self.url = STAGE_URL
            if self.env is None:
                self.env = 'qa'
        else:
            if self.url is None:
                self.url = QA_URL
            if self.env is None:
                self.env = 'ci'
        self.headers = {
            'X-4Scale-Env': self.env,
            'X-4Scale-Branch': self.branch,
        }

    def request(self, method, endpoint, **kwargs):
        """Send an HTTP request."""
        url = urljoin(self.url, endpoint)
        logger.debug(f'{method} {url} {self.headers} {self.auth} {kwargs}')
        response = requests.request(
            method=method,
            url=url,
            headers=self.headers,
            auth=self.auth,
            verify=self.verify,
            **kwargs
        )
        return self.response_handler(response)
