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

import pytest

import requests

from integrade import config
from integrade.tests.constants import (
    TEST_URL
)
from integrade.tests.utils import (
    is_on_local_network,
)
from integrade.utils import (
    uuid4,
)

logger = logging.getLogger(__name__)


def fetch_accounts():
    """Return account data for available accounts."""
    creds = ('mpierce@redhat.com', 'redhat')
    qa_branch = '554-create-delete-v2'
    accounts_url = f'{TEST_URL}accounts/'
    test_headers = {
        'X-4Scale-Env': 'ci',
        'X-4Scale-Branch': qa_branch,
    }
    accounts = requests.get(
        accounts_url,
        auth=creds,
        headers=test_headers,
        verify=False,
    ).json()['data']
    return accounts


@pytest.mark.skipif(not is_on_local_network(),
                    reason="Can't run outside of local RH network")
def test_create_cloud_account(cloudtrails_to_delete):
    """Ensure cloud accounts can be registered to a user.

    :id: bb8fa2a4-7ff7-43e6-affb-7a2dedaaab74
    :description: Ensure a user can create a cloud account.
    :steps: 1) Log in as a user.
    2) Send POST with the cloud account's information to
        'api/v2/account/'
    3) Sent a GET to 'api/v2/account/' to get a list of the cloud accounts
    :expectedresults: The server returns a 201 response with the information
    of the created account.
    """
    accts = []
    account_id = 0
    creds = ('mpierce@redhat.com', 'redhat')
    qa_branch = '554-create-delete-v2'
    accounts_url = f'{TEST_URL}accounts/'
    cfg = config.get_config()
    profile = cfg['aws_profiles'][0]
    arn = profile['arn']
    post_params = {
        'account_arn': arn,
        'name': uuid4(),
        'cloud_type': 'aws',
        }
    test_headers = {
        'X-4Scale-Env': 'ci',
        'X-4Scale-Branch': qa_branch,
        }
    # In case something went wrong last time this test ran,
    # check to be sure that the account doesn't exist and delete
    # it if it does.
    accounts = fetch_accounts()
    for acct in accounts:
        if acct['content_object']['account_arn'] == arn:
            account_id = acct['account_id']
            account_url = f'{TEST_URL}accounts/{account_id}/'
            delete_acct_response = requests.delete(
                account_url,
                auth=creds,
                headers=test_headers,
                verify=False,
            )

    # POST
    # Create an account
    add_acct_response = requests.post(
        accounts_url,
        auth=creds,
        headers=test_headers,
        verify=False,
        data=post_params,
    )
    assert add_acct_response.status_code == 201

    cloudtrails_to_delete.append((
        profile['name'],
        profile['cloudtrail_name']
    ))
    # Find the recently added account so we can delete it
    accounts = fetch_accounts()
    for acct in accounts:
        if acct['content_object']['account_arn'] == arn:
            account_id = acct['account_id']

    # DELETE
    # Delete that account
    account_url = f'{TEST_URL}accounts/{account_id}/'
    delete_acct_response = requests.delete(
        account_url,
        auth=creds,
        headers=test_headers,
        verify=False,
    )
    assert delete_acct_response.status_code == 204
    accts.append(add_acct_response.json())
