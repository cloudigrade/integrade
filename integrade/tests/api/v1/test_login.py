"""Test authentication with the server.

:caseautomation: automated
:casecomponent: api
:caseimportance: high
:caselevel: integration
:requirement: Cloud Meter
:testtype: functional
:upstream: yes
"""
from integrade import api
from integrade.utils import uuid4

import pytest


@pytest.mark.skip
def test_login():
    """Test that we can login to the server.

    :id: 2eb55229-4e1e-4d35-ac4a-4f2424d37cf6
    :description: Test that we can login to the server
    :steps: Send POST with username and password to the token endpoint
    :expectedresults: Receive an authorization token that we can then use
        to build our authentication headers and make authenticated requests.
    :caseautomation: notautomated
    """


@pytest.mark.skip
def test_logout(endpoint):
    """Test that we can log out of the server.

    :id: ca51b2a0-1e33-491d-8bb2-5e81d135424d
    :description: Test that we can logout of the server and requests missing
        a valid auth token are rejected.
    :steps:
        1) Log into the server
        2) Logout of the server
        3) Try an access the server
    :expectedresults: Our request missing a valid auth token is rejected.
    :caseautomation: notautomated
    """


def test_token():
    """Given that we have a valid token, we can make requests.

    :id: addd7d83-961a-4cdf-9473-7c6db93e6af9
    :description: Test that if we have a good token, we can use it  to make
        requests.
    :steps:
        1) Send a GET request with a valid authorization token in the header.
        2) Assert that we get a 200 response.
    :expectedresults: The server accepts our valid token.
    """
    client = api.Client()
    response = client.get()
    assert response.status_code == 200


def test_token_negative():
    """Given that we have an invalid token, we cannot make requests.

    :id: a87f7069-3ee9-4435-a953-fd8664199419
    :description: Test that if we have a bad token, we cannot use it to make
        requests.
    :steps:
        1) Send a GET request with a invalid authorization token in the header.
        2) Assert that we get a 401 response.
    :expectedresults: The server rejects our invalid token.
    """
    client = api.Client(response_handler=api.echo_handler)
    client.token = uuid4()
    response = client.get()
    assert response.status_code == 401
