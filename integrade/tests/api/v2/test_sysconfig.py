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
import re
import requests

from integrade import api
from integrade.tests import urls
from integrade.tests.utils import get_auth

def is_on_local_network():
    """Check if on internal RH network. This matters because we can ONLY access
    3scale from inside Red Hat network. API V2 tests should be skipped if this
    returns False - ie. if running in gitlab CI"""

    url = 'https://api.access.stage.cloud.paas.upshift.redhat.com'
    try:
        requests.get(url, verify=False)
    except requests.exceptions.ConnectionError as e:
        logging.warning(e)
        return False
    return True

@pytest.mark.skipif(not is_on_local_network(),
                    reason='Can\'t run outside of local RH network')
def test_sysconfig():
    """Ensure API v2 sysconfig returns expected configuration information.

    :id: 437E5632-60AD-43F6-A121-AE57A9A07F9A
    :description: Ensure sysconfig returns expected configuration information.
    :steps: Do a GET request to /api/v2/sysconfig/ with correct headers and
        check the response.
    :expectedresults: The server returns a 200 response with the expected
        configuration information.
    """

    qa = 'api.access.qa.cloud.paas.upshift.redhat.com'
    qa_end = '/r/insights/platform/cloudigrade/api/v2/sysconfig/'
    creds = ('mpierce@redhat.com', 'redhat')
    V2_QA_URL = f'https://{qa}{qa_end}'
    qa_branch = '3scale-investigation'
    qa_url = V2_QA_URL
    test_headers = {'X-4Scale-Env': 'ci', 'X-4Scale-Branch': qa_branch}
    qa_response = requests.get(
                    qa_url,
                    auth=creds,
                    headers=test_headers,
                    verify=False
                )

    stage = 'api.access.stage.cloud.paas.upshift.redhat.com'
    stage_end = '/r/insights/platform/cloudigrade/auth/"'
    V2_STAGE_URL = f'https://{stage}{stage_end}'
    stage_url = V2_STAGE_URL
    stage_headers = {'X-4Scale-Env': 'qa'}
    stage_response = requests.get(
                        stage_url,
                        auth=creds,
                        headers=stage_headers,
                        verify=False
                    )

    # check that the config is able to access the stage env
    assert stage_response.status_code == 200
    # check that the config is able to access the test env
    assert qa_response.status_code == 200
