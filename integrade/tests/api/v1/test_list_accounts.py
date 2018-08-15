"""Test account report summary API.

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
from integrade.injector import (
    inject_aws_cloud_account,
    inject_instance_data,
)
from integrade.tests import (
    urls,
    utils,
)


def test_list_accounts_empty():
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
    """
    user = utils.create_user_account()
    auth = utils.get_auth(user)
    acct = inject_aws_cloud_account(user['id'])
    client = api.Client(authenticate=False)

    start, end = utils.get_time_range()
    params = {
        'start': start,
        'end': end,
    }
    response = client.get(urls.REPORT_ACCOUNTS, params=params, auth=auth)

    account = response.json()['cloud_account_overviews'][0]

    assert account['cloud_account_id'] == acct['aws_account_id']
    assert account['images'] == 0, repr(account)
    assert account['instances'] == 0, repr(account)
    assert account['rhel_instances'] == 0, repr(account)
    assert account['openshift_instances'] == 0, repr(account)


def test_past_without_instances():
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
    user = utils.create_user_account()
    auth = utils.get_auth(user)
    acct = inject_aws_cloud_account(user['id'])
    client = api.Client(authenticate=False)

    start, end = utils.get_time_range(-30)
    params = {
        'start': start,
        'end': end,
    }
    response = client.get(urls.REPORT_ACCOUNTS, params=params, auth=auth)

    account = response.json()['cloud_account_overviews'][0]

    assert account['cloud_account_id'] == acct['aws_account_id']
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
def test_list_account_tagging(conf):
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
    user = utils.create_user_account()
    auth = utils.get_auth(user)
    acct = inject_aws_cloud_account(user['id'])
    image_type, exp_inst, exp_images, exp_rhel, exp_openshift, \
        start, end, offset = conf

    client = api.Client(authenticate=False)

    events = [start]
    if end:
        events.append(end)
    inject_instance_data(acct['id'], image_type, events)

    start, end = utils.get_time_range(offset)
    params = {
        'start': start,
        'end': end,
    }
    response = client.get(urls.REPORT_ACCOUNTS, params=params, auth=auth)

    account = response.json()['cloud_account_overviews'][0]

    assert account['cloud_account_id'] == acct['aws_account_id']
    assert account['images'] == exp_images, repr(account)
    assert account['instances'] == exp_inst, repr(account)
    assert account['rhel_instances'] == exp_rhel, repr(account)
    assert account['openshift_instances'] == exp_openshift, repr(account)


@pytest.mark.parametrize('impersonate', (False, True))
def test_list_account_while_impersonating(impersonate):
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
    user = utils.create_user_account()
    auth = utils.get_auth(user)
    acct = inject_aws_cloud_account(user['id'])
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
    inject_instance_data(acct['id'], image_type, events)

    start, end = utils.get_time_range(offset)
    params = {
        'start': start,
        'end': end,
    }
    if impersonate:
        params['user_id'] = user['id']
    response = client.get(urls.REPORT_ACCOUNTS, params=params, auth=auth)

    account = response.json()['cloud_account_overviews'][0]

    assert account['cloud_account_id'] == acct['aws_account_id']
    assert account['images'] == exp_images, repr(account)
    assert account['instances'] == exp_inst, repr(account)
    assert account['rhel_instances'] == exp_rhel, repr(account)
    assert account['openshift_instances'] == exp_openshift, repr(account)


def test_list_account_with_multiple():
    """Test that a user with multiple accounts can list all.

    :id: 1f16a664-a4ea-410e-9ff8-0a6e42cb4df2
    :description: Test that the same assertions can be made for fetching data
        with just one account works with multiple.
    :steps:
        1) Add a cloud account
        2) Insert instance, image, and event data
        3) GET from the account report endpoint as regular user
    :expectedresults:
        - The instance, image, RHEL, and Openshift counts match the expectation
    """
    user = utils.create_user_account()
    auth = utils.get_auth(user)
    acct = inject_aws_cloud_account(user['id'])
    image_type = 'rhel'
    exp_inst = 1
    exp_images = 1
    exp_rhel = 1
    exp_openshift = 0
    time = 0
    offset = 0

    acct2 = inject_aws_cloud_account(user['id'])

    client = api.Client(authenticate=False)

    inject_instance_data(acct['id'], image_type, [time])

    start, end = utils.get_time_range(offset)
    params = {
        'start': start,
        'end': end,
    }
    response = client.get(urls.REPORT_ACCOUNTS, params=params, auth=auth)

    accounts = response.json()['cloud_account_overviews']
    account = accounts[0]
    account2 = accounts[1]

    assert account['cloud_account_id'] == acct['aws_account_id']
    assert account2['cloud_account_id'] == acct2['aws_account_id']
    assert account['images'] == exp_images, repr(account)
    assert account['instances'] == exp_inst, repr(account)
    assert account['rhel_instances'] == exp_rhel, repr(account)
    assert account['openshift_instances'] == exp_openshift, repr(account)


def test_multiple_runs_counted_once():
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
    user = utils.create_user_account()
    auth = utils.get_auth(user)
    acct = inject_aws_cloud_account(user['id'])
    image_type = ''
    exp_inst = 1
    exp_images = 1
    exp_rhel = 0
    exp_openshift = 0

    client = api.Client(authenticate=False)

    start, end = utils.get_time_range()
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
    inject_instance_data(acct['id'], image_type, events)

    response = client.get(urls.REPORT_ACCOUNTS, params=params, auth=auth)

    account = response.json()['cloud_account_overviews'][0]

    assert account['cloud_account_id'] == acct['aws_account_id']
    assert account['images'] == exp_images, repr(account)
    assert account['instances'] == exp_inst, repr(account)
    assert account['rhel_instances'] == exp_rhel, repr(account)
    assert account['openshift_instances'] == exp_openshift, repr(account)
