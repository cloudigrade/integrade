"""Tests for cloud accounts.

:caseautomation: automated
:casecomponent: api
:caseimportance: high
:caselevel: integration
:requirement: Cloud Meter
:testtype: functional
:upstream: yes
"""
import pytest

from integrade import api, config
from integrade.tests import urls
from integrade.tests.utils import (
    get_auth,
    needed_aws_profiles_present,
)
from integrade.utils import uuid4


@pytest.mark.skip(reason='refactor with seed data')
@pytest.mark.serial_only
@pytest.mark.skipif(not needed_aws_profiles_present(2),
                    reason='needs at least 2 aws profile')
def test_create_multiple_cloud_accounts(cloudtrails_to_delete):
    """Ensure cloud accounts can be registered to a user.

    :id: f1db2617-fd15-4270-b9d3-595db001e1e7
    :description: Ensure an user can register multiple cloud accounts as long
        as each ARN is associated with unique cloud accounts.
    :steps: 1) Create a user and authenticate with their password
        2) Send POSTS with each of the cloud account's information to
            'api/v1/account/'
        3) Send a GET to 'api/v1/account/' to get a list of the cloud accounts
    :expectedresults: The server returns a 201 response with the information of
        the created accounts.
    """
    client = api.Client(authenticate=False)
    auth = get_auth()
    cfg = config.get_config()
    accts = []
    for profile in cfg['aws_profiles']:
        arn = profile['arn']
        cloud_account = {
            'account_arn': arn,
            'name': uuid4(),
            'resourcetype': 'AwsAccount'
        }
        create_response = client.post(
            urls.CLOUD_ACCOUNT,
            payload=cloud_account,
            auth=auth
        )
        assert create_response.status_code == 201
        cloudtrails_to_delete.append((
            profile['name'],
            profile['cloudtrail_name']
        ))

        accts.append(create_response.json())

    # list cloud accounts associated with this user
    list_response = client.get(urls.CLOUD_ACCOUNT, auth=auth)
    for acct in accts:
        assert acct in list_response.json()['results']


@pytest.mark.skip(reason='refactor with seed data')
@pytest.mark.serial_only
@pytest.mark.skipif(not needed_aws_profiles_present(2),
                    reason='needs at least 2 aws profile')
def test_create_cloud_account_duplicate_names_different_users(
    cloudtrails_to_delete
):
    """Ensure cloud accounts can be registered to a user.

    :id: 7bf483b7-f0d0-40db-9c18-396dc4a58792
    :description: Ensure an user can register a cloud account by specifying
        the role ARN.
    :steps: 1) Create a user and authenticate with their password
        2) Send a POST with the cloud account information to 'api/v1/account/'
        3) Send a GET to 'api/v1/account/' to get a list of the cloud accounts
        4) Attempt to create a duplicate and expect it to be rejected
        5) Attempt to delete the account and expect to be rejected
    :expectedresults:
        1) The server returns a 201 response with the information
            of the created account.
        2) The account cannot be duplicated, and attempts to do so receive a
            400 status code.
        3) The account cannot be deleted and attempts to do so receive a 405
            response.
    """
    # TODO: refactor inject_aws_cloud_account to use seed data
    user = ''  # create_user_account()
    auth = get_auth(user)
    client = api.Client(authenticate=False, response_handler=api.echo_handler)
    cfg = config.get_config()
    aws_profile = cfg['aws_profiles'][0]
    # TODO: refactor inject_aws_cloud_account to use seed data
    profile_name = ''  # aws_profile['name']
    # inject_aws_cloud_account(user['id'], name=profile_name)

    # Now try to reuse the name
    auth = get_auth()
    aws_profile = cfg['aws_profiles'][1]
    acct_arn = aws_profile['arn']
    cloud_account = {
        'account_arn': acct_arn,
        'name': profile_name,
        'resourcetype': 'AwsAccount'
    }
    create_response = client.post(
        urls.CLOUD_ACCOUNT,
        payload=cloud_account,
        auth=auth
    )
    assert create_response.status_code == 201, create_response.json()
