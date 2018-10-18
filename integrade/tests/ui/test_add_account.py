"""Tests for the Add Account wizard interface.

:caseautomation: automated
:casecomponent: ui
:caseimportance: low
:caselevel: integration
:requirement: Cloud Meter
:testtype: functional
:upstream: yes
"""
import json
import logging
from time import sleep

import pytest

from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.support.ui import WebDriverWait

from integrade import api, config
from integrade.tests import urls
from integrade.tests.utils import get_auth

from .utils import (
    fill_input_by_label,
    find_element_by_text,
    read_input_by_label,
    wait_for_page_text,
)

logger = logging.getLogger(__name__)


ACCT_CREATE_TIMEOUT = 5


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
    input = fill_input_by_label(selenium, dialog, 'Account Name', 'My Account')

    assert not dialog_next.get_attribute('disabled')
    input.clear()
    assert dialog_next.get_attribute('disabled')


def test_aws_link(browser_session, ui_addacct_page1):
    """Check the Add Account dialog's AWS link.

    :id: 9f7d2780-63b9-4691-a7e3-3dfa738a994b
    :description: The link to the AWS IAM console must open in a new tab
        and must link to the correct section, not the top-level console.
    :steps:
        1) Navigate to the dashboard and click the "Add Account" button
        2) Observe the AWS link on the dialog
    :expectedresults: The link should go to the expected page and should
        target a new, blank tab.
    """
    selenium = browser_session
    dialog = ui_addacct_page1['dialog']

    link = find_element_by_text(selenium, 'AWS Identity Access Management')
    assert link, dialog.get_attribute('outerHTML')

    href = link.get_attribute('href')
    target = link.get_attribute('target')

    assert href == 'https://console.aws.amazon.com/iam'
    assert target == '_blank'


@pytest.mark.parametrize('options', [
    ('', '', '', True),
    ('x'*300, 'x'*256, None, False)
])
def test_account_name_required(options, browser_session, ui_addacct_page1):
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
    selenium = browser_session
    name, expected, error, disabled = options
    dialog = ui_addacct_page1['dialog']
    dialog_next = ui_addacct_page1['dialog_next']

    assert dialog_next.get_attribute('disabled')
    fill_input_by_label(selenium, dialog, 'Account Name', name)

    assert read_input_by_label(selenium, dialog, 'Account Name') == expected
    assert bool(dialog_next.get_attribute('disabled')) == disabled
    if error:
        assert error in selenium.page_source


def test_cancel(drop_account_data, browser_session, ui_addacct_page3, ui_user):
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
    selenium = browser_session
    dialog = ui_addacct_page3['dialog']

    assert ui_addacct_page3['dialog_add'].get_attribute('disabled')

    acct_arn = config.get_config()['aws_profiles'][0]['arn']
    fill_input_by_label(selenium, dialog, 'ARN', acct_arn)

    find_element_by_text(dialog, 'Cancel').click()
    find_element_by_text(selenium, 'Yes').click()

    pytest.raises(
        NoSuchElementException,
        selenium.find_element_by_tag_name,
        'dialog',
    )

    c = api.Client()
    r = c.get(urls.CLOUD_ACCOUNT).json()
    accounts = [a for a in r['results'] if a['user_id'] == ui_user['id']]
    assert accounts == []


@pytest.mark.parametrize('mistake', [
    'fake_out_cancel',
    'invalid_arn1',
    'invalid_arn2',
])
def test_arn_mistakes(mistake,
                      browser_session, ui_addacct_page3,
                      ui_user):
    """The user will fail to create a new account using an invalid current ARN.

    :id: 7f4e55e8-b4c2-42ac-b651-b7f6689aeebe
    :description: We ensure the correct error reponse for a number of mistakes
        the user can make
    :steps:
        1) Open the dashboard and click the "Add Account"
        2) Enter a name for the account
        3) Proceed to page 3
        4) Enter an incorrect ARN
        5) Click the "Add" button to attempt to create the account
    :expectedresults: The Account is not created and the proper error is shown
        and is able to be corrected
    """
    selenium = browser_session
    dialog = ui_addacct_page3['dialog']
    wait = WebDriverWait(selenium, 15)

    assert ui_addacct_page3['dialog_add'].get_attribute('disabled')

    acct_arn = config.get_config()['aws_profiles'][0]['arn']
    acct_arn_good = acct_arn
    if mistake == 'invalid_arn1':
        acct_arn = 'oops:' + acct_arn
    elif mistake == 'invalid_arn2':
        acct_arn = acct_arn.replace('iam::', 'iam:')
    fill_input_by_label(selenium, dialog, 'ARN', acct_arn)

    if mistake == 'fake_out_cancel':
        find_element_by_text(dialog, 'Cancel').click()
        find_element_by_text(selenium, 'No').click()

        # The add account dialog must still looks right after closed the cancel
        # dialog
        value = read_input_by_label(selenium, None, 'ARN')
        add = find_element_by_text(selenium, 'Add')

        assert value == acct_arn
        assert not add.get_attribute('disabled')

    if mistake == 'invalid_arn1':
        # The invalid ARN error must appear once the incorrect ARN is entered
        assert 'You must enter a valid ARN' in selenium.page_source

        # The invalid ARN error must go away once the correct ARN is entered
        fill_input_by_label(selenium, dialog, 'ARN', acct_arn_good,
                            timeout=0.25)
        assert 'You must enter a valid ARN' not in selenium.page_source

    elif mistake == 'invalid_arn2':
        # Trying to submit with an invalid ARN should display an error both on
        # the confirmation page and on the original form if you return
        find_element_by_text(dialog, 'Add',
                             timeout=0.25).click()
        wait.until(wait_for_page_text('Invalid ARN.'))
        find_element_by_text(dialog, 'Back').click()
        wait.until(wait_for_page_text('Invalid ARN.'))

        # The error should be removed if you enter a correct ARN
        fill_input_by_label(selenium, dialog, 'ARN', acct_arn_good,
                            timeout=0.25)
        assert find_element_by_text(selenium, 'Invalid ARN') is None


