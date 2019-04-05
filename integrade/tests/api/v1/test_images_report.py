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
from integrade.tests import urls, utils


@pytest.skip(reason='TODO refactor')
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

    # ask for last 30 days
    report_start, report_end = utils.get_time_range()
    params = {
        'start': report_start,
        'end': report_end,
        'account_id': acct['id'],
    }

    response = client.get(urls.REPORT_IMAGES, params=params, auth=auth)
    images = response.json()['images']

    assert images == [], repr(images)

    # No tagged images, started 60 days ago and stopped 45 days ago
    image_type = ''
    instance_start = 60
    instance_end = 45
    events = [instance_start, instance_end]
    inject_instance_data(acct['id'], image_type, events)

    # test that still have no images in report
    response = client.get(urls.REPORT_IMAGES, params=params, auth=auth)
    images = response.json()['images']

    assert images == [], repr(images)
