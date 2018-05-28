"""Unit tests for :mod:`integrade.api`."""
import json
from copy import deepcopy
from json import JSONDecodeError
from unittest import mock
from unittest.mock import Mock, patch
from urllib.parse import urljoin

import pytest

import requests

from integrade import api, config, exceptions
from integrade.utils import uuid4


VALID_CONFIG = {
    'superuser': 'admin',
    'superuser_pass': uuid4(),
    'base_url': 'example.com',
                'superuser_token': uuid4(),
                'scheme': 'http',
                'ssl-verify': False,
                'api_version': 'v1'
}


def mock_request():
    """Return a mock request to include as attribute of mock response."""
    mock_request = mock.Mock(
        body='{"Test Body"}',
        path_url='/example/path/',
        headers={'Authorization': 'authorizationkey'},
        text='Some text',
    )
    return mock_request


@pytest.fixture
def good_response():
    """Return a mock response with a 200 status code."""
    mock_response = mock.Mock(status_code=200, text='Some text')
    mock_response.request = mock_request()
    mock_response.json = Mock(return_value=json.dumps(
        '{"Success!"}'))
    return mock_response


@pytest.fixture
def bad_response_valid_json():
    """Return a mock response with a 404 status code and valid json."""
    mock_response = mock.Mock(status_code=404)
    mock_response.request = mock_request()
    mock_response.json = Mock(return_value=json.dumps(
        '{"The resource you requested was not found"}'))
    return mock_response


@pytest.fixture
def bad_response_invalid_json():
    """Return a mock response with a 404 status code but with bad json."""
    mock_response = mock.Mock(status_code=404, text='<No JSON!>')
    mock_response.request = mock_request()
    mock_response.json = Mock()
    mock_response.json.side_effect = JSONDecodeError(
        msg='no json',
        doc='<no json>',
        pos=0
    )
    return mock_response


def test_create_with_config():
    """If a base url is specified in the environment, we use it."""
    with patch.object(config, '_CONFIG', VALID_CONFIG):
        assert config.get_config() == VALID_CONFIG
        client = api.Client(authenticate=False)
        assert client.url == 'http://example.com/api/v1/'


def test_create_no_config():
    """If a base url is specified we use it."""
    with patch.object(config, '_CONFIG', {}):
        assert config.get_config() == {}
        other_host = 'http://hostname.com'
        client = api.Client(url=other_host, authenticate=False)
        assert 'http://example.com/api/v1/' != client.url
        assert other_host == client.url


def test_create_override_config():
    """If a base url is specified, we use that instead of config file."""
    with patch.object(config, '_CONFIG', VALID_CONFIG):
        other_host = 'http://hostname.com'
        client = api.Client(url=other_host, authenticate=False)
        cfg_host = config.get_config()['base_url']
        assert cfg_host != client.url
        assert other_host == client.url


def test_negative_create():
    """Raise an error if no config entry is found and no url specified."""
    with patch.object(config, '_CONFIG', {}):
        assert config.get_config() == {}
        with pytest.raises(exceptions.BaseUrlNotFound):
            api.Client(authenticate=False)


def test_negative_create_no_token():
    """Raise an error if no config entry is found and no url specified."""
    cfg_missing_token = deepcopy(VALID_CONFIG)
    cfg_missing_token.pop('superuser_token')
    with patch.object(config, '_CONFIG', cfg_missing_token):
        with pytest.raises(exceptions.TokenNotFound):
            api.Client(authenticate=True)


def test_empty_default_headers():
    """Test when a token is not defined, default_headers is an empty dict."""
    with patch.object(config, '_CONFIG', VALID_CONFIG):
        assert config.get_config() == VALID_CONFIG
        client = api.Client(authenticate=False)
        assert client.default_headers() == {}


@pytest.mark.parametrize('handler',
                         [
                             api.code_handler,
                             api.json_handler,
                             api.echo_handler,
                         ]
                         )
def test_response_handlers(good_response, handler):
    """Test that when we get a good 2xx response, it is returned."""
    with patch.object(config, '_CONFIG', VALID_CONFIG):
        assert config.get_config() == VALID_CONFIG
        client = api.Client(
            authenticate=False,
            response_handler=handler
        )
        r = client.response_handler(good_response)
        if handler == api.json_handler:
            assert r == good_response.json()
        else:
            assert r == good_response


@pytest.mark.parametrize('handler',
                         [
                             api.code_handler,
                             api.json_handler,
                             api.echo_handler,
                         ]
                         )