def test_incorrect_arn(drop_account_data, browser_session, ui_addacct_page3,
                       ui_user):
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
    selenium = browser_session
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


def test_aws_policy(drop_account_data,
                    browser_session,
                    ui_addacct_page1,
                    ui_user):
    """Test the shared policy between UI and API.

    :id: 82c82a98-4e03-4459-8944-9cca03b59955
    :description: The UI should use the currently single policy from the API.
    :steps:
        1) Open the Add Account dialog and view the policy
        2) Get the policy from the API directly
    :expectedresults: The policy named traditional_inspection from the API
        should match the policy contents in the UI precisely.
    """
    el = browser_session.find_element_by_class_name('cloudmeter-copy-input')
    ui_policy = json.loads(el.get_attribute('value'))

    auth = get_auth()
    client = api.Client(response_handler=api.json_handler)
    response = client.get(urls.SYSCONFIG, auth=auth)
    api_policy = response['aws_policies']['traditional_inspection']

    assert api_policy == ui_policy


def test_add_account(drop_account_data,
                     browser_session, ui_addacct_page3,
                     ui_user):
    """The user can add a new account using a valid current ARN.

    :id: 8c5e7e59-94f8-43fa-9e05-682346552252
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
    selenium = browser_session
    dialog = ui_addacct_page3['dialog']
    wait = WebDriverWait(selenium, 15)

    assert ui_addacct_page3['dialog_add'].get_attribute('disabled')

    acct_name = 'My Account'
    acct_arn = config.get_config()['aws_profiles'][0]['arn']
    acct_arn_good = acct_arn
    fill_input_by_label(selenium, dialog, 'ARN', acct_arn)

    # We also want to make sure you can go back and change a name
    find_element_by_text(dialog, 'Back').click()
    find_element_by_text(dialog, 'Back').click()

    current_name = read_input_by_label(selenium, dialog, 'Account Name')
    assert current_name == acct_name
    acct_name = 'Different Name'
    fill_input_by_label(selenium, dialog, 'Account Name', acct_name)

    find_element_by_text(dialog, 'Next').click()
    find_element_by_text(dialog, 'Next').click()

    # We want a list of current accounts so we can check our new account
    # afterwards
    c = api.Client()
    r = c.get(urls.CLOUD_ACCOUNT).json()
    accounts = [a for a in r['results'] if a['user_id'] == ui_user['id']]

    find_element_by_text(dialog, 'Add', timeout=1).click()

    try:
        wait = WebDriverWait(selenium, ACCT_CREATE_TIMEOUT)
        wait.until(wait_for_page_text('%s was created' % acct_name))
    except TimeoutException:
        duplicate_error = 'aws account with this account arn already exists.'
        # Retry after waiting and clearing accounts
        if duplicate_error in selenium.page_source:
            sleep(10)
        pytest.fail(
            'Could not create cloud account, or did not see valid '
            'message to indicate successful creation.'
        )

    find_element_by_text(dialog, 'Close').click()
    sleep(0.25)

    # We don't see the welcome screen anymore
    assert find_element_by_text(selenium, 'Welcome to Cloud Meter') is None
    assert find_element_by_text(selenium, acct_name) is not None

    # The account exists in the API
    r = c.get(urls.CLOUD_ACCOUNT).json()
    accounts = [a for a in r['results'] if a['user_id'] == ui_user['id']]
    assert acct_name == accounts[0]['name']
    assert len(accounts) == 1, (len(accounts), ui_user['id'], r['results'])
    assert accounts[0]['account_arn'] == acct_arn_good
