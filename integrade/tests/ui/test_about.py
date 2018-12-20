"""Tests for the UI Login page.

:caseautomation: automated
:casecomponent: ui
:caseimportance: low
:caselevel: integration
:requirement: Cloud Meter
:testtype: functional
:upstream: yes
"""
import logging
import time

from .utils import find_element_by_text


logger = logging.getLogger(__name__)


def test_elements_present_in_modal(cloud_account_data,
                                   browser_session, ui_dashboard):
    """Confirm that necessary elements are on the cloudigrade about modal.

    :id: 85eac06a-7300-422a-9a3a-f83dd55cdb61
    :description: This test is designed to verify the about modal
    :steps:
        1) Click on the question mark
        2) Click on about
    :expectedresults:
        - Modal with app information shows up
    """
    selenium = browser_session
    menu = selenium.find_element_by_id('app-help-dropdown')
    menu.click()
    time.sleep(0.25)
    find_element_by_text(browser_session, 'About').click()

    assert find_element_by_text(selenium, 'Username')
    assert find_element_by_text(selenium, 'Browser Version')
    assert find_element_by_text(selenium, 'Browser OS')
    assert find_element_by_text(selenium, 'API Version')
