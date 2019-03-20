"""Test account report summary API.

:caseautomation: automated
:casecomponent: api
:caseimportance: high
:caselevel: integration
:requirement: Cloud Meter
:testtype: functional
:upstream: yes
"""
from collections import namedtuple
from datetime import datetime, timedelta

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


def test_list_accounts_empty(create_user_account):
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
    user = create_user_account()
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


class InstanceTagParams(namedtuple('InstanceTagParams',
                                   'name '
                                   'image_type '
                                   'exp_inst '
                                   'exp_images '
                                   'exp_rhel '
                                   'exp_openshift '
                                   'start '
                                   'end '
                                   'offset ',
                                   )):
    """Configuration parameters for scenarios of instance types and times.

    Parameters:
    name : str
        The name of the parameter, visible in test results for identification
    image_type : str
        An empty string or series of comma-separated tags (rhel or openshift)
    exp_inst : int | None
    exp_images : int | None
    exp_rhel : int | None
    exp_openshift : int | None
        The numbers of instances, images, RHEL, and OpenShift expected to be
        seen
    start : int
    end : int | None
        The start and end times the instance was run. The end time can be None,
        in which case the instance was started and is still running at this
        time.
    offset : int
        An offset for the date range used to fetch data. If 0, fetch the last
        30 days. If -30, fetch (roughly) "last month"

    """


@pytest.mark.parametrize('conf', [
    # No tagged images, started today and 2 weeks ago
    InstanceTagParams('untagged today', '', 1, 1, 0, 0, 0, None, 0),
    InstanceTagParams('untagged 2 weeks', '', 1, 1, 0, 0, 15, None, 0),
    # No tagged images, started and stopped last month
    InstanceTagParams('untagged last month', '', 0, 0, 0, 0, 60, 30, 0),
    # Tagged images started today
    InstanceTagParams('rhel today', 'rhel', 1, 1, 1, 0, 0, None, 0),
    InstanceTagParams('openshift today', 'openshift',
                      1, 1, 0, 1, 0, None, 0),
    InstanceTagParams('windows today', 'windows', 1, 1, 0, 0, 0, None, 0),
    InstanceTagParams('rhel+openshift today', 'rhel,openshift',
                      1, 1, 1, 1, 0, None, 0),
], ids=lambda p: p.name)
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
        start, end, offset = conf[1:]

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


class FutureParam(namedtuple('FutureParam', 'acct_age unknown')):
    """Configuration parameters for future instance scenarios.

    Parameters:
    acct_age : int
        The number of days old the account is
    unknown : bool
        True if we expect null/None responses because instance and image counts
        are unknown for the account in the current date range.

    """


@pytest.mark.parametrize('param', [
    # We assume to know the information if the account existed during any
    # part of the date range
    FutureParam(100, False),
    FutureParam(30, False),
    # But not if it was created after
    FutureParam(29, True),
])
def test_future_instances(param):
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
    acct = inject_aws_cloud_account(user['id'], acct_age=param.acct_age)
    start, end = 0, None

    client = api.Client(authenticate=False)

    events = [start]
    if end:
        events.append(end)
    inject_instance_data(acct['id'], '', events)

    # Set date range for 30 days in the past
    start, end = utils.get_time_range(-30)
    params = {
        'start': start,
        'end': end,
    }
    response = client.get(urls.REPORT_ACCOUNTS, params=params, auth=auth)

    account = response.json()['cloud_account_overviews'][0]
    acct_creation = datetime.today() - timedelta(days=param.acct_age)

    start, end = utils.get_time_range(-30, formatted=False)
    if acct_creation < start:
        info = 'Account created before start of window'
    elif acct_creation > end:
        info = 'Account newer than window'
    else:
        info = 'Account created during window'

    assert account['cloud_account_id'] == acct['aws_account_id']

    if param.unknown:
        exp = None
    else:
        exp = 0
    assert account['images'] == exp, info
    assert account['instances'] == exp, info
    assert account['rhel_instances'] == exp, info
    assert account['openshift_instances'] == exp, info


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
