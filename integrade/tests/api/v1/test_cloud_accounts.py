"""Tests for cloud accounts.

:caseautomation: automated
:casecomponent: api
:caseimportance: high
:caselevel: integration
:requirement: Cloud Meter
:testtype: functional
:upstream: yes
"""
from urllib.parse import urljoin

import pytest

from integrade import api, config
from integrade.tests.api.v1 import urls
from integrade.tests.api.v1.utils import get_auth
from integrade.utils import uuid4


@pytest.mark.serial_only
@pytest.mark.skipif(len(config.get_config()[
    'valid_roles']) < 1, reason='needs at least 1 valid arn')
def test_create_cloud_account(drop_account_data):
    """Ensure cloud accounts can be registered to a user.

    :id: d0174576-9b7c-48f7-8556-b560badf062d
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
    auth = get_auth()
    client = api.Client(authenticate=False)

    cfg = config.get_config()
    cloud_account = {
        'account_arn': cfg['valid_roles'][0],
        'resourcetype': 'AwsAccount'
    }
    create_response = client.post(
        urls.CLOUD_ACCOUNT,
        payload=cloud_account,
        auth=auth
    )
    assert create_response.status_code == 201

    acct = create_response.json()

    # get specific account
    get_response = client.get(
        urljoin(urls.CLOUD_ACCOUNT,
                '{}/'.format(acct['id'])
                ), auth=auth)
    assert acct == get_response.json()

    # list cloud accounts associated with this user
    list_response = client.get(urls.CLOUD_ACCOUNT, auth=auth)
    assert acct in list_response.json()['results']

    # TODO need to try and update name, but
    # feature is not delivered yet.
    # Nameing cloud accounts:
    #     https://github.com/cloudigrade/cloudigrade/issues/267
    # Updating cloud accounts:
    #     https://github.com/cloudigrade/cloudigrade/issues/333

    # TODO need to try and update arn, but
    # feature is not delivered yet.
    # Updating cloud accounts:
    # https://github.com/cloudigrade/cloudigrade/issues/333

    # assert we cannot create duplicate
    client.response_handler = api.echo_handler
    response = client.post(
        urls.CLOUD_ACCOUNT,
        payload=cloud_account,
        auth=auth
    )
    assert response.status_code == 400
    assert 'account_arn' in response.json().keys()
    assert 'already exists' in response.json()['account_arn'][0]

    # attempt to delete the specific account
    delete_response = client.delete(
        urljoin(urls.CLOUD_ACCOUNT,
                '{}/'.format(acct['id'])
                ), auth=auth)
    assert delete_response.status_code == 405


@pytest.mark.serial_only
@pytest.mark.skipif(len(config.get_config()[
                    'valid_roles']) < 2, reason='needs at least 2 valid arns')
def test_create_multiple_cloud_accounts(drop_account_data):
    """Ensure cloud accounts can be registered to a user.

    :id: d0174576-9b7c-48f7-8556-b560badf062d
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
    for arn in cfg['valid_roles']:
        cloud_account = {
            'account_arn': arn,
            'resourcetype': 'AwsAccount'
        }
        create_response = client.post(
            urls.CLOUD_ACCOUNT,
            payload=cloud_account,
            auth=auth
        )
        assert create_response.status_code == 201

        accts.append(create_response.json())

    # list cloud accounts associated with this user
    list_response = client.get(urls.CLOUD_ACCOUNT, auth=auth)
    for acct in accts:
        assert acct in list_response.json()['results']


@pytest.mark.serial_only
@pytest.mark.skipif(len(config.get_config()[
                    'valid_roles']) < 3, reason='needs at least 3 valid arns')
def test_negative_read_other_cloud_account(drop_account_data):
    """Ensure users cannot access eachother's cloud accounts.

    :id: d0174576-9b7c-48f7-8556-b560badf062d
    :description: Ensure one user is not allowed to read another user's cloud
        account data.
    :steps: 1) Create two users and authenticate with their passwords
        2) For each user, send a POST with the cloud account information to
            'api/v1/account/'
        3) For each, send a GET to 'api/v1/account/' to get a list of the
           cloud accounts
        4) Ensure a super user sees all accounts.
    :expectedresults: The server only returns cloud accounts related to the
        user making the request, except the super user, who sees all accounts.
    """
    client = api.Client(authenticate=False)
    auth1 = get_auth()
    auth2 = get_auth()

    cfg = config.get_config()

    # create cloud account for 1st user
    cloud_account = {
        'account_arn': cfg['valid_roles'][0],
        'resourcetype': 'AwsAccount'
    }
    create_response = client.post(
        urls.CLOUD_ACCOUNT,
        payload=cloud_account,
        auth=auth1
    )
    assert create_response.status_code == 201
    acct1 = create_response.json()

    # update cloud account to differnt ARN
    # and create account for 2nd user
    cloud_account['account_arn'] = cfg['valid_roles'][1]
    create_response = client.post(
        urls.CLOUD_ACCOUNT,
        payload=cloud_account,
        auth=auth2
    )
    assert create_response.status_code == 201
    acct2 = create_response.json()

    # list cloud accounts associated with each user
    list_response = client.get(urls.CLOUD_ACCOUNT, auth=auth1)
    assert acct1 in list_response.json()['results']
    assert acct2 not in list_response.json()['results']

    list_response = client.get(urls.CLOUD_ACCOUNT, auth=auth2)
    assert acct2 in list_response.json()['results']
    assert acct1 not in list_response.json()['results']

    # use super user token to see all
    superclient = api.Client()
    list_response = superclient.get(urls.CLOUD_ACCOUNT)
    assert acct1 in list_response.json()['results']
    assert acct2 in list_response.json()['results']

    # create cloud account with super user
    # update cloud account to differnt ARN
    cloud_account['account_arn'] = cfg['valid_roles'][2]
    create_response = superclient.post(
        urls.CLOUD_ACCOUNT,
        payload=cloud_account,
    )
    assert create_response.status_code == 201
    acct3 = create_response.json()
    list_response = superclient.get(urls.CLOUD_ACCOUNT)
    assert acct3 in list_response.json()['results']
    assert list_response.json()['count'] == 3

    # make sure user1 still just see theirs
    list_response = client.get(urls.CLOUD_ACCOUNT, auth=auth1)
    assert acct1 in list_response.json()['results']
    assert acct2 not in list_response.json()['results']
    assert acct3 not in list_response.json()['results']


@pytest.mark.parametrize('field_to_delete', ['resourcetype', 'account_arn'])
def test_negative_create_cloud_account_missing(field_to_delete):
    """Ensure attempts to create cloud accounts missing data are rejected.

    :id: a93821ba-4181-47e7-b685-dbe642c1441e
    :description: Ensure an user cannot register a cloud account missing data.
    :steps: 1) Create a user and authenticate with their password
        2) Send a POST with the incomplete cloud account information to
            'api/v1/account/'
    :expectedresults: The server rejects the incomplete request.
    """
    auth = get_auth()
    client = api.Client(authenticate=False, response_handler=api.echo_handler)

    cloud_account = {
        'account_arn': uuid4(),
        'resourcetype': 'AwsAccount'
    }
    # remove one field
    cloud_account.pop(field_to_delete)
    create_response = client.post(
        urls.CLOUD_ACCOUNT,
        payload=cloud_account,
        auth=auth
    )
    assert create_response.status_code == 400
