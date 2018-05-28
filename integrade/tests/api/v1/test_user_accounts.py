"""Tests for user accounts.

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
from integrade.tests.api.v1 import urls
from integrade.tests.api.v1.utils import create_user_account
from integrade.utils import gen_password, uuid4


def test_create():
    """Ensure user accounts can be created with username and password.

    :id: 5099a61d-7aa6-4c1b-8408-d030f210cd08
    :description: Ensure an user account can be created by an super user
        account with only username and password.
    :steps: With an authenticated superuser, send a post request to
        /auth/user/create/ with an username and password.
    :expectedresults: The server returns a 201 response with the information of
        the created user. The information should include the information passed
        as payload to the create request and also an ID should be created.
    """
    create_user_account({
        'email': '',
        'password': gen_password(),
        'username': uuid4(),
    })


def test_create_with_email():
    """Ensure user accounts can be created with username, email and password.

    :id: 003ac47f-9946-4ffe-b49d-732dbffe1cfc
    :description: Ensure an user account can be created by an super user
        account with username, email and password.
    :steps: With an authenticated superuser, send a post request to
        /auth/user/create/ with an username, email and password.
    :expectedresults: The server returns a 201 response with the information of
        the created user. The information should include the information passed
        as payload to the create request and also an ID should be created.
    """
    create_user_account({
        'email': 'my@email.com',
        'username': uuid4(),
        'password': gen_password()
    })


@pytest.mark.parametrize('missing_field', ('password', 'username'))
def test_create_negative(missing_field):
    """Ensure user accounts can't be created without username or password.

    :id: 133962f4-0c1c-449a-9594-5b8f3d9be0d1
    :description: Ensure an user account can't be created by an super user
        account without providing either username or password.
    :steps: With an authenticated superuser, send a post request to
        /auth/user/create/ without either username or password.
    :expectedresults: The server returns a 400 response with the information
        that the missing field is required.
    """
    user = {
        'username': uuid4(),
        'password': gen_password()
    }
    user.pop(missing_field)
    client = api.Client(response_handler=api.echo_handler)
    response = client.post(urls.AUTH_USERS_CREATE, user)
    assert response.status_code == 400
    json_response = response.json()
    assert json_response[missing_field] == ['This field is required.']


def test_change_password():
    """Ensure an user can change its account password.

    :id: 43a5ebd9-9f19-446d-8b7f-fccb7870c90d
    :description: Ensure an user can change its account password, it can login
        using the new password and can make requests using the authentication
        token obtained with the new password.
    :steps:
        1) With an authenticated user, send a post request to /auth/password/
           with the current password and the new password.
        2) Ensure that the user can generate an authentication token with the
           new password and can make requests.
    :expectedresults:
        1) Assert the server returns a 204 response..
        2) Assert the user can login with the new password and can access
           /auth/me/
    """
    user = create_user_account()
    new_password = gen_password()
    client = api.Client()
    payload = {
        'current_password': user['password'],
        'new_password': new_password,
    }

    response = client.post(urls.AUTH_TOKEN_CREATE, user)
    assert response.status_code == 200
    json_response = response.json()
    assert 'auth_token' in json_response
    auth = api.TokenAuth(json_response['auth_token'])

    response = client.post(urls.AUTH_PASSWORD, payload, auth=auth)
    assert response.status_code == 204

    response = client.post(urls.AUTH_TOKEN_DESTROY, {}, auth=auth)
    assert response.status_code == 204

    user['password'] = new_password
    response = client.post(urls.AUTH_TOKEN_CREATE, user, auth=None)
    assert response.status_code == 200
    json_response = response.json()
    assert 'auth_token' in json_response
    auth.token = json_response['auth_token']

    response = client.get(urls.AUTH_ME, auth=auth)
    assert response.status_code == 200
    json_response = response.json()
    assert json_response['username'] == user['username']

    response = client.post(urls.AUTH_TOKEN_DESTROY, {}, auth=auth)
    assert response.status_code == 204
