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
    find_element_by_text,
    find_elements_by_text,
    return_url,
)


def product_id_tag_present(driver, tag):
    """Return a boolean if the tag is found on the account detail screen.

    :param tag: Expects either RHEL or RHOCP

    Currently only can safely identify the tag if there is only one account.
    """
    time.sleep(0.5)
    results = driver.find_elements_by_xpath(
        '//div[contains(@class,\'list-view-pf-main-info\')]'
        f'//*[text()=\'{tag}\']'
    )
    if results:
        return results[0].is_displayed()
    else:
        return False


def test_empty(browser_session, u1_acct_list):
    """Test that accounts with no activity have no detail view.

    :id: fb671b8a-92b7-4493-b706-b13bf76036b2
    :description: Test accounts with no activity have no detail view.
    :steps:
        1) Create a user and a cloud account.
        2) Assert the account with no usage have no detail view.
    :expectedresults:
        Only accounts with usage have detail views.
    """
    selenium = browser_session
    clount = 'user1clount2'
    account = find_element_by_text(selenium, clount, timeout=1)
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
        1) Given a user and cloud account, mock usage for an image.
        2) Navigate to the account detail view.
        3) Assert that the image is listed.
        4) Assert that the image has the correct number of hours displayed.
    :expectedresults:
        The image used is listed in the detail view and has the hours
        used displayed correctly.
    """
    selenium = browser_session
    clount = 'user2clount3'
    account = find_element_by_text(selenium, clount, timeout=2)

    with return_url(selenium):
        account.click()
        time.sleep(1)
        ec2_ami_id = 'Joshua Perez-Access2'
        assert find_element_by_text(selenium, ec2_ami_id, exact=False,
                                    timeout=0.5)
        info_bar = browser_session.find_element_by_css_selector(
            '.cloudmeter-list-view-card'
        )
        assert find_element_by_text(info_bar, f'1RHEL', exact=False), \
            f'seen: {info_bar.get_attribute("innerText")}, ' \
            f'expected: 1 RHEL'


def test_image_flagging(browser_session, u2_acct_list):
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

    assert find_element_by_text(selenium, '3 Instances', timeout=1)

    account = find_element_by_text(selenium, 'user2clount1', timeout=0.5)

    account.click()
    time.sleep(1)

    # test data should be old so it's not updating/changing
    dropdown = find_element_by_text(selenium, 'Last 30 Days')
    dropdown.click()
    time.sleep(0.25)
    march = find_element_by_text(selenium, '2019 March')
    march.click()
    time.sleep(0.25)

    ami_id = selenium.find_elements_by_xpath(
        '//div/span/strong/span[text()="ami-31dda77f"]')
    ami_id[0].click()
    time.sleep(0.25)

    # Be sure to start test with nothing flagged:
    ctn = selenium.find_elements_by_xpath(
        '//div[@class="cloudmeter-list-container"]')
    ctn = ctn[0]
    flags = find_elements_by_text(ctn, 'Flagged for review')
    # flags is a list of nested divs that all contain the text 'Flagged for
    # review by virtue of their child dev containing the text. I only want
    # to click on the inner-most one. So of the 8 returned, the third and
    # seventh are the ones.
    if bool(flags):
        flags[3].click()
        flags[7].click()

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
    assert find_element_by_text(list_header, f'877RHEL', exact=False)
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
    assert find_element_by_text(list_header, f'N/ARHOCP', exact=False)
    # flag/challenge RHOCP
    rhocp_checkbox.click()
    time.sleep(0.25)
    # check that flagged, RHOCP displays hours and a flag
    assert find_element_by_text(list_header, f'2642RHOCP', exact=False)
    # check that the flag is present
    rhocp_flag = rhocp_ctn.find_elements_by_xpath(
        '//span/span[contains(@class, "fa-flag")]')
    assert bool(rhocp_flag)
