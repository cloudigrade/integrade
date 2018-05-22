"""Tests for the UI skeleton page.

:caseautomation: automated
:casecomponent: ui
:caseimportance: low
:caselevel: integration
:requirement: Cloud Meter
:testtype: functional
:upstream: yes
"""
import os

import pytest

from integrade.config import get_config
from integrade.utils import base_url


@pytest.fixture
def chrome_options(chrome_options):
    """Pass no sandbox to Chrome when running on Travis."""
    if os.environ.get('TRAVIS', 'false') == 'true':
        chrome_options.add_argument('--no-sandbox')
    return chrome_options


def test_skeleton(selenium):
    """Ensure the skeleton page is accessible.

    :id: 456c980f-6019-4e97-85a7-ef113a45d933
    :description: Access the cloudigrade URL and check if the skeleton page is
        accessible on the server's ``/``.
    :steps: Access ``<cloudigrade_url>/`` and check the page title.
    :expectedresults: The page should be accessible and the page's title must
        be Cloud Meter.
    """
    selenium.get(base_url(get_config()))
    assert selenium.title == 'Cloud Meter'
