"""Tests for cloud accounts.

:caseautomation: automated
:casecomponent: api
:caseimportance: high
:caselevel: integration
:requirement: Cloud Meter
:testtype: functional
:upstream: yes
"""
import logging
import operator

import pytest

from integrade import api, config
from integrade.tests.utils import (
    aws_utils, is_on_local_network
)
from integrade.utils import (
    uuid4,
)

logger = logging.getLogger(__name__)


def fetch_api_accounts():
    """Return account data for available accounts."""
    client = api.ClientV2()
    response = client.request('get', 'accounts/')
    assert response.status_code == 200, \
        'Could not retrieve any account information' \
        ' (check credentials?)'
    accounts = response.json()['data']
    return accounts


@pytest.fixture(params=[config.get_config()['aws_profiles'][0]],
                ids=operator.itemgetter('name'), scope='module')
def aws_profile(request):
    """Provide the aws profile to use to test."""
    return request.param


@pytest.fixture(autouse=True)
def delete_preexisting_accounts(aws_profile):
    """Delete any pre-existing accounts to start fresh.

    In case something went wrong last time this test ran,
    check to be sure that the account doesn't exist and delete
    it if it does.
    TODO: move this to an 'addfinalizer' to delete accounts
    """
    arn = aws_profile['arn']
    accounts = fetch_api_accounts()
    client = api.ClientV2()
    for acct in accounts:
        if acct['content_object']['account_arn'] == arn:
            account_id = acct['account_id']
            endpoint = f'accounts/{account_id}/'
            client.request('delete', endpoint)


@pytest.mark.skipif(not is_on_local_network(),
                    reason="Can't run outside of local RH network")
def test_create_cloud_account(cloudtrails_to_delete, aws_profile, request):
    """Ensure cloud accounts can be registered to a user.

    :id: bb8fa2a4-7ff7-43e6-affb-7a2dedaaab74
    :description: Ensure a user can create a cloud account.
    :steps: 1) Log in as a user.
    2) Send POST with the cloud account's information to
        'api/v2/account/'
    3) Send a GET to 'api/v2/account/' to get a list of the cloud accounts
    4) Run an instance in that account
    5) Check that Cloudigrade and AWS both show same instance_id
    6) Delete account
    7) Check instance in AWS
    :expectedresults: The server returns a 201 response with the information
    of the created account. Cloudigrade and AWS both show same instance_id.
    Delete account response returns status 204. After deletion, AWS
    instance_id.state is 'terminated'.
    """
    account_id = 0
    arn = aws_profile['arn']
    client = api.ClientV2()
    acct_data_params = {
        'account_arn': arn,
        'name': uuid4(),
        'cloud_type': 'aws',
        }

    # POST
    # Create an account
    add_acct_response = client.request(
        'post', 'accounts/', data=acct_data_params)
    assert add_acct_response.status_code == 201

    # Check AWS permissions
    acct_details = add_acct_response.json()
    permission = acct_details['content_object']['account_arn']
    assert 'allow-dev11-cloudigrade-metering' in permission

    # Start AWS session and cloudtrail client
    session = aws_utils.aws_session('DEV07CUSTOMER')
    env_bucket_name = config.get_config(
        )['openshift_prefix'].strip('c-review-')
    aws_cloudtrails = session.client(
        'cloudtrail').describe_trails()['trailList']
    aws_cloudtrail_found = False
    aws_cloudtrail_arn = ''
    cloudtrails_client = session.client('cloudtrail')

    # Find the cloudtrail for this particular account and check that
    # it's enabled.
    for trail in aws_cloudtrails:
        if env_bucket_name in trail['S3BucketName']:
            aws_cloudtrail_found = True
            aws_cloudtrail_arn = trail['TrailARN']
    assert aws_cloudtrail_found is True
    trail_status = cloudtrails_client.get_trail_status(
        Name=aws_cloudtrail_arn)
    assert trail_status['IsLogging'] is True

    # Find the recently added account so we can delete it
    accounts = fetch_api_accounts()
    for acct in accounts:
        if acct['content_object']['account_arn'] == arn:
            account_id = acct['account_id']

    # DELETE
    # Delete that account
    endpoint = f'accounts/{account_id}/'
    delete_acct_response = client.request('delete', endpoint)
    assert delete_acct_response.status_code == 204
    # Check that deleted account is no longer present in cloudigrade
    accounts = fetch_api_accounts()
    assert account_id not in accounts

    # Check that the cloudtrail has been disabled
    trail_status = cloudtrails_client.get_trail_status(Name=aws_cloudtrail_arn)
    assert trail_status['IsLogging'] is False

    # Cleanup: Remove cloudtrail from AWS
    cloudtrails_to_delete.append((
        aws_profile['name'],
        aws_profile['cloudtrail_name']
    ))
