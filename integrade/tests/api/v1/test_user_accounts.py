"""Tests for user accounts.

:caseautomation: automated
:casecomponent: api
:caseimportance: high
:caselevel: integration
:requirement: Cloud Meter
:testtype: functional
:upstream: yes
"""
from integrade import api
from integrade.config import get_config
from integrade.tests.api.v1 import urls
from integrade.tests.api.v1.utils import create_user_account, get_auth
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


def test_user_list(drop_account_data):
    """Super users can request lists of created user accounts.

    :id: 52567e92-2b6a-43b0-bdc0-5a347b9dd4bc
    :description: Super users, and only super users, are able to request a user
        list.
    :steps:
        1) Authenticate with a super user account and request the user list
            end point contains yourself and a created non-super user account.
        2) Authenticate with a non-super user account and request the user list
            to verify a 4xx error
    :expectedresults: The super user can get the list, but not the regular user
        account.
    """
    client = api.Client()
    response = client.get(urls.USER_LIST)
    pre_user_list = response.json()
    usernames = [user['username'] for user in pre_user_list]
    assert get_config()['super_user_name'] in usernames

    new_user = create_user_account()
    response = client.get(urls.USER_LIST)
    new_user_list = [user for user in response.json()
                     if user not in pre_user_list]
    new_user_ids = [user['id'] for user in new_user_list]

    assert new_user['id'] in new_user_ids

    auth = get_auth(new_user)
    client = api.Client(authenticate=False, response_handler=api.echo_handler)
    response = client.get(urls.USER_LIST, auth=auth)
    assert response.status_code == 403
