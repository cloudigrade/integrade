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

from .utils import (
    fill_input_by_label,
    find_element_by_text,
    page_has_text,
)
from ...injector import (
    inject_aws_cloud_account,
    inject_instance_data,
)


def open_account_menu(browser_session, name):
    """Open the menu for a given account by name."""
    path = "./ancestor::*[contains(@class, 'list-group-item')]"
    el = find_element_by_text(browser_session, name)
    el = el.find_element_by_xpath(path)
    el.find_element_by_class_name('dropdown-toggle').click()


def test_edit_account_name(drop_account_data, browser_session, ui_dashboard,
                           ui_user):
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
    name1 = 'My Account'
    name2 = 'What now?!'

    inject_aws_cloud_account(ui_user['id'], name=name1)
    browser_session.refresh()
    sleep(0.25)

    open_account_menu(browser_session, name1)

    find_element_by_text(browser_session, 'Edit Name').click()
    fill_input_by_label(browser_session, None, 'Account Name', name2)
    find_element_by_text(browser_session, 'Save').click()

    assert not find_element_by_text(browser_session, name1)
    assert page_has_text(browser_session, name2)


def test_account_delete(
    cloud_account_data, browser_session, ui_user, ui_acct_list
):
    """Accounts can be deleted from the account summary list.

    :id: f941ac0f-ee46-4085-a92c-acff394fa6fe
    :description: The account menu includes a Delete option which prompts you
        before deleting the cloud account from your cloudigrade account.
    :steps:
        1) Click the menu icon on the account you'd like to delete
        2) Click "Delete" in the dropdown menu
        3) Click "Delete" in the confirmation dialog
    :expectedresults:
        The account should be removed from your list.
    """
    acct2 = inject_aws_cloud_account(ui_user['id'], 'Second Account')

    for i in range(3):
        cloud_account_data('', [40, 39], ec2_ami_id='image2')
        cloud_account_data('', [10], ec2_ami_id='image1')

    inject_instance_data(acct2['id'], '', [10], ec2_ami_id='image1')
    browser_session.refresh()

    find_element_by_text(browser_session, 'Second Account')

    open_account_menu(browser_session, 'Second Account')
    browser_session.execute_script(
        'window.scrollTo(0, document.body.scrollHeight);'
    )  # TODO: Move to a utility, but where?

    # Click delete in the dropdown
    find_element_by_text(browser_session, 'Delete').click()

    # Click delete in the confirmation dialog
    find_element_by_text(browser_session, 'Delete').click()

    browser_session.refresh()
    sleep(1)

    assert not find_element_by_text(browser_session, 'Second Account')
