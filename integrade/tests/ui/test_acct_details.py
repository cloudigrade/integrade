"""Tests for account summary list.

:caseautomation: automated
:casecomponent: ui
:caseimportance: high
:caselevel: integration
:requirement: Cloud Meter
:testtype: functional
:upstream: yes
"""

import time

from .utils import (
    back_in_time,
    find_element_by_text,
    find_elements_by_text,
    unflag_everything,
)


def product_id_tag_present(driver, tag):
    """Return a boolean if the tag is found on the account detail screen.

    :param tag: Expects either RHEL or RHOCP

    Currently only can safely identify the tag if there is only one account.
    """
    time.sleep(0.5)
    results = driver.find_elements_by_xpath(
        "//div[contains(@class,'list-view-pf-main-info')]"
        f"//*[text()='{tag}']"
    )
    if results:
        return results[0].is_displayed()
    else:
        return False


def test_empty(new_session, browser_session, u1_acct_list):
    """Test that accounts with no activity have no detail view.

    :id: fb671b8a-92b7-4493-b706-b13bf76036b2
    :description: Test accounts with no activity have no detail view.
    :steps:
        1) Logon to user1 account.
        2) Click on user1clount2.
        3) Assert the account with no usage have no detail view.
    :expectedresults:
        Only accounts with usage have detail views.
    """
    selenium = browser_session
    clount = 'user1clount2'
    account = find_element_by_text(selenium, clount, timeout=3)
    print('Account innerText: ')
    print(account.get_attribute('innerText'))
    account.click()
    assert find_element_by_text(
        selenium,
        'No instances available',
        exact=False,
        timeout=5,
    )
    # assert we are still on the account summary view
    assert find_element_by_text(selenium, 'user1@example.com')


def test_hours_image(new_session, u2_acct_list, browser_session):
    """Test that the account detail view displays correct data for images.

    :id: 2f666f93-5844-4bfb-b0bf-e31f856657a3
    :description: Test that the account detail view shows the detailed
        breakdown of hours used per image.
    :steps:
        1) Log in as user2.
        2) Navigate to the clount3 detail view.
        3) Assert that the image is listed.
        4) Assert that the image has the correct number of hours displayed.
    :expectedresults:
        The image used is listed in the detail view and has the hours
        used displayed correctly.
    """
    selenium = browser_session
    unflag_everything(selenium)
    back_in_time(selenium, 1)
    clount2 = find_elements_by_text(
        browser_session, 'user2clount2', exact=False)
    account = clount2[19].find_element_by_xpath(
        '../../../..')
    account.click()
    time.sleep(1)
    ec2_ami_id = 'ami-8f6ad3ef'
    assert find_element_by_text(selenium, ec2_ami_id, exact=False,
                                timeout=0.5)
    info_bar = browser_session.find_element_by_css_selector(
        '.cloudmeter-list-view-card'
    )
    assert find_element_by_text(info_bar, f'1364RHOCP', exact=False), \
        f'seen: {info_bar.get_attribute("innerText")}, ' \
        f'expected: 1 RHEL'


def test_image_flagging(new_session, browser_session, u2_acct_list):
    """Flagging images should negate the detected states w/ proper indication.

    :id: 5c9b8d7c-9b0d-43b5-ab1a-220556adf99c
    :description: Test flagging both detected and undetected states for RHEL
        and Openshfit.
    :steps:
        1) Given a user and cloud account and an image with some usage for
           each combination of RHEL and Openshift being detected or undetected
           by cloudigrade.
        2) For each tag flag the detected state
    :expectedresults:
        - For either detected or undetected states the label should appear
        - Once flagged, a flag should be added
        - The graph should be updated with new data
    """
    selenium = browser_session
    # Be sure to start test with nothing flagged:
    unflag_everything(selenium)
    assert find_element_by_text(selenium, '3 Instances', timeout=1.5)

    account = find_element_by_text(selenium, 'user2clount2', timeout=0.5)

    account.click()
    time.sleep(1)

    # test data should be old so it's not updating/changing
    back_in_time(selenium, 1)
    ami_id = selenium.find_elements_by_xpath(
        '// div/span/strong/span[text()="ami-8f6ad3ef"]')
    ami_id[0].click()
    time.sleep(0.25)

    list_header = selenium.find_elements_by_class_name(
        'list-group-item-header')
    list_header = list_header[0]
    flaggable_text = selenium.find_elements_by_xpath('//div/h5/strong')

    # check RHEL UI details
    rhel_text = flaggable_text[0]
    rhel_ctn = rhel_text.find_elements_by_xpath('../..')
    rhel_ctn = rhel_ctn[0]
    rhel_checkbox = rhel_ctn.find_elements_by_xpath(
        '//input[@type="checkbox"]')
    rhel_checkbox = rhel_checkbox[0]
    # check that unflagged, RHEL is not detected in the info bar
    assert find_element_by_text(list_header, f'N/ARHEL', exact=False)
    # flag/challenge RHEL
    rhel_checkbox.click()
    time.sleep(0.25)

    # check that flagged, RHEL displays hours and a flag
    assert find_element_by_text(list_header, f'744RHEL', exact=False)
    # check that the flag is present
    rhel_flag = rhel_ctn.find_elements_by_xpath(
        '//span/span[contains(@class, "fa-flag")]')
    assert bool(rhel_flag)

    # check RHOCP UI details
    rhocp_text = flaggable_text[1]
    rhocp_ctn = rhocp_text.find_elements_by_xpath('../..')
    rhocp_ctn = rhocp_ctn[0]
    rhocp_checkbox = rhocp_ctn.find_elements_by_xpath(
        '//input[@type="checkbox"]')
    rhocp_checkbox = rhocp_checkbox[1]
    # check that unflagged, RHOCP is not detected in the info bar
    assert find_element_by_text(list_header, f'1364RHOCP', exact=False)
    # flag/challenge RHOCP
    rhocp_checkbox.click()
    time.sleep(0.25)
    # check that flagged, RHOCP displays hours and a flag
    assert find_element_by_text(list_header, f'N/ARHOCP', exact=False)
    # check that the flag is present
    rhocp_flag = rhocp_ctn.find_elements_by_xpath(
        '//span/span[contains(@class, "fa-flag")]')
    assert bool(rhocp_flag)
