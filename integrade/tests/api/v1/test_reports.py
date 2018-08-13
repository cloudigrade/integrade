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

from integrade import api, config
from integrade.injector import inject_instance_data
from integrade.tests import urls
from integrade.tests.utils import (
    create_cloud_account,
    get_auth,
    get_time_range,
)


def usertype(superuser):
    """Generate a test id based on the user type."""
    return 'superuser' if superuser else 'regularuser'


@pytest.mark.skipif(
    len(config.get_config()['aws_profiles']) < 3,
    reason='needs at least 3 aws profiles',
)
@pytest.mark.parametrize('superuser', (False, True), ids=usertype)
def test_cloud_account_filter_by_name(
        cloudtrails_to_delete, drop_account_data, superuser):
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
    auth = get_auth()
    cfg = config.get_config()
    first_account = create_cloud_account(
        auth, 0, name='greatest account ever')
    cloudtrails_to_delete.append([
        cfg['aws_profiles'][0]['name'],
        cfg['aws_profiles'][0]['cloudtrail_name']
    ])
    second_account = create_cloud_account(
        auth, 1, name='just another account')
    cloudtrails_to_delete.append([
        cfg['aws_profiles'][1]['name'],
        cfg['aws_profiles'][1]['cloudtrail_name']
    ])
    third_account = create_cloud_account(
        auth, 2, name='my awesome account')
    cloudtrails_to_delete.append([
        cfg['aws_profiles'][2]['name'],
        cfg['aws_profiles'][2]['cloudtrail_name']
    ])

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

    start, end = get_time_range()
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
        key=operator.itemgetter('cloud_account_id')
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
