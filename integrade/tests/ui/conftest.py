"""Collection of fixtures representing reusable UI steps for UI tests."""
import atexit
import logging
import os
import time

import pytest

from selenium import webdriver
from selenium.common.exceptions import TimeoutException, WebDriverException
from selenium.webdriver.support.ui import WebDriverWait

from widgetastic.browser import Browser

from integrade.config import get_config
from integrade.injector import inject_aws_cloud_account, inject_instance_data
from integrade.tests.utils import create_user_account, get_auth
from integrade.utils import base_url

from .utils import (
    fill_input_by_label,
    find_element_by_text,
    wait_for_page_text,
)
from .views import LoginView
from ...utils import gen_password, uuid4


logger = logging.getLogger(__name__)
USER = None
CLOUD_ACCOUNT_NAME = 'First Account'


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


@pytest.fixture
def cloud_account(ui_user, drop_account_data):
    """Create a cloud account, return the auth object and account details."""
    return inject_aws_cloud_account(ui_user['id'], name=CLOUD_ACCOUNT_NAME)


@pytest.fixture
def cloud_account_data(cloud_account):
    """Create a factory to create cloud account data.

    This fixture creates a factory (a function) which will insert data into a
    newly created cloud account. Repeated calls will insert the data into the
    same cloud account. Data is inserted with a given image tag and a series
    of instance events, given in either `datetime` objects or day offsets from
    the current time.

    Create one instance with a RHEL image that was powered on 5 days ago:

        cloud_account_data("rhel", [5])

    Create three instances from a single non-RHEL, non-OpenShift image that
    ran for two weeks in September:

        image_id = "my_image_id"
        start = datetime(2018, 9, 1)
        stop = datetime(2018, 9, 14)
        for i in range(3):
            cloud_account_data("", [start, stop], ec2_ami_id=image_id)
    """
    def factory(tag, events, **kwargs):
        inject_instance_data(cloud_account['id'], tag, events, **kwargs)
    return factory


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
def ui_loginpage_empty(browser_session, ui_user):
    """Fixture factory to navigate to the login page."""
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


@pytest.fixture()
def ui_loginpage(ui_loginpage_empty, ui_user):
    """Fixture factory to navigate to the login and fill in the username."""
    def _():
        browser, login = ui_loginpage_empty()
        login.username.fill(ui_user['username'])
        return browser, login
    return _


@pytest.fixture
def ui_dashboard(browser_session, ui_loginpage, ui_user):
    """Fixture to navigate to the dashboard by logging in."""
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


@pytest.fixture
def ui_acct_list(browser_session, ui_loginpage, ui_user):
    """Fixture to navigate to the account list by logging in."""
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


@pytest.fixture
def ui_addacct_page1(browser_session, ui_dashboard):
    """Open the Add Account dialog."""
    selenium = browser_session
    browser, login = ui_dashboard

    browser.refresh()
    time.sleep(0.25)

    btn_add_account = find_element_by_text(selenium, 'Add Account')
    btn_add_account.click()

    dialog = selenium.find_element_by_css_selector('[role=dialog]')

    return {
        'dialog': dialog,
        'dialog_next': find_element_by_text(dialog, 'Next'),
    }


@pytest.fixture
def ui_addacct_page2(browser_session, ui_addacct_page1):
    """Navigate to the second page of the Add Account dialog."""
    selenium = browser_session
    profile_name = 'My Account'
    dialog = ui_addacct_page1['dialog']

    fill_input_by_label(selenium, dialog, 'Account Name', profile_name)
    ui_addacct_page1['dialog_next'].click()

    return ui_addacct_page1


@pytest.fixture
def ui_addacct_page3(ui_addacct_page2):
    """Navigate to the 3rd page of the dialog, with the ARN field."""
    dialog = ui_addacct_page2['dialog']
    dialog_next = ui_addacct_page2['dialog_next']

    dialog_next.click()

    dialog_add = find_element_by_text(dialog, 'Add')
    assert dialog_add.get_attribute('disabled')

    ui_addacct_page2['dialog_add'] = dialog_add
    return ui_addacct_page2