def test_response_handler_raises(
    bad_response_valid_json,
    handler
):
    """Test that when we get a 4xx or 5xx response, an error is raised."""
    with patch.object(config, '_CONFIG', VALID_CONFIG):
        assert config.get_config() == VALID_CONFIG
        bad_response = bad_response_valid_json
        client = api.Client(
            authenticate=False,
            response_handler=handler
        )
        if handler != api.echo_handler:
            with pytest.raises(requests.exceptions.HTTPError):
                client.response_handler(bad_response)
        else:
            # no error should be raised with the echo handler
            client.response_handler(bad_response)


@pytest.mark.parametrize('handler',
                         [
                             api.code_handler,
                             api.json_handler,
                             api.echo_handler,
                         ]
                         )
def test_response_handler_raises_no_json(
    bad_response_invalid_json,
    handler
):
    """Test that when we get a 4xx or 5xx response, an error is raised."""
    with patch.object(config, '_CONFIG', VALID_CONFIG):
        assert config.get_config() == VALID_CONFIG
        bad_response = bad_response_invalid_json
        client = api.Client(
            authenticate=False,
            response_handler=handler
        )
        if handler != api.echo_handler:
            with pytest.raises(requests.exceptions.HTTPError) as exc_info:
                client.response_handler(bad_response)
            assert 'No JSON!' in str(exc_info.value)
            assert "'Authorization': '********'" in str(exc_info.value)
        else:
            # no error should be raised with the echo handler
            client.response_handler(bad_response)


def test_post(good_response):
    """Test that when we use the post method, a well formed request is sent."""
    with patch.object(config, '_CONFIG', VALID_CONFIG):
        cl = api.Client()
        cl.request = Mock(return_value=good_response)
        r = cl.post('api/v1/', {})
        assert r == good_response
        cl.request.assert_called_once_with(
            'POST', urljoin(cl.url, 'api/v1/'), json={})


def test_put(good_response):
    """Test that when we use the put method, a well formed request is sent."""
    with patch.object(config, '_CONFIG', VALID_CONFIG):
        cl = api.Client()
        cl.request = Mock(return_value=good_response)
        r = cl.put('api/v1/', {})
        assert r == good_response
        cl.request.assert_called_once_with(
            'PUT', urljoin(cl.url, 'api/v1/'), json={})


def test_get(good_response):
    """Test that when we use the get method, a well formed request is sent."""
    with patch.object(config, '_CONFIG', VALID_CONFIG):
        cl = api.Client()
        cl.request = Mock(return_value=good_response)
        r = cl.get('api/v1/')
        assert r == good_response
        cl.request.assert_called_once_with(
            'GET', urljoin(cl.url, 'api/v1/'))


def test_head(good_response):
    """Test that when we use the head method, a well formed request is sent."""
    with patch.object(config, '_CONFIG', VALID_CONFIG):
        cl = api.Client()
        cl.request = Mock(return_value=good_response)
        r = cl.head('api/v1/')
        assert r == good_response
        cl.request.assert_called_once_with(
            'HEAD', urljoin(cl.url, 'api/v1/'))


def test_options(good_response):
    """Test that the options method sends a well formed request."""
    with patch.object(config, '_CONFIG', VALID_CONFIG):
        cl = api.Client()
        cl.request = Mock(return_value=good_response)
        r = cl.options('api/v1/')
        assert r == good_response
        cl.request.assert_called_once_with(
            'OPTIONS', urljoin(cl.url, 'api/v1/'))


def test_delete(good_response):
    """Test that the delete method sends a well formed request."""
    with patch.object(config, '_CONFIG', VALID_CONFIG):
        cl = api.Client()
        cl.request = Mock(return_value=good_response)
        r = cl.delete('api/v1/')
        assert r == good_response
        cl.request.assert_called_once_with(
            'DELETE', urljoin(cl.url, 'api/v1/'))


def test_request(good_response):
    """Test that the request method sets all options correctly."""
    with patch.object(config, '_CONFIG', VALID_CONFIG):
        client = api.Client()
        requests.request = Mock(return_value=good_response)
        client.request(
            'GET',
            'http://example.com/api/v1/',
            headers={
                'Foo': 'bar'})
        args, kwargs = requests.request.call_args
        assert args == ('GET', 'http://example.com/api/v1/')
        assert kwargs == {
            'headers': {
                'Authorization': 'Token {}'.format(
                    client.token),
                'Foo': 'bar'},
            'verify': False}


def test_token_auth():
    """Test TokenAuth generates proper request header."""
    token = uuid4()
    header_format = uuid4()
    auth = api.TokenAuth(token, header_format)
    request = Mock()
    request.headers = {}
    changed_request = auth(request)
    assert changed_request is request
    assert 'Authorization' in request.headers
    assert request.headers['Authorization'] == f'{header_format} {token}'
