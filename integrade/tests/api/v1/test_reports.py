"""Tests for reports.

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
from integrade.injector import (
    inject_aws_cloud_account,
    inject_instance_data,
)
from integrade.tests import urls, utils


def usertype(superuser):
    """Generate a test id based on the user type."""
    return 'superuser' if superuser else 'regularuser'


@pytest.mark.parametrize('superuser', (False, True), ids=usertype)
def test_cloud_account_filter_by_name(drop_account_data, superuser):
    """Test that cloud accounts can be filtered by name.

    :id: 5abbfb8d-c447-464a-a980-4c7e8d2fcc80
    :description: Test that regular users and superusers can filter cloud
        accounts by name. Cloudigrade takes the search pattern, split its words
        and then for each word is matched as a substring in the name, any
        account that is matched is returned.
    :steps:
        1) Add three cloud accounts
        2) Insert some instance events for all accounts.
        3) Filter the cloud accounts using a two word long pattern. Each
           pattern's word should match a single account.
        4) Ensure two accounts are returned and assert that their instance
           events are correct.
    :expectedresults:
        Two accounts are returned, one matched by the first word and the other
        by the second word. All instance events should match.
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

    client = api.Client(authenticate=superuser)

    # Make first account have one RHEL instance and image that was running for
    # 3 days
    inject_instance_data(first_account['id'], 'rhel', [5, 2])

    # Make second account have one RHEL and one OpenShift instance and image
    # that was running for 5 days
    inject_instance_data(second_account['id'], 'rhel,openshift', [12, 7])

    # Make third account have one OpenShift instance and image that was running
    # for 10 days
    inject_instance_data(third_account['id'], 'openshift', [13, 3])

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
