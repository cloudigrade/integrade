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

import pytest

from selenium.webdriver.common.keys import Keys

from .utils import (
    back_in_time,
    element_has_text,
    fill_input_by_placeholder,
    find_element_by_text,
    find_elements_by_text,
    page_has_text,
    unflag_everything,
)


def sum_usage(usage):
    """Sum up the total number of seconds from an usage list.

    :param usage: A list with an even number of items where each pair indicates
        instances' turn on and turn off events.
    :returns: the total number of seconds that an instance was running.
    """
    total_seconds = 0
    for start, end in zip(usage[0::2], usage[1::2]):
        total_seconds += (end - start).total_seconds()
    return total_seconds


def test_empty(new_session, browser_session, u1_acct_list):
    """Account summaries should shown 0 images and instances without data.

    :id: d23e7196-3139-4017-8d46-6d430c5c4f84
    :description: Looking at account summaries for a date range after creation
        but without any observed instances should show 0 counts.
    :steps:
        1) Log in as user1, which has no images/instances
    :expectedresults:
        Both images and instance should show 0 counts
    """
    assert find_element_by_text(
        browser_session,
        '0RHEL',
        timeout=2,
        exact=False), \
        f'{browser_session}'
    assert find_element_by_text(
        browser_session,
        '0RHOCP',
        timeout=2,
        exact=False), \
        f'{browser_session}'
    assert page_has_text(browser_session, '0 Images')
    assert page_has_text(browser_session, '0 Instances')


def test_summary_list_layout(new_session, browser_session, u2_acct_list):
    """Confirm aspects of the layout of elements on the summary list.

    :id: 873fb451-6ed7-4be4-9dfa-a8f0c22a4dfb
    :description: This test was created to check the behavior of long account
        names.
    :steps:
        1) Log in as user2, which has clounts with short and long names
        2) Check the lengths of both summary rows
    :expectedresults:
        - Confirm both lengths are equal
    """
    back_in_time(browser_session, 1)

    # Compare 'scrollWidth' of the 2nd and 3rd list-group-items.
    # The third is the one with the long name.
    a, b = browser_session.execute_script("""
    var items = document.querySelectorAll('.list-group-item')
    return [items[1].scrollWidth, items[2].scrollWidth]
    """)

    assert a == b
    assert find_element_by_text(browser_session, '1 Images', timeout=1)
    assert find_element_by_text(browser_session, '2 Instances')


def test_running_start_times(new_session, browser_session, u2_acct_list):
    """Instances left running from various days ago should count today.

    :id: e3f8972d-d1dc-4a59-950f-d7a5ad1491a5
    :description: An instance and its image should be counted if it was
        started in the past and has not yet been stopped.
    :steps:
        1) Log in as user2
        2) Clount2 has an instance event that has started and is still
        running and one that started, ended, then restarted and is still
        running.
    :expectedresults:
        - Confirm the instance and its image is counted once.
    """
    # Isolate the clount and its info bar
    clount2 = find_element_by_text(browser_session, 'user2clount2')
    div = clount2.find_element_by_xpath('../../../..')
    # Check that instances and images are correctly reported
    assert element_has_text(div, '1 Images')
    assert element_has_text(div, '2 Instances')


def test_running_tags(new_session, browser_session, u1_acct_list):
    """Tags on images should not affect image or instance counts in summaries.

    :id: e9ea3960-051d-47cd-a23b-013ad8deb243
    :description: The presence of tags should not affect image or instance
    counts, but should be reflected in the summaries themselves.
    :steps:
        1) Log on as user1
        2) Notes re: user1 seed data -
        images are a year old, so go back to this time last year in UI
        user1clount1image1 - private image
        user1clount2image1 - rhel detected, certs and rhocp detected = True
        user1clount2image2 - rhel detected, certs and rhel pkgs = True
        user1clount2image3 - all rhel reasons = true
    :expectedresults:
        - The image and instance counts should always be 1
        - The RHEL label should be 1 when the image has the rhel tag
        - The RHOCP label should be 1 when the image has the openshift tag
        - Both labels should be 1 when an image has both tags
    """
    browser_session.refresh()
    # this clount's images are old, so  go back to this time last year in UI
    back_in_time(browser_session, 12)
    time.sleep(0.25)
    assert find_element_by_text(browser_session, '3 Images', timeout=1)
    assert find_element_by_text(browser_session, '3 Instances')

    for level in ('summary', 'detail'):
        if level == 'detail':
            find_element_by_text(
                browser_session, 'user1clount2', timeout=1).click()
            time.sleep(1)
            assert find_element_by_text(browser_session,
                                        '48RHEL')
            assert find_element_by_text(browser_session, '150RHEL')
            assert find_element_by_text(browser_session,
                                        '4608RHOCP')
        else:
            assert find_element_by_text(browser_session, '0RHOCP')
            assert find_element_by_text(browser_session, '0RHEL')
            assert find_element_by_text(browser_session, '384RHEL')
            assert find_element_by_text(browser_session, '4608RHOCP')


