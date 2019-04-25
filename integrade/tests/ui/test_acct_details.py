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
    expand,
    find_element_by_text,
    find_elements_by_text,
    return_url,
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
        2) Navigate to the clount2 detail view.
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
    info_bar = browser_session.find_element_by_css_selector(
        '.cloudmeter-list-view-card'
    )
    assert find_element_by_text(info_bar, f'672RHOCP', exact=False), \
        f'seen: {info_bar.get_attribute("innerText")}, '


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
    account = find_element_by_text(selenium, 'user2clount2', timeout=0.5)

    account.click()
    time.sleep(1)

    # test data should be old so it's not updating/changing
    back_in_time(selenium, 1)
    header_dropdown = selenium.find_elements_by_class_name(
        'list-view-pf-expand')[0]
    header_dropdown.click()
    time.sleep(0.5)

    list_header = selenium.find_elements_by_class_name(
        'list-group-item-header')
    list_header = list_header[0]
    # flaggable_text = selenium.find_elements_by_xpath('//div/h5/strong')

    # check RHEL UI details
    ctn_class = 'cloudmeter-accountview-list-view-item'
    ctn = browser_session.find_element_by_class_name(ctn_class)
    expand(selenium)
    rhel_ctn = ctn.find_elements_by_class_name('col-xs-6')[0]
    rhel_checkbox = rhel_ctn.find_elements_by_xpath(
        '//input[@type="checkbox"]')
    rhel_checkbox = rhel_checkbox[0]
    # check that unflagged, RHEL is not detected in the info bar
    assert find_element_by_text(list_header, f'N/ARHEL', exact=False)
    # flag/challenge RHEL
    rhel_checkbox.click()
    time.sleep(0.5)

    # check that flagged, RHEL displays flag and hours match on card and row
    cards = browser_session.find_elements_by_css_selector(
        '.cloudmeter-utilization-graph')[0]
    summary_row = browser_session.find_elements_by_css_selector(
        '.cloudmeter-accountview-list-view-item')[0]
    row_rhel = cards.find_elements_by_xpath(
        '//div[@class="cloudmeter-card-info"]')
    time.sleep(0.5)
    row_rhel = row_rhel[0].get_attribute('innerText')
    card_rhel_hours = summary_row.find_elements_by_xpath(
        '//div/span/strong[@data-test="rhel"]')[0]
    card_rhel_hours = card_rhel_hours.get_attribute('innerText')
    row_rhel_hours = [int(s) for s in row_rhel.split() if s.isdigit()][0]
    # Check that the card and summary row are reporting the same hours
    assert int(card_rhel_hours) == row_rhel_hours
    # check that the flag is present
    rhel_flag = rhel_ctn.find_elements_by_xpath(
        '//span/span[contains(@class, "fa-flag")]')
    assert bool(rhel_flag)

    # check RHOCP UI details
    unflag_everything(selenium)
    expand(selenium)
    list_header = selenium.find_elements_by_class_name(
        'list-group-item-header')
    list_header = list_header[0]
    dropdown = selenium.find_element_by_class_name(
        'list-view-pf-expand')
    dropdown.click()
    time.sleep(0.25)
    ctn_class = 'cloudmeter-accountview-list-view-item'
    ctn = browser_session.find_element_by_class_name(ctn_class)
    expand(selenium)
    rhocp_ctn = ctn.find_elements_by_class_name('col-xs-6')[1]
    rhocp_checkbox = rhocp_ctn.find_elements_by_xpath(
        '//input[@type="checkbox"]')
    rhocp_checkbox = rhocp_checkbox[1]
    # check that unflagged, RHOCP hours are detected in the info bar
    # This can't be specific number of hours because seed data is transient
    hours = list_header.get_attribute('innerText').split('\n')[5]
    assert int(hours)
    # flag/challenge RHOCP
    rhocp_checkbox.click()
    time.sleep(0.5)

    # check that flagged, RHOCP displays flag and hours match on card and row
    cards = browser_session.find_elements_by_css_selector(
        '.cloudmeter-utilization-graph')[1]
    summary_row = browser_session.find_elements_by_css_selector(
        '.cloudmeter-accountview-list-view-item')[0]
    row_rhocp = cards.find_elements_by_xpath(
        '//div[@class="cloudmeter-card-info"]')
    row_rhocp = row_rhocp[1].get_attribute('innerText')
    card_rhocp_hours = summary_row.find_elements_by_xpath(
        '//div/strong[@data-test="rhocp"]')[0]
    card_rhocp_hours = card_rhocp_hours.get_attribute('innerText')
    row_rhocp_hours = [int(s) for s in row_rhocp.split() if s.isdigit()][0]
    # Check that the card and summary row are reporting the same information
    assert row_rhocp_hours == 0
    assert card_rhocp_hours == 'N/A'
    # check that the flag is present
    rhocp_flag = rhocp_ctn.find_elements_by_xpath(
        '//span/span[contains(@class, "fa-flag")]')
    assert bool(rhocp_flag)
    unflag_everything(selenium)


