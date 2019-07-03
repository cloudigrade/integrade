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

from integrade import api
from integrade.tests.utils import (
    is_on_local_network
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
    client = api.ClientV2()
    response = client.request('get', 'sysconfig/')
    assert response.status_code == 200, response.text