def test_reused_image(new_session, browser_session, u2_acct_list):
    """An image used in multiple instance should only count once in summary.

    :id: 87a32f9c-da2c-4834-81d5-696b50433bf8
    :description: Multiple instances using the same image should not cause
        those images to be counted multiple times.
    :steps:
        1) Log on to user2
        2) user2clount2 has one image that has started and stopped multiple
        times.
    :expectedresults:
        There should be 1 Image and 2 Instances
    """
    # Isolate the clount and its info bar
    clount2 = find_element_by_text(browser_session, 'user2clount2')
    div = clount2.find_element_by_xpath('../../../..')
    # Check that instances and images are correctly reported
    assert element_has_text(div, '1 Images')
    assert element_has_text(div, '2 Instances')


@pytest.mark.skip(reason='http://gitlab.com/cloudigrade/frontigrade/issues/67')
def test_last_event_time(new_session, browser_session, u2_acct_list):
    """Account summaries show the date and time of the last observed event.

    :id: c6d5c52c-0640-4409-8b43-7beb600217d7
    :description: Each account should display including the time when the last
        instance was observed being powered on or off.
    :steps:
        1) Log on as user2
        2) TODO when issue 67 addressed
    :expectedresults:
        - The date should be the same date as the known power on event
    """
    expected = 'Created 9:51AM, August 10th 2018'

    browser_session.refresh()
    assert find_element_by_text(browser_session, expected, timeout=1), \
        browser_session.page_source


def test_account_name_filter(new_session, browser_session, u2_acct_list):
    """Account summary list can be filtered by name.

    :id: e8c290d0-481d-46c8-9da6-540ec4f8dc24
    :description: The filter should show matching accounts in the summary list.
    :steps:
        1) User2 has multiple cloud accounts with known and different names
        2) Enter a word in one account name, but not both, and apply the filter
        3) Click the link to clear the filters
    :expectedresults:
        The matching account should still be listed, the other account should
        not. When clearing the filter, both accounts should appear again.
    """
    assert find_element_by_text(browser_session, 'user2clount1', timeout=1)
    assert find_element_by_text(browser_session, 'user2clount2')

    input = fill_input_by_placeholder(
        browser_session, None,
        'Filter by Name', 'clount2')

    input.send_keys(Keys.RETURN)
    assert not find_element_by_text(browser_session, 'user2clount1')
    assert find_element_by_text(browser_session, 'user2clount2')

    input = fill_input_by_placeholder(
        browser_session, None,
        'Filter by Name', 'clount1')
    input.send_keys(Keys.RETURN)
    assert find_element_by_text(browser_session, 'user2clount1', timeout=1)
    assert not find_element_by_text(browser_session, 'user2clount2')

    find_element_by_text(browser_session, 'Clear All Filters').click()
    assert find_element_by_text(browser_session, 'user2clount1', timeout=1)
    assert find_element_by_text(browser_session, 'user2clount2')


