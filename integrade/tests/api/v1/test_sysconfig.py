"""Tests for system configuration information.

:caseautomation: automated
:casecomponent: api
:caseimportance: high
:caselevel: integration
:requirement: Cloud Meter
:testtype: functional
:upstream: yes
"""
import re

import pytest

from integrade import api
from integrade.tests import urls
from integrade.tests.utils import get_auth


@pytest.mark.skip(reason='v1 authentication no longer works - this is v2')
def test_sysconfig():
    """Ensure sysconfig returns expected configuration information.

    :id: 984b1e7c-597f-419c-8c73-8d84ce4417ff
    :description: Ensure sysconfig returns expected configuration information.
    :steps: Do an authenticated GET requests to /api/v1/sysconfig/ and check
        the response.
    :expectedresults: The server returns a 201 response with the expected
        configuration information. The api.json_handler will raise an error if
        the response_code isn't a successful one - ie 2XX OK, 4XX or 5XX NOK.
    """
    user = {
        'username': 'user1@example.com',
        'password': 'user1@example.com',
    }
    auth = get_auth(user)
    client = api.Client(response_handler=api.json_handler, token=auth)
    response = client.get(urls.SYSCONFIG, auth=auth)
    assert set(response.keys()) == set((
        'aws_account_id',
        'aws_policies',
        'version',
    ))
    assert re.match(r'\d+', response['aws_account_id'])


@pytest.mark.skip(reason='v1 authentication no longer works - this is v2')
def test_sysconfig_negative():
    """Ensure unauthenticated requests can't access configuration information.

    :id: 41b8309d-610e-4980-904d-72e19c0e1b63
    :description: Ensure that unauthenticated requests to sysconfig can't
        access configuration information.
    :steps: Do an unauthenticated GET request to /api/v1/sysconfig/.
    :expectedresults: The server returns a 401 response informing that the
        authentication information is needed to access the system
        configuration.
    """
    client = api.Client(authenticate=False, response_handler=api.echo_handler)
    response = client.get(urls.SYSCONFIG)
    assert response.status_code == 401
    assert response.json() == {
        'detail': 'Authentication credentials were not provided.'
    }
