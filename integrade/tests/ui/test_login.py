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
import os

import pytest

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait

from widgetastic.browser import Browser

from integrade.config import get_config
from integrade.utils import base_url

from .utils import find_element_by_text, wait_for_input_value, \
    wait_for_page_text
from .views import LoginView
from ..api.v1.utils import create_user_account, get_auth
from ...utils import gen_password, uuid4


logger = logging.getLogger(__name__)


@pytest.fixture
def chrome_options(chrome_options):
    """Pass no sandbox to Chrome when running on Travis."""
    if os.environ.get('TRAVIS', 'false') == 'true':
        chrome_options.add_argument('--no-sandbox')
    return chrome_options


@pytest.fixture
def selenium(selenium):
    """Adjust the selenium fixture's browser size."""
    selenium.set_window_size(1200, 800)
    return selenium


def test_login(selenium):
    """Ensure login and logout operate properly for all credential cases.

    :id: e3858c7d-1be8-475a-944b-4a05392f404f
    :description: Open the cloudigrade interface and test failed logins,
        successful logins, and logout UIs.
    :steps:
        1) Open the page and make sure we see the login form, not dashboard
        2) Login with the wrong password and the verify error message
        3) Login with the right password and verify the dashboard is seen
        4) Attempt to open the user menu and click "Logout"
        5) Verify the login page appears again
    :expectedresults: The login should allow correct credentials only,
        reporting any errors to the user. The logout should be in the user menu
        and log the user totally out of the system.
    """
    username = uuid4() + '@example.com'
    password = gen_password()
    user = create_user_account({
        'username': username,
        'email': username,
        'password': password,
    })
    get_auth(user)
    logger.debug('user: %s / %s', username, password)

    selenium.get(base_url(get_config()))
    assert selenium.title == 'Cloud Meter'

    browser = Browser(selenium)
    login = LoginView(browser)
    wait = WebDriverWait(selenium, 5)

    # User is directed to the login page, not the dashboard
    wait.until(wait_for_page_text('Log In to Your Account'))

    # Username field is not valid without a proper e-mail address entered
    login.username.fill('admin')
    check_valid = 'return document.getElementById("email").matches(":valid")'
    assert not browser.execute_script(check_valid)

    # Username field becomes valid with an e-mail address entered as username
    login.username.fill(username)
    assert browser.execute_script(check_valid)

    # Login fails with incorrect password
    login.password.fill('notmypassword')
    login.login.click()
    wait.until(wait_for_input_value((By.ID, 'password'), ''))
    error_card_class = 'cloudmeter-login-card-error'
    error_card = selenium.find_element_by_class_name(error_card_class)
    assert error_card.text == 'Email address or password is incorrect.'

    # Login passes with correct password
    login.password.fill(password)
    login.login.click()
    wait.until(wait_for_page_text('Welcome to Cloud Meter'))

    # Logout appears in user dropdown, and logs out when clicked.
    # And, the Logout item does not appear outside the menu.
    logout = find_element_by_text(selenium, 'Logout')
    assert not logout or not logout.is_displayed()
    menu = find_element_by_text(selenium, username, fail_hard=True)
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