def test_account_date_filter(new_session, browser_session, u1_acct_list):
    """The date dropdown should select and filter by previous months.

    :id: 4eacca3e-c1a1-4de1-a874-bf730cd5596b
    :description: The default date filter of "Last 30 Days" is a dropdown that
        lists the 12 previous months, each of which can be selected to filter
        the account summary list to results from that month.
    :steps:
        1) User1clount2 has no data available in the current month but has data
        available from a year ago
        2) Confirm that data does not show up in the default 30 days filter.
        3) Click the dropdown and select a year ago.
        4) Confirm the account list now reflects the appropriate counts.
    :expectedresults:
        The counts shown in the account summary should reflect images and
        instances as they were counted within the time frame of the selected
        date filter.
    """
    # Isolate the clount and its info bar
    clount2 = find_element_by_text(browser_session, 'user1clount2')
    div = clount2.find_element_by_xpath('../../../..')
    # Check that instances and images are correctly reported (should be none)
    assert find_element_by_text(div, '0 Images')
    assert find_element_by_text(div, '0 Instances')
    # No spaces because there are not spaces between the DOM nodes, even tho
    # they are rendered separately.
    assert find_element_by_text(div, '0RHEL')
    assert find_element_by_text(div, '0RHOCP')

    back_in_time(browser_session, 12)

    # Isolate the clount and its info bar
    clount2 = find_element_by_text(browser_session, 'user1clount2')
    div = clount2.find_element_by_xpath('../../../..')
    # Check that instances and images are correctly reported (should be some)
    assert find_element_by_text(div, '3 Images')
    assert find_element_by_text(div, '3 Instances')
    assert find_element_by_text(div, '384RHEL')
    assert find_element_by_text(div, '4608RHOCP')


DIM_INSTANCE = ('instance', 'Instance Hours')
DIM_MEMORY = ('gb', 'GB Memory Hours')
DIM_VCPU = ('cpu', 'Core Hours')


def test_summary_cards(new_session, browser_session, u2_acct_list):
    """Ensure the summary cards provide the summary usage information.

    :id: 53aeef62-79a8-4576-8cc5-b9dcc66d61b8
    :description: Test that the summary cards on the top of the accounts page
        show the summary usage information. The usage information must be the
        usage on the selected month and should only include RHEL and/or
        OpenShift usage.
    :steps:
        1) User2clount2 and user2clount3 have images and instances that ran
           across different months: 42 days ago, 1 month ago and the current
           month. User2clount1 includes usage from non RHEL and OpenShift, that
           should not be shown on the report.
        2) Select the past month as the usage period. Confirm the usage is
           reported as expected.
        3) Do the same for 2 months ago as the usage period. Confirm the usage
           is reported as expected.
        4) Click on summary row. Confirm that RHEL and RHOCP hours are as
           expected.
    :expectedresults:
        The usage report should count only RHEL and OpenShift hours. Any usage
        from a non RHEL or OpenShift image should not be considered.
    """
    # Expected results cards
    last_30_days = {
        'clount1_images': '1 Images',
        'clount1_instances': '3 Instances',
        'clount1_rhel_hours': '0RHEL',
        'clount1_rhocp_hours': '0RHOCP',
        'clount2_images': '1 Images',
        'clount2_instances': '2 Instances',
        'clount2_rhel_hours': '0RHEL',
        'clount2_rhocp_hours': '',  # seed data instance still running/changing
        'clount3_images': '2 Images',
        'clount3_instances': '2 Instances',
        'clount3_rhel_hours': '1RHEL',
        'clount3_rhocp_hours': '0RHOCP',
        'rhel_card': '1RHEL',
        'rhocp_card': '',  # seed data instance still running/changing
    }
    last_month = {
        'clount1_images': '1 Images',
        'clount1_instances': '3 Instances',
        'clount1_rhel_hours': '0RHEL',
        'clount1_rhocp_hours': '0RHOCP',
        'clount2_images': '1 Images',
        'clount2_instances': '2 Instances',
        'clount2_rhel_hours': '0RHEL',
        'clount2_rhocp_hours': '1392RHOCP',
        'clount3_images': '2 Images',
        'clount3_instances': '2 Instances',
        'clount3_rhel_hours': '1RHEL',
        'clount3_rhocp_hours': '0RHOCP',
        'rhel_card': '1RHEL',
        'rhocp_card': '1392RHOCP',
    }
    months_ago_2 = {
        'clount1_images': '0 Images',
        'clount1_instances': '0 Instances',
        'clount1_rhel_hours': '0RHEL',
        'clount1_rhocp_hours': '0RHOCP',
        'clount2_images': '1 Images',
        'clount2_instances': '2 Instances',
        'clount2_rhel_hours': '0RHEO',
        'clount2_rhocp_hours': '1488RHOCP',
        'clount3_images': '0 Images',
        'clount3_instances': '0 Instances',
        'clount3_rhel_hours': '0RHEL',
        'clount3_rhocp_hours': '0RHOCP',
        'rhel_card': '0RHEL',
        'rhocp_card': '1488RHOCP',
    }
    # Start the test with nothing flagged
    unflag_everything(browser_session)
    # Check data for last 30 days, last month, 2 months ago
    for i in range(3):
        # set variables for each time_frame (month in UI dropdown)
        if i == 0:
            t_frame = last_30_days
        elif i == 1:
            t_frame = last_month
            browser_session.refresh()
        elif i == 2:
            t_frame = months_ago_2
            browser_session.refresh()

        back_in_time(browser_session, i)
        time.sleep(1)
        cards = browser_session.find_elements_by_css_selector(
            '.cloudmeter-utilization-graph'
        )
        assert len(cards) == 2
        assert find_element_by_text(
            cards[0], f'{t_frame["rhel_card"]}', exact=False), \
            f"card text: {cards[0].get_attribute('innerText')}" \
            f"t_frame['rhel_card']: {t_frame['rhel_card']}"
        if i > 0:
            assert find_element_by_text(cards[1], f'{t_frame["rhocp_card"]}',
                                        exact=False)
        # Isolate clount2 and its info bar
        clount1 = find_element_by_text(browser_session, 'user2clount1')
        clount1_summary_row = clount1.find_element_by_xpath('../../../..')

        # Isolate clount2 and its info bar
        clount2 = find_element_by_text(browser_session, 'user2clount2')
        clount2_summary_row = clount2.find_element_by_xpath('../../../..')

        # Isolate clount3 and its info bar
        clount3 = find_elements_by_text(
            browser_session, 'user2clount3', exact=False)
        clount3_summary_row = clount3[19].find_element_by_xpath(
            '../../../../..')

        assert element_has_text(clount1_summary_row,
                                f'{t_frame["clount1_images"]}')
        assert element_has_text(clount1_summary_row,
                                f'{t_frame["clount1_instances"]}')
        assert element_has_text(clount2_summary_row,
                                f'{t_frame["clount2_images"]}')
        assert element_has_text(clount2_summary_row,
                                f'{t_frame["clount2_instances"]}')
        assert element_has_text(clount3_summary_row,
                                f'{t_frame["clount3_images"]}')
        assert element_has_text(clount3_summary_row,
                                f'{t_frame["clount3_instances"]}')
        assert find_element_by_text(
            clount3_summary_row, f'{t_frame["rhel_card"]}', exact=False)


