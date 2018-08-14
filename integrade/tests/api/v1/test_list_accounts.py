"""Test account report summary API.

:caseautomation: automated
:casecomponent: api
:caseimportance: high
:caselevel: integration
:requirement: Cloud Meter
:testtype: functional
:upstream: yes
"""
from datetime import datetime, time, timedelta

import pytest

from integrade import api, config
from integrade.injector import (
    clear_images,
    direct_count_images,
    inject_instance_data,
)
from integrade.tests import urls
from integrade.tests.utils import get_auth
from integrade.utils import uuid4


def get_time_range(offset=0):
    """Create start/end time for parameters to account report API."""
    fmt = '%Y-%m-%dT%H:%MZ'
    tomorrow = datetime.now().date() + timedelta(days=1 + offset)
    end = datetime.combine(tomorrow, time(4, 0, 0))
    start = end - timedelta(days=30)
    return start.strftime(fmt), end.strftime(fmt)


def create_cloud_account(auth, n, name=None):
    """Create a cloud account based on configured AWS customer info."""
    client = api.Client(authenticate=False)
    cfg = config.get_config()
    aws_profile = cfg['aws_profiles'][n]
    acct_arn = aws_profile['arn']
    cloud_account = {
        'account_arn': acct_arn,
        'name': name or uuid4(),
        'resourcetype': 'AwsAccount'
    }
    create_response = client.post(
        urls.CLOUD_ACCOUNT,
        payload=cloud_account,
        auth=auth
    )
    assert create_response.status_code == 201
    clear_images(create_response.json()['id'])
    return create_response.json()


@pytest.fixture
def cloud_account(drop_account_data, cloudtrails_to_delete):
    """Create a cloud account, return the auth object and account details."""
    assert direct_count_images() == 0
    auth = get_auth()
    create_response = create_cloud_account(auth, 0)
    return (auth, create_response)


def test_list_accounts_empty(cloud_account):
    """Test accounts without any instance or image history have empty summaries.

    :id: 2a152ef6-fcd8-491c-b3cc-bda81699453a
    :description: Test that an account without any instances or images shows up
        in the results with 0 counts.
    :steps:
        1) Add a cloud account
        2) GET from the account report endpoint
    :expectedresults:
        - The account is in the response and matches the created account
        - Instances, images, RHEL, and Openshift all have 0 counts

    TEST CHANGE
    """
    auth, cloud_account = cloud_account
    client = api.Client(authenticate=False)

    start, end = get_time_range()
    params = {
        'start': start,
        'end': end,
    }
    response = client.get(urls.REPORT_ACCOUNTS, params=params, auth=auth)

    account = response.json()['cloud_account_overviews'][0]

    assert account['cloud_account_id'] == cloud_account['aws_account_id']
    assert account['images'] == 0, repr(account)
    assert account['instances'] == 0, repr(account)
    assert account['rhel_instances'] == 0, repr(account)
    assert account['openshift_instances'] == 0, repr(account)


def test_past_without_instances(cloud_account):
    """Test accounts with instances only after the filter period.

    :id: 72aaa6e2-2c60-4e71-bb47-3644bd6beb71
    :description: Test that an account with instances that were created prior
        to the current report end date.
    :steps:
        1) Add a cloud account
        2) Inject instance data for today
        3) GET from the account report endpoint for 30 days ago
    :expectedresults:
        - The account is in the response and matches the created account
        - Instances, images, RHEL, and Openshift all have None counts
    """
    auth, cloud_account = cloud_account
    client = api.Client(authenticate=False)

    start, end = get_time_range(-30)
    params = {
        'start': start,
        'end': end,
    }
    response = client.get(urls.REPORT_ACCOUNTS, params=params, auth=auth)

    account = response.json()['cloud_account_overviews'][0]

    assert account['cloud_account_id'] == cloud_account['aws_account_id']
    assert account['images'] is None, repr(account)
    assert account['instances'] is None, repr(account)
    assert account['rhel_instances'] is None, repr(account)
    assert account['openshift_instances'] is None, repr(account)


@pytest.mark.parametrize('conf', [
    # No tagged images, started today and 2 weeks ago
    ('', 1, 1, 0, 0, 0, None, 0),
    ('', 1, 1, 0, 0, 15, None, 0),
    # No tagged images, started and stopped last month
    ('', 0, 0, 0, 0, 60, 30, 0),
    # Tagged images started today
    ('rhel', 1, 1, 1, 0, 0, None, 0),
    ('openshift', 1, 1, 0, 1, 0, None, 0),
    ('windows', 1, 1, 0, 0, 0, None, 0),
    ('rhel,openshift', 1, 1, 1, 1, 0, None, 0),
    # Instances created after window
    ('', None, None, None, None, 0, None, -30),
])
def test_list_account_tagging(cloud_account, conf):
    """Test instance events generate usage summary results for correct tags.

    :id: f3c84697-a40c-40d9-846d-117e2647e9d3
    :description: Test combinations of image tags, start/end events, and the
        resulting counts from the summary report API.
    :steps:
        1) Add a cloud account
        2) Insert instance, image, and event data
        3) GET from the account report endpoint
    :expectedresults:
        - The instance, image, RHEL, and Openshift counts match the expectation
    """
    auth, cloud_account = cloud_account
    image_type, exp_inst, exp_images, exp_rhel, exp_openshift, \
        start, end, offset = conf

    client = api.Client(authenticate=False)

    events = [start]
    if end:
        events.append(end)
    inject_instance_data(cloud_account['id'], image_type, events)

    start, end = get_time_range(offset)
    params = {
        'start': start,
        'end': end,
    }
    response = client.get(urls.REPORT_ACCOUNTS, params=params, auth=auth)

    account = response.json()['cloud_account_overviews'][0]

    assert cloud_account['aws_account_id'] == account['cloud_account_id']
    assert account['images'] == exp_images, repr(account)
    assert account['instances'] == exp_inst, repr(account)
    assert account['rhel_instances'] == exp_rhel, repr(account)
    assert account['openshift_instances'] == exp_openshift, repr(account)


