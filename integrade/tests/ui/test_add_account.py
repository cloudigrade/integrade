"""Tests for the Add Account wizard interface.

:caseautomation: automated
:casecomponent: ui
:caseimportance: low
:caselevel: integration
:requirement: Cloud Meter
:testtype: functional
:upstream: yes
"""
import logging

import pytest

from selenium.webdriver.support.ui import WebDriverWait

from integrade import api
from integrade.tests.api.v1 import urls

from .utils import find_element_by_text, wait_for_page_text

logger = logging.getLogger(__name__)


@pytest.fixture
def ui_addacct_page1(selenium, ui_dashboard):
    """Open the Add Account dialog."""
    browser, login = ui_dashboard

    btn_add_account = find_element_by_text(selenium, 'Add Account')
    btn_add_account.click()

    dialog = selenium.find_element_by_css_selector('[role=dialog]')

    return {
        'dialog': dialog,
        'dialog_next': find_element_by_text(dialog, 'Next'),
    }


@pytest.fixture
def ui_addacct_page2(selenium, ui_addacct_page1):
    """Navigate to the second page of the Add Account dialog."""
    profile_name = 'My Account'

    find_element_by_text(ui_addacct_page1['dialog'], 'Account Name').click()
    input = selenium.execute_script('return document.activeElement')
    input.send_keys(profile_name)

    ui_addacct_page1['dialog_next'].click()

    return ui_addacct_page1


@pytest.fixture
def ui_addacct_page3(selenium, ui_addacct_page2):
    """Navigate to the 3rd page of the dialog, with the ARN field."""
    dialog = ui_addacct_page2['dialog']
    dialog_next = ui_addacct_page2['dialog_next']

    dialog_next.click()

    dialog_add = find_element_by_text(dialog, 'Add')
    assert dialog_add.get_attribute('disabled')

    ui_addacct_page2['dialog_add'] = dialog_add
    return ui_addacct_page2


@pytest.mark.skip()
def test_account_name_required(selenium, ui_addacct_page1, ui_user):
    """The first page's Account Name field is required before proceeding.

    :id: 259bf756-86da-11e8-bec5-8c1645548902
    :description: The Account Name field must not be empty before proceeding.
        The "Next" button must be disabled if this field is invalid.
    :steps:
        1) Navigate to the dashboard and click the "Add Account" button
        2) Observe the "Next" button is disabled by default
        3) Try to enter less than 3 characters, observe the button is still
           disabled
        4) Entry a longer name and observe the button is enabled now
        5) Clear the field and observe the button is disabled again
    :expectedresults: The "Next" button should only ever be enabled when the
        account name field is valid.
    """
    dialog = ui_addacct_page1['dialog']
    dialog_next = ui_addacct_page1['dialog_next']

    assert dialog_next.get_attribute('disabled')
    find_element_by_text(dialog, 'Account Name').click()
    input = selenium.execute_script('return document.activeElement')
    input.send_keys('My Account')

    assert not dialog_next.get_attribute('disabled')
    input.clear()
    assert dialog_next.get_attribute('disabled')


def test_add_account(drop_account_data, selenium, ui_addacct_page3, ui_user):
    """The user can add a new account using a valid current ARN.

    :id: fa01c0a2-86da-11e8-af5f-8c1645548902
    :description: The user can create and name a new cloud account.
    :steps:
        1) Open the dashboard and click the "Add Account"
        2) Enter a name for the account
        3) Proceed to page 3
        4) Enter an ARN which is not a valid ARN for a resource we are granted
           permission to
        5) Click the "Add" button to attempt to create the account
    :expectedresults: The Account is created and can be fetched by the account
        list API for verification with the given name and ARN.
    """
    dialog = ui_addacct_page3['dialog']
    dialog_add = ui_addacct_page3['dialog_add']
    wait = WebDriverWait(selenium, 10)

    assert dialog_add.get_attribute('disabled')

    acct_arn = 'arn:aws:iam::518028203513:role/Cloud-Meter-role'
    find_element_by_text(dialog, 'ARN').click()
    input = selenium.execute_script('return document.activeElement')
    input.send_keys(acct_arn)
    assert not dialog_add.get_attribute('disabled')

    c = api.Client()
    r = c.get(urls.CLOUD_ACCOUNT).json()
    accounts = [a for a in r['results'] if a['user_id'] == ui_user['id']]

    dialog_add.click()

    wait = WebDriverWait(selenium, 90)
    wait.until(wait_for_page_text('My Account was created'))

    r = c.get(urls.CLOUD_ACCOUNT).json()
    assert len(accounts) == 1, accounts
    assert accounts['account_arn'] == acct_arn


def test_invalid_arn(drop_account_data, selenium, ui_addacct_page3, ui_user):
    """The account cannot be added if the ARN given is not valid.

    :id: 3dc59808-86c3-11e8-9cd4-8c1645548902
    :description: Walking to the end of the wizard fails if the ARN given does
        not give our account access to the resource.
    :steps:
        1) Open the dashboard and click the "Add Account"
        2) Enter a name for the account
        3) Proceed to page 3
        4) Enter an ARN which is not a valid ARN for a resource we are granted
           permission to
        5) Click the "Add" button to attempt to create the account
    :expectedresults: The user should see the page load for a few seconds and
        then receive an error, after which they should not be able to continue.
    """
    dialog = ui_addacct_page3['dialog']
    dialog_add = ui_addacct_page3['dialog_add']
    wait = WebDriverWait(selenium, 10)

    acct_arn = 'arn:aws:iam::543234867065:role/Cloud-Meter-role-WRONG'
    find_element_by_text(dialog, 'ARN').click()
    input = selenium.execute_script('return document.activeElement')
    input.send_keys(acct_arn)
    assert not dialog_add.get_attribute('disabled')

    dialog_add.click()

    wait.until(wait_for_page_text('Permission denied for ARN'))

    assert find_element_by_text(dialog, 'Close').get_attribute('disabled')
    assert not find_element_by_text(dialog, 'Next')
    assert not find_element_by_text(dialog, 'Add')
