"""Utilities functions for tests."""
import copy

from integrade import api, injector
from integrade.tests import urls
from integrade.utils import gen_password, uuid4


def create_user_account(user=None):
    """Create a new user account.

    :param user: A dictionary with the arguments to be passed to the Django's
        create_user helper function.
    """
    if user is None:
        user = {
            'email': '',
            'password': gen_password(),
            'username': uuid4(),
        }
    else:
        user = copy.deepcopy(user)

    user['id'] = injector.run_remote_python("""
        from django.contrib.auth.models import User
        return User.objects.create_user(**user).id
    """, **locals())

    return user


def get_auth(user=None):
    """Get authentication for given user to use with requests.

    For example::
        usr = create_user_account({
            'email': '',
            'password': gen_password(),
            'username': uuid4(),
        })
        auth = get_auth(username, pwd)
        client = api.Client(authenticate=False)
        client.get(urls.AUTH_ME, auth=auth)

    If no user is provided, a new user is created.
    This is useful when you need to make authenticated requests as a regular
    user, but never need to use the user information for anything else.

    Example::

        from integrade.tests import urls
        client = api.client(authenticate=False)
        auth1 = get_user_and_auth()
        client.get(urls.CLOUD_ACCOUNT, auth=auth1)

    :returns: instance of api.TokenAuth
    """
    if not user:
        user = create_user_account({
            'email': '',
            'password': gen_password(),
            'username': uuid4(),
        })
    client = api.Client(authenticate=False)
    response = client.post(urls.AUTH_TOKEN_CREATE, user)
    assert response.status_code == 200
    json_response = response.json()
    assert 'auth_token' in json_response
    return api.TokenAuth(json_response['auth_token'])
