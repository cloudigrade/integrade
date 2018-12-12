"""Utilities functions for tests."""
import calendar
import copy
from datetime import datetime, time, timedelta, timezone
from multiprocessing import Pool

from integrade import api, config, injector
from integrade.tests import aws_utils, urls
from integrade.utils import gen_password, uuid4


_SENTINEL = object()


def needed_aws_profiles_present(num_profiles=1):
    """Return True if the number of profiles indicated are present.

    See the README for how aws profiles for customers are defined.
    """
    return False if not config.get_config().get('aws_profiles') else len(
        config.get_config().get('aws_profiles', [])) > num_profiles


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
        email = f'{uuid4()}@example.com'
        user = create_user_account({
            'email': email,
            'password': gen_password(),
            'username': email,
        })
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
    from account.models import AwsMachineImage, AwsMachineImageCopy
    # Must delete AwsMachineImageCopy first because they reference
    # AwsMachineImage objects
    AwsMachineImageCopy.objects.all().delete()
    AwsMachineImage.objects.all().delete()
    Account.objects.all().delete()
    """)


def drop_image_data():
    """Drop all image data from the cloudigrade's database."""
    injector.run_remote_python("""
    from account.models import AwsMachineImage, AwsMachineImageCopy
    # Must delete AwsMachineImageCopy first because they reference
    # AwsMachineImage objects
    AwsMachineImageCopy.objects.all().delete()
    AwsMachineImage.objects.all().delete()
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
        email = f'{uuid4()}@example.com'
        password = gen_password()
        user = create_user_account({
            'email': email,
            'password': password,
            'username': email,
        })
    print(f'USER {email} {password}')
    client = api.Client(authenticate=False)
    response = client.post(urls.AUTH_TOKEN_CREATE, user)
    assert response.status_code == 200
    json_response = response.json()
    assert 'auth_token' in json_response
    return api.TokenAuth(json_response['auth_token'])


def get_time_range(offset=0, formatted=True):
    """Create start/end time for parameters to account report API."""
    fmt = '%Y-%m-%dT%H:%MZ'
    tomorrow = datetime.now().date() + timedelta(days=1 + offset)
    end = datetime.combine(tomorrow, time(4, 0, 0))
    start = end - timedelta(days=30)
    if formatted:
        return start.strftime(fmt), end.strftime(fmt)
    else:
        return start, end


def utc_dt(*args, **kwargs):
    """Wrap datetime construction to force result to UTC.

    :returns: datetime.datetime instance with its timezone set to UTC.
    """
    return datetime(*args, **kwargs).replace(tzinfo=timezone.utc)


def utc_now(*args, **kwargs):
    """Return the datetime.now forcing result to UTC.

    :returns: datetime.datetime instance with its timezone set to UTC.
    """
    return datetime.now().replace(tzinfo=timezone.utc)


def days_in_month(year, month):
    """Return the number of days on a given month.

    :returns: An integer with the number of days a given month has.
    """
    return calendar.monthrange(year, month)[1]
