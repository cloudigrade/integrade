"""Collection of fixtures representing reusable UI steps for UI tests."""
import logging

import pytest

from selenium.webdriver.support.ui import WebDriverWait

from widgetastic.browser import Browser

from integrade.config import get_config
from integrade.utils import base_url

from .utils import wait_for_page_text
from .views import LoginView
from ..api.v1.utils import create_user_account, get_auth
from ...utils import gen_password, uuid4


logger = logging.getLogger(__name__)
USER = None


@pytest.fixture()
def ui_user():
    """Create a user for use in a UI test."""
    global USER
    if USER:
        return USER
    else:
        username = uuid4() + '@example.com'
        password = gen_password()
        user = create_user_account({
            'username': username,
            'email': username,
            'password': password,
        })
        get_auth(user)
        logger.debug('user: %s / %s', username, password)

        USER = user
        return user


@pytest.fixture()
def ui_loginpage_empty(selenium, ui_user):
    """Fixture factory to navigate to the login page."""
    def _():
        selenium.get(base_url(get_config()))
        assert selenium.title == 'Cloud Meter'

        browser = Browser(selenium)
        login = LoginView(browser)

        # User is directed to the login page, not the dashboard
        wait = WebDriverWait(selenium, 30)
        wait.until(wait_for_page_text('Log In to Your Account'))

        return browser, login
    return _


@pytest.fixture()
def ui_loginpage(selenium, ui_loginpage_empty, ui_user):
    """Fixture factory to navigate to the login and fill in the username."""
    def _():
        browser, login = ui_loginpage_empty()
        login.username.fill(ui_user['username'])
        return browser, login
    return _


@pytest.fixture
def ui_dashboard(selenium, ui_loginpage, ui_user):
    """Fixture to navigate to the dashboard by logging in."""
    if 'Welcome to Cloud Meter' in selenium.page_source:
        browser = Browser(selenium)
        return browser, LoginView(browser)
    else:
        browser, login = ui_loginpage()

    wait = WebDriverWait(selenium, 10)

    # Login passes with correct password
    login.password.fill(ui_user['password'])
    login.login.click()

    wait.until(wait_for_page_text('Welcome to Cloud Meter'))

    return browser, login
