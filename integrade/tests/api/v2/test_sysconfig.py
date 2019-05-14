"""Tests for system configuration information.

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

from integrade.tests.constants import (
    TEST_URL,
)
from integrade.tests.utils import (
    get_credentials, is_on_local_network
)

logger = logging.getLogger(__name__)


@pytest.mark.skipif(not is_on_local_network(),
                    reason="Can't run outside of local RH network")
def test_sysconfig():
    """Ensure API v2 sysconfig returns expected configuration information.

    :id: 437E5632-60AD-43F6-A121-AE57A9A07F9A
    :description: Ensure sysconfig returns expected configuration information.
    :steps: Do a GET request to /api/v2/sysconfig/ with correct headers and
        check the response.
    :expectedresults: The server returns a 200 response with the expected
        configuration information.
    """
    creds = get_credentials()
    qa_branch = '554-create-delete-v2'
    qa_url = f'{TEST_URL}/sysconfig/'
    test_headers = {'X-4Scale-Env': 'ci', 'X-4Scale-Branch': qa_branch}
    qa_response = requests.get(
                    qa_url,
                    auth=creds,
                    headers=test_headers,
                    verify=False
                )
    stage_url = f'{TEST_URL}/sysconfig/'
    stage_headers = {'X-4Scale-Env': 'ci', 'X-4Scale-Branch': qa_branch}
    stage_response = requests.get(
        stage_url,
        auth=creds,
        headers=stage_headers,
        verify=False
    )

    # check that the config is able to access the test env
    assert qa_response.status_code == 200
    # check that the config is able to access the stage env
    assert stage_response.status_code == 200
