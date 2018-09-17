"""Tests for accounts reports.

:caseautomation: automated
:casecomponent: api
:caseimportance: high
:caselevel: integration
:requirement: Cloud Meter
:testtype: functional
:upstream: yes
"""
import operator

import pytest

from integrade import api
from integrade.injector import inject_aws_cloud_account, inject_instance_data
from integrade.tests import urls, utils


def usertype(superuser):
    """Generate a test id based on the user type."""
    return 'superuser' if superuser else 'regularuser'


@pytest.fixture(scope='module')
def accounts_report_data():
    """Create cloud account data for the accounts report tests.

    Create three cloud accounts and create some instance data.
    """
    user = utils.create_user_account()
    auth = utils.get_auth(user)
    first_account = inject_aws_cloud_account(
        user['id'],
        name='a greatest account ever',
    )
    second_account = inject_aws_cloud_account(
        user['id'],
        name='b just another account',
    )
    third_account = inject_aws_cloud_account(
        user['id'],
        name='c my awesome account',
    )

    # Make first account have one RHEL instance and image that was running for
    # 3 days
    inject_instance_data(first_account['id'], 'rhel', [5, 2])

    # Make second account have one RHEL and one OpenShift instance and image
    # that was running for 5 days
    inject_instance_data(second_account['id'], 'rhel,openshift', [12, 7])

    # Make third account have one OpenShift instance and image that was running
    # for 10 days
    inject_instance_data(third_account['id'], 'openshift', [13, 3])

    return auth, first_account, second_account, third_account


@pytest.mark.parametrize('superuser', (False, True), ids=usertype)
def test_filter_by_account_id(accounts_report_data, superuser):
    """Test that cloud accounts report can be filtered by account ID.

    :id: 8de488c4-2550-4d51-9d25-a7c4355fe6f4
    :description: Test that regular users and superusers can filter cloud
        accounts by account ID.
    :steps:
        1) Add three cloud accounts
        2) Insert some instance events for all accounts.
        3) Filter the cloud accounts by providing the account_id of one of the
           three accounts ID
        4) Ensure a single account is returned and assert that their instance
           events are correct.
    :expectedresults:
        One account matched by its account ID is returned. All instance events
        should match.
    """
    auth, first_account, second_account, third_account = accounts_report_data
    client = api.Client(authenticate=superuser)
    start, end = utils.get_time_range()
    params = {
        'account_id': second_account['id'],
        'end': end,
        'start': start,
    }
    if superuser:
        params['user_id'] = first_account['user_id']
    response = client.get(urls.REPORT_ACCOUNTS, params=params, auth=auth)

    cloud_account_overviews = response.json()['cloud_account_overviews']
    assert len(cloud_account_overviews) == 1, cloud_account_overviews
    account = cloud_account_overviews[0]
    assert second_account['aws_account_id'] == account['cloud_account_id']
    assert account['images'] == 1, repr(account)
    assert account['instances'] == 1, repr(account)
    assert account['rhel_instances'] == 1, repr(account)
    assert account['openshift_instances'] == 1, repr(account)


@pytest.mark.parametrize('superuser', (False, True), ids=usertype)
def test_filter_by_name(accounts_report_data, superuser):
    """Test that cloud accounts can be filtered by name.

    :id: 5abbfb8d-c447-464a-a980-4c7e8d2fcc80
    :description: Test that regular users and superusers can filter cloud
        accounts by name. Cloudigrade takes the search pattern, split its words
        and then for each word is matched as a substring in the name, any
        account that is matched is returned.
    :steps:
        1) Add three cloud accounts
        2) Insert some instance events for all accounts.
        3) Filter the cloud accounts using a two words pattern. Each pattern's
           word should match a single account.
        4) Ensure two accounts are returned and assert that their instance
           events are correct.
    :expectedresults:
        Two accounts are returned, one matched by the first word and the other
        by the second word. All instance events should match.
    """
    auth, first_account, second_account, third_account = accounts_report_data
    client = api.Client(authenticate=superuser)
    start, end = utils.get_time_range()
    params = {
        'end': end,
        'name_pattern': 'EaT sOme ToFu',
        'start': start,
    }
    if superuser:
        params['user_id'] = first_account['user_id']
    response = client.get(urls.REPORT_ACCOUNTS, params=params, auth=auth)

    results = sorted(
        response.json()['cloud_account_overviews'],
        key=operator.itemgetter('name')
    )
    assert len(results) == 2, results
    for expected, account in zip((first_account, third_account), results):
        assert expected['aws_account_id'] == account['cloud_account_id']
        assert account['images'] == 1, repr(account)
        assert account['instances'] == 1, repr(account)
        if expected is first_account:
            assert account['rhel_instances'] == 1, repr(account)
            assert account['openshift_instances'] == 0, repr(account)
        else:
            assert account['rhel_instances'] == 0, repr(account)
            assert account['openshift_instances'] == 1, repr(account)


@pytest.mark.parametrize('superuser', (False, True), ids=usertype)
def test_filter_by_account_id_and_name(accounts_report_data, superuser):
    """Test that cloud accounts report can be filtered by account ID and name.

    :id: edacb611-dfec-4d8b-b480-b0c0d901c08e
    :description: Test that regular users and superusers can filter cloud
        accounts by account ID and name. This is not useful since the account
        ID will restrict the list to a single account but, since this is a
        possibility, ensure that an and operation will be done to match both
        account ID and name.
    :steps:
        1) Add three cloud accounts
        2) Insert some instance events for all accounts.
        3) Filter the cloud accounts by providing the account_id and a name
           pattern that does not match the account's name.
        4) Ensure an emptly list is returned since it won't match anything.
        5) Now update the account ID and the name pattern to match both the
           account ID and the name.
        4) Ensure a single account is returned and assert that their instance
           events are correct.
    :expectedresults:
        No result should be returned if both account ID and name pattern don't
        match any account. One result is returned when both account ID and name
        pattern match an account. All instance events should match for the
        matched account.
    """
    auth, first_account, second_account, third_account = accounts_report_data
    client = api.Client(authenticate=superuser)
    start, end = utils.get_time_range()
    params = {
        'end': end,
        'account_id': second_account['id'],
        'name_pattern': 'EaT sOme ToFu',
        'start': start,
    }
    if superuser:
        params['user_id'] = first_account['user_id']

    # No result will be returned since it will try to mach the account ID and
    # the name pattern
    response = client.get(urls.REPORT_ACCOUNTS, params=params, auth=auth)
    cloud_account_overviews = response.json()['cloud_account_overviews']
    assert len(cloud_account_overviews) == 0, cloud_account_overviews

    # Now update the account ID to point to an account that the name pattern
    # will match, it should return a single result.
    params['account_id'] = first_account['id']
    response = client.get(urls.REPORT_ACCOUNTS, params=params, auth=auth)
    cloud_account_overviews = response.json()['cloud_account_overviews']
    assert len(cloud_account_overviews) == 1, cloud_account_overviews
    account = cloud_account_overviews[0]
    assert first_account['aws_account_id'] == account['cloud_account_id']
    assert account['images'] == 1, repr(account)
    assert account['instances'] == 1, repr(account)
    assert account['rhel_instances'] == 1, repr(account)
    assert account['openshift_instances'] == 0, repr(account)