@pytest.mark.parametrize('impersonate', (False, True))
def test_list_account_while_impersonating(cloud_account, impersonate):
    """Test account data fetched via impersonating a user as a superuser.

    :id: 5f99c7ec-a4d3-4040-868f-9340015e4c9c
    :description: Test that the same assertions can be made for fetching data
        as a regular user and fetching data impersonating that same user
    :steps:
        1) Add a cloud account
        2) Insert instance, image, and event data
        3) GET from the account report endpoint as regular user
        3) GET from the account report endpoint as super user impersonating
    :expectedresults:
        - The instance, image, RHEL, and Openshift counts match the expectation
    """
    auth, cloud_account = cloud_account
    image_type = 'rhel'
    exp_inst = 1
    exp_images = 1
    exp_rhel = 1
    exp_openshift = 0
    start = 0
    end = None
    offset = 0

    # authenticate (as superuser) if we are impersonating
    client = api.Client(authenticate=impersonate)

    events = [start]
    if end:
        events.append(end)
    inject_instance_data(cloud_account['id'], image_type, events)

    start, end = get_time_range(offset)
    params = {
        'start': start,
        'end': end,
    }
    if impersonate:
        params['user_id'] = cloud_account['user_id']
    response = client.get(urls.REPORT_ACCOUNTS, params=params, auth=auth)

    account = response.json()['cloud_account_overviews'][0]

    assert cloud_account['aws_account_id'] == account['cloud_account_id']
    assert account['images'] == exp_images, repr(account)
    assert account['instances'] == exp_inst, repr(account)
    assert account['rhel_instances'] == exp_rhel, repr(account)
    assert account['openshift_instances'] == exp_openshift, repr(account)


@pytest.mark.skipif(len(config.get_config()[
    'aws_profiles']) < 2, reason='needs at least 2 aws profiles')
def test_list_account_with_multiple(cloud_account):
    """Test account data fetched via impersonating a user as a superuser.

    :id: 1f16a664-a4ea-410e-9ff8-0a6e42cb4df2
    :description: Test that the same assertions can be made for fetching data
        as a regular user and fetching data impersonating that same user
    :steps:
        1) Add a cloud account
        2) Insert instance, image, and event data
        3) GET from the account report endpoint as regular user
        3) GET from the account report endpoint as super user impersonating
    :expectedresults:
        - The instance, image, RHEL, and Openshift counts match the expectation
    """
    auth, cloud_account = cloud_account
    image_type = 'rhel'
    exp_inst = 1
    exp_images = 1
    exp_rhel = 1
    exp_openshift = 0
    time = 0
    offset = 0

    second_account = create_cloud_account(auth, 1)

    client = api.Client(authenticate=False)

    inject_instance_data(cloud_account['id'], image_type, [time])

    start, end = get_time_range(offset)
    params = {
        'start': start,
        'end': end,
    }
    response = client.get(urls.REPORT_ACCOUNTS, params=params, auth=auth)

    accounts = response.json()['cloud_account_overviews']
    account = accounts[0]
    account2 = accounts[1]

    assert second_account['aws_account_id'] == account2['cloud_account_id']
    assert cloud_account['aws_account_id'] == account['cloud_account_id']
    assert account['images'] == exp_images, repr(account)
    assert account['instances'] == exp_inst, repr(account)
    assert account['rhel_instances'] == exp_rhel, repr(account)
    assert account['openshift_instances'] == exp_openshift, repr(account)


def test_multiple_runs_counted_once(cloud_account):
    """Test instances being run a different times in the same period count once.

    :id: 0e8d0475-54d9-43af-9c2b-23f84865c6b4
    :description: Within any single period of reporting an instance which has
        been started and stopped multiple times still counts just once.
    :steps:
        1) Add a cloud account
        2) Insert event data with more than one start and stop in the last 30
           day period
        3) GET from the account report endpoint
    :expectedresults:
        - The instance and image should only be counted once
    """
    auth, cloud_account = cloud_account
    image_type = ''
    exp_inst = 1
    exp_images = 1
    exp_rhel = 0
    exp_openshift = 0

    client = api.Client(authenticate=False)

    start, end = get_time_range()
    params = {
        'start': start,
        'end': end,
    }

    events = [
        20,
        15,
        10,
        5,
    ]
    inject_instance_data(cloud_account['id'], image_type, events)

    response = client.get(urls.REPORT_ACCOUNTS, params=params, auth=auth)

    account = response.json()['cloud_account_overviews'][0]

    assert cloud_account['aws_account_id'] == account['cloud_account_id']
    assert account['images'] == exp_images, repr(account)
    assert account['instances'] == exp_inst, repr(account)
    assert account['rhel_instances'] == exp_rhel, repr(account)
    assert account['openshift_instances'] == exp_openshift, repr(account)
