"""Tests for cloud accounts.

:caseautomation: automated
:casecomponent: api
:caseimportance: high
:caselevel: integration
:requirement: Cloud Meter
:testtype: functional
:upstream: yes
"""

import json
import logging
import time
from datetime import datetime, timedelta

from integrade import api
from integrade.tests.constants import (
    QA_URL,
    SOURCES_URL,
)
from integrade.tests.utils import get_credentials

_logger = logging.getLogger(__name__)


def create_auth_obj_in_sources():
    """Get authentication object from Sources.

    Add a source with AWS credentials. You must have a Source object first.
    Then get the Endpoint object and whth you can create an Authentication
    object. Once this is done, Cloudigrade should notice the authentication
    and from there, create a cloud account for the user to monitor the newly
    triggered activity.
    """
    creds = get_credentials()
    client = api.ClientV2(
        SOURCES_URL,
        auth=creds
    )
    now = datetime.now()
    unique_name = now.strftime('%m_%d_%Y-%H:%M:%S')
    name = f'integrade_test_source_{unique_name}'
    # Get Source object id.
    source_data = json.dumps({'name': name, 'source_type_id': '2'})
    source_r = client.request('post', 'sources', data=source_data)
    source_response = json.loads(source_r.content)
    source_id = source_response['id']
    # Get Endpoint object id.
    endpoint_data = json.dumps({'role': 'aws', 'source_id': source_id})
    endpoint_r = client.request(
        'post', 'endpoints', data=endpoint_data)
    endpoint_response = json.loads(endpoint_r.content)
    endpoint_id = endpoint_response['id']
    # Get Authentication object id. 'aws_username' and 'aws_password' should
    # be from temp/throw-away AWS account. See TODO in
    # 'delete_current_cloud_accounts'.
    aws_username = 'AKIAWMYORTXEGOIMOZNW'
    aws_password = 'PPckD2nxcQk/k/Wf4EIx6iWqT/wTJSzXNtI2FmDM'
    auth_data = json.dumps({'resource_id': endpoint_id,
                            'resource_type': 'Endpoint',
                            'username': aws_username,
                            'password': aws_password})
    auth_r = client.request('post', 'authentications', data=auth_data)
    auth_response = json.loads(auth_r.content)
    auth_id = auth_response['id']
    auth_id_response = client.request('get', f'authentications/{auth_id}')
    auth_id = auth_id_response.json()['id']

    print(f'Source response: {source_response}')
    print(f'Endpoint response: {endpoint_response}')
    print(f'Auth id response: {auth_id_response.text}')
    print(f'Auth id: {auth_id}')


def delete_current_cloud_accounts(arn):
    """Delete current cloud accounts to start fresh.

    Args:
        arn (string): the arn of the temporary AWS account used for this test.
    The AWS account used here needs to be a temporary one because there are
    real username/password combinations being used and Sources is not
    encrypted in any way.
    TODO: Currently, the AWS temporary account is semi-permanent, ie, there is
    nothing in place to create a new one for each run of the tests and then
    destroy it after the test runs. This should be done.
    """
    client = api.ClientV2(
        url=QA_URL,
    )
    keep_deleting = True
    while keep_deleting:
        r_clounts = client.request(
            'get',
            'accounts/',
        )
        clounts_data = r_clounts.json()
        keep_deleting = clounts_data['links']['next'] is not None
        for clount in clounts_data['data']:
            obj_cont = clount['content_object']
            acct_arn = obj_cont['account_arn']
            clount_id = clount['account_id']
            if acct_arn == arn:
                # import ipdb; ipdb.set_trace()
                d_clount = client.request(
                    'delete',
                    f'accounts/{clount_id}/',
                )
                print(f'deleted clount id {clount_id}: '
                      f'request: {d_clount}'
                      f'arn: {arn}')


def wait_for_response_with_timeout(client, params, arn, timeout):
    """Poll cloudigrade to see it recognize 'Sources'-triggered event.

    Args:
        client: An API client (v2)
        params (tuple): First value (string) is the request method and the
            second one (also string) is the endpoint to hit.
        timeout (int): how long (seconds) do we want to wait before giving up.
        Currently in these tests, there won't me many items returned in the
        response, but pagination is included in case there are more than 10.
    """
    start_time = datetime.now()
    method, endpoint = params
    while datetime.now() < start_time+timedelta(seconds=timeout):
        cloudi_response = client.request(f'{method}', f'{endpoint}').json()
        count = cloudi_response['meta']['count']
        if count != 0:
            for response_arn in cloudi_response['data']:
                if response_arn['content_object']['account_arn'] == arn:
                    return response_arn
                else:
                    while cloudi_response['links']['next'] is not None:
                        cloudi_response = client.request(
                            'get', cloudi_response['links']['next']).json()
                        for response_arn in cloudi_response['data']:
                            if response_arn == arn:
                                return response_arn
        time.sleep(3)
    _logger.info(
        f"Cloudigrade didn't notice event {params} before timeout.")


def test_cloudi_create_account():
    """Ensure that Cloudigrade responds appropriately to Sources trigger.

    :id: 8DA8D12F-A6FE-426E-BF87-33DFBE2E65D0
    :description: Ensure that Cloudigrade recognizes when a user initiates
        an event via Sources.
    :steps:
        1) Add a source with AWS credentials.
        2) Watch Cloudigrade to see that a new cloud account with the
        appropriate arn is created.
    :expectedresults:
        1) Account is created in Cloudigrade with a name matching the pattern
        'aws-account-<ACCOUNT_NUMBER_OF_TEMP_AWS_ACCOUNT>'.
        2) Said account has expected arn for same temp account in AWS.
    """
    client = api.ClientV2()
    arn = 'arn:aws:iam::439727791560:role/cloudigrade-role-for-743187646576'
    # Make sure that there isn't already an account using this arn.
    delete_current_cloud_accounts(arn)
    # Trigger Sources authentication
    create_auth_obj_in_sources()
    time = 30
    params = ('get', 'accounts/')
    cloudi_response = wait_for_response_with_timeout(client, params, arn, time)
    assert cloudi_response['name'] == 'aws-account-439727791560'
    assert cloudi_response['content_object']['account_arn'] == arn