def test_flag_icons_on_challenged_accounts(new_session, browser_session,
                                           u2_acct_list):
    """Presence of flag icon should correlate across accounts and images.

    :id: DC7F8495-FDFE-4B55-8B95-858E8021FA7A
    :description: Check that flags ARE or ARE NOT present for accounts
        accurately representing the status of their images
        (challenged/not challenged)

    :steps:
        1) Given a user with accounts, user2clount2, which has images capable
        of each combination of RHEL / Openshift and disputed / undisputed.
        2) Dispute images such that there are account instances of each of the
        following:
        Both RHEL and RHOCP, neither disputed
        Both RHEL and RHOCP, RHEL disputed
        Both RHEL and RHOCP, RHOCP disputed
        Both RHEL and RHOCP, both RHEL and RHOCP disputed
    :expectedresults:
        - Accounts with undisputed (non-flagged) images should have no flag
        - Accounts with a disputed (flagged) image should have a flag by the
        disputed image tag ('RHEL' or 'RHOCP')
        - Accounts with both RHEL and RHOCP disputes should have both flagged
    """
    selenium = browser_session
    back_in_time(selenium, 1)
    unflag_everything(selenium)
    flagged = False
    clount = 'user2clount2'
    long_css_selector = '.cloudmeter-accountview-list-view-item'
    # There are no flags on the account when nothing has been challenged
    # Specifically selecting user2clount2
    ctn = selenium.find_elements_by_css_selector(long_css_selector)[1]
    assert bool(ctn.find_elements_by_class_name('fa-flag')) == flagged
    account = find_element_by_text(selenium, clount, timeout=0.5)
    with return_url(selenium):
        account.click()
        time.sleep(1)

        # Challenge current tag
        check = 'Flag for review'
        header_dropdown = selenium.find_elements_by_class_name(
            'list-view-pf-expand')[0]
        header_dropdown.click()
        time.sleep(0.1)
        find_element_by_text(selenium, check, selector='label').click()

    # Go back to accounts page and see that flagging matches
    # (currently one (RHEL) flagged)
    time.sleep(1)
    ctn = selenium.find_elements_by_css_selector(long_css_selector)[1]
    flags = ctn.find_elements_by_class_name('fa-flag')
    assert bool(flags) != flagged
    assert len(flags) == 1

    # Challenge the other tag (so both are challenged)
    account = find_element_by_text(selenium, clount, timeout=0.5)
    with return_url(selenium):
        account.click()
        time.sleep(1)
        header_dropdown = selenium.find_elements_by_class_name(
            'list-view-pf-expand')[0]
        header_dropdown.click()
        time.sleep(0.5)
        find_element_by_text(selenium, check, selector='label').click()

    # Go back to accounts page and see that flagging matches
    # (currently two (RHEL and RHOCP) flagged)
    time.sleep(1)
    ctn = selenium.find_elements_by_css_selector(long_css_selector)[1]
    flags = ctn.find_elements_by_class_name('fa-flag')
    assert bool(flags) != flagged
    assert len(flags) == 2

    account = find_element_by_text(selenium, clount, timeout=0.5)
    with return_url(selenium):
        account.click()
        time.sleep(1)

        # Unchallenge first flagged item (RHEL)
        header_dropdown = selenium.find_elements_by_class_name(
            'list-view-pf-expand')[0]
        header_dropdown.click()
        time.sleep(0.5)
        find_element_by_text(selenium,
                             'Flagged for review', selector='label').click()
        time.sleep(1)

    # Go back to the accounts page and be sure that only one is flagged
    time.sleep(1)
    ctn = selenium.find_elements_by_css_selector(long_css_selector)[1]
    flags = ctn.find_elements_by_class_name('fa-flag')
    assert len(flags) == 1
