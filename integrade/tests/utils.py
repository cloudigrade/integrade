"""Utilities functions for tests."""
import copy
from datetime import datetime, time, timedelta
from multiprocessing import Pool

from integrade import api, config, injector
from integrade.tests import aws_utils, urls
from integrade.utils import gen_password, uuid4


_SENTINEL = object()


def create_cloud_account(auth, n, cloudtrails_to_delete=None, name=_SENTINEL):
    """Create a cloud account based on configured AWS customer info."""
    client = api.Client(authenticate=False)
    cfg = config.get_config()
    aws_profile = cfg['aws_profiles'][n]
    acct_arn = aws_profile['arn']
    cloud_account = {
        'account_arn': acct_arn,
        'name': uuid4() if name is _SENTINEL else name,
        'resourcetype': 'AwsAccount'
    }
    create_response = client.post(
        urls.CLOUD_ACCOUNT,
        payload=cloud_account,
        auth=auth
    )
    assert create_response.status_code == 201
    injector.clear_images(create_response.json()['id'])

    if isinstance(cloudtrails_to_delete, list):
        cloudtrails_to_delete.append(
            (aws_profile['name'], aws_profile['cloudtrail_name'])
        )
    return create_response.json()


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


def delete_cloudtrails(cloudtrails_to_delete=None):
    """Delete cloudtrails.

    The cloudtrails_to_delete param must be a list of tuples of (aws_profile,
    cloudtrail_name).
    """
    if cloudtrails_to_delete:
        with Pool() as p:
            p.map(
                aws_utils.delete_cloudtrail, cloudtrails_to_delete)


def drop_account_data():
    """Drop all account data from the cloudigrade's database."""
    injector.run_remote_python("""
    from account.models import Account
    Account.objects.all().delete()
    """)


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


def get_time_range(offset=0):
    """Create start/end time for parameters to account report API."""
    fmt = '%Y-%m-%dT%H:%MZ'
    tomorrow = datetime.now().date() + timedelta(days=1 + offset)
    end = datetime.combine(tomorrow, time(4, 0, 0))
    start = end - timedelta(days=30)
    return start.strftime(fmt), end.strftime(fmt)
