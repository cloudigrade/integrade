"""Collection of fixtures representing reusable UI steps for UI tests."""
import atexit
import logging
import os

import pytest

from selenium import webdriver
from selenium.common.exceptions import TimeoutException, WebDriverException
from selenium.webdriver.support.ui import WebDriverWait

from widgetastic.browser import Browser

from integrade.config import get_config
from integrade.tests.utils import create_user_account, get_auth
from integrade.utils import base_url

from .utils import wait_for_page_text
from .views import LoginView


logger = logging.getLogger(__name__)
USER = None

USER1 = {
    'username': 'user1@example.com',
    'password': 'user1@example.com',
}
USER2 = {
    'username': 'user2@example.com',
    'password': 'user2@example.com',
}

DRIVERS = {}
BROWSERS = os.environ.get('UI_BROWSER', 'Chrome').split(',')


@pytest.fixture()
def new_session(request, scope='function'):
    """Close current browser session to force a new one to start.

    new_session must come _before_ browser_session in the fixture list of any
    test that depends on it.
    """
    browser = BROWSERS[0]
    if browser in DRIVERS:
        DRIVERS[browser].close()
        del DRIVERS[browser]


def _sauce_ondemand_url(saucelabs_user, saucelabs_key):
    """Get sauce ondemand URL for a given user and key."""
    return 'http://{0}:{1}@ondemand.saucelabs.com:80/wd/hub'.format(
        saucelabs_user, saucelabs_key)


@pytest.fixture()
def browser_session(request, scope='function'):
    """Adjust the selenium fixture's browser size."""
    use_saucelabs = os.environ.get('UI_USE_SAUCELABS', False)
    use_remote = os.environ.get('UI_USE_REMOTE', False)
    browser = BROWSERS[0]
    testsfailed = request.session.testsfailed

    if browser in DRIVERS:
        yield DRIVERS[browser]

    else:
        if use_saucelabs or browser in (
            'MicrosoftEdge',
            'InternetExplorer',
        ):
            cap = {
                'browserName': browser,
            }
            user = os.environ['SAUCELABS_USERNAME']
            key = os.environ['SAUCELABS_API_KEY']
            url = _sauce_ondemand_url(user, key)
            driver = webdriver.Remote(desired_capabilities=cap,
                                      command_executor=url)

        # Use selenium remote driver to connect to containerized browsers on CI
        elif use_remote:
            caps = webdriver.DesiredCapabilities
            cap = getattr(caps, browser.upper()).copy()
            driver = webdriver.Remote(
                command_executor='http://selenium:4444/wd/hub',
                desired_capabilities=cap,
            )

        elif browser == 'Firefox':
            opt = webdriver.FirefoxOptions()
            if os.environ.get('UITEST_SHOW', 'No').lower() != 'yes':
                opt.add_argument('--headless')
            driver = webdriver.Firefox(options=opt)
        elif browser == 'Chrome':
            opt = webdriver.ChromeOptions()
            if os.environ.get('UITEST_SHOW', 'No').lower() != 'yes':
                opt.add_argument('--headless')
            opt.add_argument('--no-sandbox')
            opt.add_argument('--disable-dev-shm-usage')
            driver = webdriver.Chrome(options=opt)

        driver.set_window_size(1200, 800)

        @atexit.register
        def clean_up():
            try:
                driver.close()
            except WebDriverException:
                pass

        DRIVERS[browser] = driver
        yield driver

    if testsfailed < request.session.testsfailed:
        # lets rebuild the browser session to be safe...
        try:
            DRIVERS[browser].close()
        except WebDriverException:
            pass
        del DRIVERS[browser]


def ui_user(user_info):
    """Create a user for use in a UI test."""
    user = create_user_account(user_info)
    get_auth(user)
    logger.debug('user: %s / %s', user['username'], user['password'])

    return user


