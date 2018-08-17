"""Tests for the Edit Account wizard interface.

:caseautomation: automated
:casecomponent: ui
:caseimportance: low
:caselevel: integration
:requirement: Cloud Meter
:testtype: functional
:upstream: yes
"""
from time import sleep

from integrade.injector import (
    inject_aws_cloud_account,
)

from .utils import (
    fill_input_by_label,
    find_element_by_text,
)


def test_edit_account_name(drop_account_data, selenium, ui_dashboard, ui_user):
    """The user can edit the name of an account which already exists.

    :id: 3a63ddbc-b153-415e-a6d1-b7255e0d1f80
    :description: An account on the dashboard can be given a new name.
    :steps:
        1) Open the dashboard logged in as a user who has at least 1 cloud
           account registered.
        2) Click the three-dot menu icon at the right of the account summary
        3) Click "Edit Name"
        4) Enter a different name and press "Save"
    :expectedresults: The account is now listed in the dashboard with the newly
        chosen name.
    """
    inject_aws_cloud_account(ui_user['id'], name='My Account')
    selenium.refresh()
    sleep(0.25)

    path = "./ancestor::*[contains(@class, 'list-group-item')]"
    el = find_element_by_text(selenium, 'My Account')
    el = el.find_element_by_xpath(path)
    el.find_element_by_class_name('dropdown-toggle').click()
    find_element_by_text(el, 'Edit Name').click()
    fill_input_by_label(selenium, None, 'Account Name', 'What now?!')
    find_element_by_text(selenium, 'Save').click()

    assert not find_element_by_text(selenium, 'My Account')
    assert find_element_by_text(selenium, 'What now?!')
