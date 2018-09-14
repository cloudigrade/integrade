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

import pytest

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait

from .utils import find_element_by_text, wait_for_input_value, \
    wait_for_page_text


logger = logging.getLogger(__name__)


CHECK_VALID = 'return document.getElementById("email").matches(":valid")'


def test_login_invalid_username(selenium, ui_loginpage_empty, ui_user):
    """Test the login form is invalid without an e-mail in the username.

    :id: e3858c7d-1be8-475a-944b-4a05392f404f
    :description: Open the cloudigrade interface and test non-email usernames
    :steps:
        1) Open the page and make sure we see the login form, not dashboard
        2) Fill the username field with a non-email
    :expectedresults: The login form's username field should not be marked as
        valid by the browser.
    """
    browser, login = ui_loginpage_empty()

    # Username field is not valid without a proper e-mail address entered
    login.username.fill('admin')
    assert not browser.execute_script(CHECK_VALID)


@pytest.mark.smoketest
def test_login_valid_username(selenium, ui_loginpage, ui_user):
    """Test the login form is valid with an e-mail in the username.

    :id: f5288391-08b3-4a4f-9fd3-b558caadd396
    :description: Open the cloudigrade interface and test email usernames
    :steps:
        1) Open the page and make sure we see the login form, not dashboard
        2) Fill the username field with an email address
    :expectedresults: The login form's username field should be marked as
        valid by the browser.
    """
    browser, login = ui_loginpage()

    # Username field becomes valid with an e-mail address entered as username
    assert browser.execute_script(CHECK_VALID)


def test_incorrect_login(selenium, ui_loginpage, ui_user):
    """Test the login fails with the correct username but incorrect password.

    :id: 55ce36fe-4055-4394-9cfe-2ae95a84d9d2
    :description: Open the cloudigrade interface and test that incorrect
        credentials fail.
    :steps:
        1) Open the page and make sure we see the login form, not dashboard
        2) Fill the username field with incorrect credentials for the test user
        3) Click the login button to attempt a login
    :expectedresults: The login should fail with an error on the page.
    """
    browser, login = ui_loginpage()
    wait = WebDriverWait(selenium, 30)

    # Username field becomes valid with an e-mail address entered as username
    login.username.fill(ui_user['username'])
    CHECK_VALID = 'return document.getElementById("email").matches(":valid")'
    assert browser.execute_script(CHECK_VALID)

    # Login fails with incorrect password
    login.password.fill('notmypassword')
    login.login.click()
    wait.until(wait_for_input_value((By.ID, 'password'), ''))
    error_card_class = 'cloudmeter-login-card-error'
    error_card = selenium.find_element_by_class_name(error_card_class)
    assert error_card.text == 'Email address or password is incorrect.'


def test_correct_login(selenium, ui_dashboard, ui_user):
    """Test the login fails with the correct username and password for the user.

    :id: 5c590b1b-ad1e-4efe-ba79-ed06e558e46a
    :description: Open the cloudigrade login page and successfully log into the
        dashboard
    :steps:
        1) Open the page and make sure we see the login form, not dashboard
        2) Fill the username field with correct credentials for the test user
        3) Click the login button to attempt a login
    :expectedresults: We should see the dashboard page, which the user is taken
        to after a successful login.
    """
    pass


def test_logout(selenium, ui_dashboard, ui_user):
    """Test the user can log out of the dashboard through the user menu.

    :id: 88763345-a218-4d70-8dab-c98b16e2d1ef
    :description: After a successful login try to logout of the site through
        the user menu.
    :steps:
        1) Follow the login steps to the dashboard
        2) Click the user menu identified by the username to open the menu
        3) Click the logout link in the open menu
    :expectedresults: The user should be taken back to the login page and when
        loading the site again they should still be logged out to ensure no
        session cookies remain valid.
    """
    browser, login = ui_dashboard
    wait = WebDriverWait(selenium, 10)

    # Logout appears in user dropdown, and logs out when clicked.
    # And, the Logout item does not appear outside the menu.
    logout = find_element_by_text(selenium, 'Logout')
    assert not logout or not logout.is_displayed()
    menu = find_element_by_text(selenium, ui_user['username'],
                                fail_hard=True, exact=False)
    if not menu:
        raise ValueError(selenium.page_source)
    assert menu.is_displayed(), selenium.get_window_size()
    menu.click()
    wait.until(wait_for_page_text('Logout'))
    find_element_by_text(selenium, 'Logout').click()

    login.login.wait_displayed()

    # User *stays* logged out, verifying authentication state was cleared as
    # well as login form being displayed
    selenium.refresh()
    login.login.wait_displayed()
