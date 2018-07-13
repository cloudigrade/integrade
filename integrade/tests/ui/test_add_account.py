import logging
import time

import pytest

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait

from integrade import api, config
from integrade.utils import get_primary_account_id
from .utils import find_element_by_text, wait_for_input_value, \
    wait_for_page_text, get_element_depth

from urllib.parse import urljoin
from integrade.tests.api.v1 import urls


logger = logging.getLogger(__name__)


@pytest.mark.skip()
def test_clearing_name(selenium, ui_dashboard, ui_user):
    browser, login = ui_dashboard

    btn_add_account = find_element_by_text(selenium, 'Add Account')
    btn_add_account.click()

    dialog = selenium.find_element_by_css_selector('[role=dialog]')
    dialog_next = find_element_by_text(dialog, 'Next')

    assert dialog_next.get_attribute('disabled')
    find_element_by_text(dialog, 'Account Name').click()
    input = selenium.execute_script('return document.activeElement')
    input.send_keys('My Account')

    assert not dialog_next.get_attribute('disabled')
    input.clear()
    assert dialog_next.get_attribute('disabled')


def test_add_account(drop_account_data, selenium, ui_dashboard, ui_user):
    browser, login = ui_dashboard

    profile_name = 'My Account'
    acct_arn = 'arn:aws:iam::543234867065:role/Cloud-Meter-role'

    btn_add_account = find_element_by_text(selenium, 'Add Account')
    btn_add_account.click()

    dialog = selenium.find_element_by_css_selector('[role=dialog]')
    dialog_next = find_element_by_text(dialog, 'Next')

    assert dialog_next.get_attribute('disabled')
    find_element_by_text(dialog, 'Account Name').click()
    input = selenium.execute_script('return document.activeElement')
    input.send_keys(profile_name)

    assert not dialog_next.get_attribute('disabled')
    dialog_next.click()

    dialog_next.click()

    dialog_add = find_element_by_text(dialog, 'Add')
    assert dialog_add.get_attribute('disabled')

    find_element_by_text(dialog, 'ARN').click()
    input = selenium.execute_script('return document.activeElement')
    input.send_keys(acct_arn)
    assert not dialog_add.get_attribute('disabled')

    dialog_add.click()

    wait = WebDriverWait(selenium, 30)
    wait.until(wait_for_page_text('My Account was created'))

    c = api.Client()
    r = c.get(urls.CLOUD_ACCOUNT).json()
    assert r['results'][0]['aws_account_id'] == get_primary_account_id()
    assert r['results'][0]['account_arn'] == 'arn:aws:iam::543234867065:role/Cloud-Meter-role'


def test_invalid_arn(drop_account_data, selenium, ui_dashboard, ui_user):
    browser, login = ui_dashboard
    wait = WebDriverWait(selenium, 10)

    profile_name = 'My Account'
    acct_arn = 'arn:aws:iam::543234867065:role/Cloud-Meter-role-WRONG'

    btn_add_account = find_element_by_text(selenium, 'Add Account')
    btn_add_account.click()

    dialog = selenium.find_element_by_css_selector('[role=dialog]')
    dialog_next = find_element_by_text(dialog, 'Next')

    assert dialog_next.get_attribute('disabled')
    find_element_by_text(dialog, 'Account Name').click()
    input = selenium.execute_script('return document.activeElement')
    input.send_keys(profile_name)

    assert not dialog_next.get_attribute('disabled')
    dialog_next.click()

    dialog_next.click()

    dialog_add = find_element_by_text(dialog, 'Add')
    assert dialog_add.get_attribute('disabled')

    find_element_by_text(dialog, 'ARN').click()
    input = selenium.execute_script('return document.activeElement')
    input.send_keys(acct_arn)
    assert not dialog_add.get_attribute('disabled')

    dialog_add.click()

    wait.until(wait_for_page_text('Permission denied for ARN'))
