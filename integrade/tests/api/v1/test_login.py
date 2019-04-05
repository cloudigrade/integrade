"""Test authentication with the server.

:caseautomation: automated
:casecomponent: api
:caseimportance: high
:caselevel: integration
:requirement: Cloud Meter
:testtype: functional
:upstream: yes
"""
import pytest

from integrade import api
from integrade.config import get_config
from integrade.tests import urls
from integrade.tests.utils import create_user_account
from integrade.utils import uuid4


@pytest.skip(reason='injector, also redundant?')
@pytest.mark.smoketest
def test_login_logout():
    """Test that we can login, make requests and logout to the server.

    :id: 2eb55229-4e1e-4d35-ac4a-4f2424d37cf6
    :description: Test that we can login, make requests and logout to the
        server.
    :steps:
        1) Send POST with username and password to the token endpoint.
        2) Send a GET request to /auth/me/ with the authorization token from
           previous step in the headers.
        3) Send a POST request to /auth/token/destroy/.
        4) Try to access /auth/me/ again with the authorization token from step
           1.
    :expectedresults:
        1) Receive an authorization token that can then be used to build
           authentication headers and make authenticated requests.
        2) Assert a 200 response is returned and the information about the
           logged in user are correct, including being flagged as a non-super
           user
        3) Assert a 204 response is returned
        4) Assert a 401 response is returned and the detailed message states
           the authentication token is now invalid.
    """
    user = create_user_account()
    client = api.Client(authenticate=False)
    response = client.post(urls.AUTH_TOKEN_CREATE, user)
    assert response.status_code == 200
    json_response = response.json()
    assert 'auth_token' in json_response
    assert not json_response['is_superuser']
    auth = api.TokenAuth(json_response['auth_token'])

    response = client.get(urls.AUTH_ME, auth=auth)
    assert response.status_code == 200
    json_response = response.json()
    assert json_response['email'] == user['email']
    assert json_response['username'] == user['username']

    response = client.post(urls.AUTH_TOKEN_DESTROY, {}, auth=auth)
    assert response.status_code == 204

    client.response_handler = api.echo_handler
    response = client.get(urls.AUTH_ME, auth=auth)
    assert response.status_code == 401
    json_response = response.json()
    assert json_response['detail'] == 'Invalid token.'


@pytest.skip(reason='superuser, injector')
def test_superuser_login():
    """Test that we can login as a super user and identify we are super.

    :id: 0815070f-5042-45ba-a6bb-f2596f764c7e
    :description: Test that we can login with a super user's credentials and
        that the token response includes a flag indicating super user status.
    :steps:
        1) Send POST with username and password to the token endpoint.
    :expectedresults:
        1) Receive an authorization token that can then be used to build
           authentication headers and make authenticated requests.
        2) Assert a 200 response is returned and the information about the
           logged in user are correct
        3) Assert the response includes the `is_superuser` field set to True
    """
    config = get_config()
    client = api.Client(authenticate=False)
    user = {
        'username': config['super_user_name'],
        'password': config['super_user_password'],
    }
    response = client.post(urls.AUTH_TOKEN_CREATE, user)
    assert response.status_code == 200
    json_response = response.json()
    assert 'auth_token' in json_response
    assert json_response['is_superuser']


@pytest.skip(reason='Redundant?')
@pytest.mark.parametrize(
    'endpoint', ('account', 'event', 'instance', 'image', 'report/instances'))
def test_token_negative(endpoint):
    """Given that we have an invalid token, we cannot make requests.

    :id: a87f7069-3ee9-4435-a953-fd8664199419
    :description: Test that if we have a bad token, we cannot use it to make
        requests to any of the /api/v1/* endpoints
    :steps:
        1) Send a GET request with a invalid authorization token in the header
           to all /api/v1/* endpoints.
        2) Assert that we get a 401 response for all requests.
    :expectedresults: The server rejects our invalid token for all /api/v1/*
        endpoints.
    """
    client = api.Client(response_handler=api.echo_handler)
    auth = api.TokenAuth(uuid4())
    response = client.get(f'/api/v1/{endpoint}', auth=auth)
    assert response.status_code == 401
    assert response.json() == {'detail': 'Invalid token.'}