@pytest.fixture()
def ui_loginpage_empty(browser_session):
    """Tool to navigate to the login page."""
    selenium = browser_session

    def _():
        selenium.get(base_url(get_config()))
        assert selenium.title == 'Cloud Meter', selenium.page_source

        browser = Browser(selenium)
        login = LoginView(browser)

        # User is directed to the login page, not the dashboard
        wait = WebDriverWait(selenium, 30)
        wait.until(wait_for_page_text('Log In to Your Account'))

        return browser, login
    return _


def ui_loginpage(ui_loginpage_empty, ui_user):
    """Tool to navigate to the login and fill in the username."""
    def _():
        browser, login = ui_loginpage_empty()
        login.username.fill(ui_user['username'])
        return browser, login
    return _


def ui_dashboard(browser_session, ui_loginpage, ui_user):
    """Tool to navigate to the dashboard by logging in."""
    selenium = browser_session
    if 'Welcome to Cloud Meter' in selenium.page_source:
        browser = Browser(selenium)
        login = None
        return browser, LoginView(browser)
    elif 'Login to Your Account' in selenium.page_source:
        browser, login = ui_loginpage()
    elif not selenium.current_url.startswith('http'):
        browser, login = ui_loginpage()
    else:
        browser = Browser(selenium)
        login = None

    wait = WebDriverWait(selenium, 30)

    if login:
        # Login passes with correct password
        login.password.fill(ui_user['password'])
        login.login.click()

        text = 'Welcome to Cloud Meter'
        try:
            wait.until(wait_for_page_text(text))
        except TimeoutException as e:
            e.msg = f'{text} not found in page: {selenium.page_source}'

    return browser, login


def ui_acct_list(browser_session, ui_loginpage, ui_user):
    """Tool to navigate to the account list by logging in."""
    selenium = browser_session
    if 'Welcome to Cloud Meter' in selenium.page_source:
        browser = Browser(selenium)
        return browser, LoginView(browser)
    elif 'Login to Your Account' in selenium.page_source:
        browser, login = ui_loginpage()
    elif not selenium.current_url.startswith('http'):
        browser, login = ui_loginpage()
    else:
        browser = Browser(selenium)
        login = None

    if login:
        wait = WebDriverWait(selenium, 10)

        # Login passes with correct password
        login.password.fill(ui_user['password'])
        login.login.click()

        wait.until(wait_for_page_text('Accounts'))

    return browser, login


@pytest.fixture()
def u1_user():
    """Create User1 for UI tests."""
    return ui_user(USER1)


@pytest.fixture()
def u2_user():
    """Create User2 for UI tests."""
    return ui_user(USER2)


@pytest.fixture()
def u1_loginpage(ui_loginpage_empty, u1_user):
    """Fixture factory to navigate/login and fill in user1 username."""
    return ui_loginpage(ui_loginpage_empty, u1_user)


@pytest.fixture()
def u2_loginpage(ui_loginpage_empty, u2_user):
    """Fixture factory to navigate/login and fill in user2 username."""
    return ui_loginpage(ui_loginpage_empty, u2_user)


@pytest.fixture()
def u1_dashboard(browser_session, u1_loginpage, u1_user):
    """Fixture to navigate to the dashboard user1 by logging in."""
    return ui_dashboard(browser_session, u1_loginpage, u1_user)


@pytest.fixture()
def u2_dashboard(browser_session, u2_loginpage, u2_user):
    """Fixture to navigate to the dashboard user2 by logging in."""
    return ui_dashboard(browser_session, u2_loginpage, u2_user)


@pytest.fixture()
def u1_acct_list(browser_session, u1_loginpage, u1_user):
    """Fixture to navigate to user1 account list by logging in."""
    return ui_acct_list(browser_session, u1_loginpage, u1_user)


@pytest.fixture()
def u2_acct_list(browser_session, u2_loginpage, u2_user):
    """Fixture to navigate to user2 account list by logging in."""
    return ui_acct_list(browser_session, u2_loginpage, u2_user)