def test_last_thirty_days(new_session, browser_session, u1_acct_list):
    """Test the treatment of runs that start and stop across the boundary.

    :id: db535c33-09f7-471d-afc3-5ca6dc16b33b
    :description: Test the treatment of runs that start and stop across the
        boundary.
    :steps:
        1) User1clount2image3 was running when the current 30 day window began
        and ended within it.
        2) Check that the runtime on the graphs and the summary rows match
    :expectedresults:
        - All the times should be the same
    """
    dropdown_choices = (
        'Instance Hours',
        'GB Memory Hours',
        'Core Hours',
    )
    for choice in dropdown_choices:
        cards = browser_session.find_elements_by_css_selector(
            '.cloudmeter-utilization-graph'
        )[0]
        summary_row = browser_session.find_elements_by_css_selector(
            '.cloudmeter-accountview-list-view-item'
        )[1]
        row_rhel = cards.find_elements_by_xpath(
            '//div[@class="cloudmeter-card-info"]')
        row_rhel = row_rhel[0].get_attribute('innerText')
        card_rhel_hours = summary_row.find_elements_by_xpath(
            '//div/span/strong[@data-test="rhel"]')
        card_rhel_hours = card_rhel_hours[1].get_attribute('innerText')
        row_rhel_hours = [int(s) for s in row_rhel.split() if s.isdigit()][0]
        # Check that the card and summary row are reporting the same hours
        assert int(card_rhel_hours) == row_rhel_hours
        if choice in ('Instance Hours', 'GB Memory Hours'):
            # Change dropdown to the next category
            next_selection = ''
            dropdown = find_element_by_text(cards, choice)
            assert dropdown
            dropdown.click()
            time.sleep(0.1)
            if choice == 'Instance Hours':
                next_selection = 'GB Memory Hours'
            elif choice == 'GB Memory Hours':
                next_selection = 'Core Hours'
            # Only click on to the next choice the first 2 times
            find_element_by_text(cards, next_selection).click()
            time.sleep(0.5)
        else:
            return
