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
from time import sleep

import pytest

from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.support.ui import WebDriverWait

from integrade import api, config
from integrade.tests.api.v1 import urls
from integrade.utils import flaky

from .utils import (
    fill_input_by_label,
    find_element_by_text,
    read_input_by_label,
    wait_for_page_text,
)

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
    dialog = ui_addacct_page1['dialog']

    fill_input_by_label(selenium, dialog, 'Account Name', profile_name)
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


@pytest.mark.skip(reason='http://gitlab.com/cloudigrade/frontigrade/issues/50')
def test_fill_name_and_clear(selenium, ui_addacct_page1, ui_user):
    """The account name's validity is always reflected in the Next button state.

    :id: b37525f1-e3d7-4fc9-80c1-270de82783fb
    :description: The Account Name field must not be empty before proceeding.
    :steps:
        1) Navigate to the dashboard and click the "Add Account" button
        2) Observe the "Next" button is disabled by default
        3) Enter a valid name and observe the "Next" button becomes enabled
        5) Clear the field and observe the button is disabled again
    :expectedresults: The "Next" button should only ever be enabled when the
        account name field is valid.
    """
    dialog = ui_addacct_page1['dialog']
    dialog_next = ui_addacct_page1['dialog_next']

    assert dialog_next.get_attribute('disabled')
    fill_input_by_label(selenium, dialog, 'Account Name', 'My Account')

    assert not dialog_next.get_attribute('disabled')
    input.clear()
    assert dialog_next.get_attribute('disabled')


@pytest.mark.parametrize('options', [
    ('It', 'It', 'Enter minimum of 3 characters for account name', True),
    ('x'*300, 'x'*256, None, False)
])
def test_account_name_required(options, selenium, ui_addacct_page1, ui_user):
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
    name, expected, error, disabled = options
    dialog = ui_addacct_page1['dialog']
    dialog_next = ui_addacct_page1['dialog_next']

    assert dialog_next.get_attribute('disabled')
    fill_input_by_label(selenium, dialog, 'Account Name', name)

    assert read_input_by_label(selenium, dialog, 'Account Name') == expected
    assert bool(dialog_next.get_attribute('disabled')) == disabled
    if error:
        assert error in selenium.page_source


def test_cancel(drop_account_data, selenium, ui_addacct_page3, ui_user):
    """The user can add a new account using a valid current ARN.

    :id: fa01c0a2-86da-11e8-af5f-8c1645548902
    :description: The user can create and name a new cloud account.
    :steps:
        1) Open the dashboard and click the "Add Account"
        2) Enter a name for the account
        3) Proceed to page 3
        4) Enter an ARN which is valid ARN for a resource we are granted
           permission to
        5) Click the "Add" button to attempt to create the account
    :expectedresults: The Account is created and can be fetched by the account
        list API for verification with the given name and ARN.
    """
    dialog = ui_addacct_page3['dialog']

    assert ui_addacct_page3['dialog_add'].get_attribute('disabled')

    acct_arn = config.get_config()['aws_profiles'][0]['arn']
    fill_input_by_label(selenium, dialog, 'ARN', acct_arn)

    find_element_by_text(dialog, 'Cancel').click()
    find_element_by_text(dialog, 'Yes').click()

    pytest.raises(
        NoSuchElementException,
        selenium.find_element_by_tag_name,
        'dialog',
    )

    c = api.Client()
    r = c.get(urls.CLOUD_ACCOUNT).json()
    accounts = [a for a in r['results'] if a['user_id'] == ui_user['id']]
    assert accounts == []


@flaky()
@pytest.mark.parametrize('mistake', [
    'change_name',
    'fake_out_cancel',
    'invalid_arn1',
    'invalid_arn2',
    None,
])
def test_add_account(mistake,
                     drop_account_data, selenium, ui_addacct_page3, ui_user):
    """The user can add a new account using a valid current ARN.

    :id: fa01c0a2-86da-11e8-af5f-8c1645548902
    :description: The user can create and name a new cloud account.
    :steps:
        1) Open the dashboard and click the "Add Account"
        2) Enter a name for the account
        3) Proceed to page 3
        4) Enter an ARN which is valid ARN for a resource we are granted
           permission to
        5) Click the "Add" button to attempt to create the account
    :expectedresults: The Account is created and can be fetched by the account
        list API for verification with the given name and ARN.
    """
    dialog = ui_addacct_page3['dialog']
    wait = WebDriverWait(selenium, 10)

    assert ui_addacct_page3['dialog_add'].get_attribute('disabled')

    acct_name = 'My Account'
    acct_arn = config.get_config()['aws_profiles'][0]['arn']
    acct_arn_good = acct_arn
    if mistake == 'invalid_arn1':
        acct_arn = 'oops:' + acct_arn
    elif mistake == 'invalid_arn2':
        acct_arn = acct_arn.replace('iam::', 'iam:')
    fill_input_by_label(selenium, dialog, 'ARN', acct_arn)

    c = api.Client()
    r = c.get(urls.CLOUD_ACCOUNT).json()
    accounts = [a for a in r['results'] if a['user_id'] == ui_user['id']]

    # Wait! Maybe I decided to change the account name?
    if mistake == 'change_name':
        find_element_by_text(dialog, 'Back').click()
        find_element_by_text(dialog, 'Back').click()

        current_name = read_input_by_label(selenium, dialog, 'Account Name')
        assert current_name == acct_name
        acct_name = 'Different Name'
        fill_input_by_label(selenium, dialog, 'Account Name', acct_name)

        find_element_by_text(dialog, 'Next').click()
        find_element_by_text(dialog, 'Next').click()

    if mistake == 'fake_out_cancel':
        find_element_by_text(dialog, 'Cancel').click()
        find_element_by_text(dialog, 'No').click()
        sleep(0.1)

    if mistake == 'invalid_arn1':
        assert 'You must enter a valid ARN' in selenium.page_source
        fill_input_by_label(selenium, dialog, 'ARN', acct_arn_good)
    elif mistake == 'invalid_arn2':
        find_element_by_text(dialog, 'Add').click()
        wait.until(wait_for_page_text('Invalid ARN.'))
        find_element_by_text(dialog, 'Back').click()
        fill_input_by_label(selenium, dialog, 'ARN', acct_arn_good)

    find_element_by_text(dialog, 'Add', timeout=1000).click()

    try:
        wait = WebDriverWait(selenium, 90)
        wait.until(wait_for_page_text('%s was created' % acct_name))
    except TimeoutException:
        duplicate_error = 'aws account with this account arn already exists.'
        if duplicate_error in selenium.page_source:
            # Retry after waiting and clearing accounts
            sleep(60)

    r = c.get(urls.CLOUD_ACCOUNT).json()
    accounts = [a for a in r['results'] if a['user_id'] == ui_user['id']]
    assert acct_name == accounts[0]['name']
    assert len(accounts) == 1, (len(accounts), ui_user['id'], r['results'])
    assert accounts[0]['account_arn'] == acct_arn_good


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
    fill_input_by_label(selenium, dialog, 'ARN', acct_arn)
    assert not dialog_add.get_attribute('disabled')

    dialog_add.click()

    wait.until(wait_for_page_text('Permission denied for ARN'))

    assert find_element_by_text(dialog, 'Close').get_attribute('disabled')
    assert not find_element_by_text(dialog, 'Next')
    assert not find_element_by_text(dialog, 'Add')
