"""Utilities functions for API tests."""
import copy

from integrade import api
from integrade.tests.api.v1 import urls
from integrade.utils import gen_password, uuid4


def create_user_account(user=None):
    """Create a new user account.

    :param user: A dictionary with the paylod to send to the API.
    """
    if user is None:
        user = {
            'email': '',
            'password': gen_password(),
            'username': uuid4(),
        }
    else:
        user = copy.deepcopy(user)
    response = api.Client().post(urls.AUTH_USERS_CREATE, user)
    assert response.status_code == 201
    json_response = response.json()
    assert 'id' in json_response
    assert json_response['username'] == user['username']
    assert json_response['email'] == user['email']
    user.update(response.json())
    return user
