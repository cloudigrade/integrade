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
from random import randint

import pytest

from integrade.injector import (
    inject_aws_cloud_account,
    inject_instance_data,
)
from integrade.utils import get_expected_hours_in_past_30_days

from .conftest import (
    CLOUD_ACCOUNT_NAME,
)
from .utils import (
    find_element_by_text,
)

INSTANCE_START = randint(1, 99)
INSTANCE_END = INSTANCE_START - randint(0, 45)
if INSTANCE_END < 0:
    INSTANCE_END = None


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


def test_empty(cloud_account_data, browser_session, ui_acct_list):
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
    account = find_element_by_text(selenium, CLOUD_ACCOUNT_NAME)
    account.click()
    assert find_element_by_text(
        selenium,
        'No instances available',
        exact=False,
        timeout=5,
    )
    # assert we are still on the account summary view
    assert find_element_by_text(selenium, CLOUD_ACCOUNT_NAME)


class return_url:
    """Conext manager to control return back to a URL after steps completed."""

    def __init__(self, browser):
        """Initialize with reference to the WebDriver."""
        self.browser = browser

    def __enter__(self):
        """Remember current URL before entering context."""
        self.url = self.browser.current_url

    def __exit__(self, *args):
        """Return to original URL outside context."""
        self.browser.get(self.url)


@pytest.mark.parametrize(
    'events', (
        # started two days ago, turned off 1 day ago
        [2, 1],
        # started 45 days ago, turned off 25 days ago
        [45, 25],
        # started 45 days ago, turned off 25 days ago
        # then started again and turned off again,
        # finally turned on and left on
        [45, 29, 15, 14, 1, None],
    )
)
def test_hours_image(events, cloud_account_data, browser_session,
                     ui_acct_list):
    """Test that the account detail view displays correct data for images.

    :id: 2f666f93-5844-4bfb-b0bf-e31f856657a3
    :description: Test the account detail view shows detail breakdown of hours
        used per image.
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

    instance_id = 'i-{}'.format(randint(1000, 99999))
    ec2_ami_id = 'ami-{}'.format(randint(1000, 99999))
    hours, spare_min, events = get_expected_hours_in_past_30_days(events)
    cloud_account_data(
        '',
        events,
        instance_id=instance_id,
        ec2_ami_id=ec2_ami_id)
    selenium.refresh()
    account = find_element_by_text(selenium, CLOUD_ACCOUNT_NAME, timeout=0.5)

    with return_url(selenium):
        account.click()
        assert find_element_by_text(selenium, ec2_ami_id, exact=False,
                                    timeout=0.5)
        hours_el = find_element_by_text(selenium, f'Hours', exact=False)
        assert find_element_by_text(selenium, f'{hours} Hours', exact=False), \
            f'seen: {hours_el.get_attribute("innerText")}, ' \
            'expected: {hours} Hours'


tag_names = ['No Tag', 'RHEL', 'Openshift', 'RHEL and Openshift']


@pytest.mark.parametrize('tag', ['', 'rhel', 'openshift', 'rhel,openshift'],
                         ids=tag_names)
@pytest.mark.parametrize(
    'events', ([2, 1],)
)
def test_image_tag(events, cloud_account_data, browser_session,
                   ui_acct_list, tag):
    """Test that the account detail view displays correct tags for images.

    :id: 20b060c0-c2f4-4864-bb71-239720ceaa8f
    :description: Test the account detail view shows correct tags for images.
    :steps:
        1) Given a user and cloud account, mock usage for an image.
        2) Navigate to the account detail view.
        3) Assert that the image is listed.
        4) Assert that the image has the correct number of hours displayed.
        5) Assert that the correct tags are displayed.
    :expectedresults:
        Image tags are displayed in the detail view and tags do not interfere
        with any listing of other data.
    """
    selenium = browser_session

    instance_id = 'i-{}'.format(randint(1000, 99999))
    ec2_ami_id = 'ami-{}'.format(randint(1000, 99999))
    hours, spare_min, events = get_expected_hours_in_past_30_days(events)
    cloud_account_data(
        tag,
        events,
        instance_id=instance_id,
        ec2_ami_id=ec2_ami_id)
    selenium.refresh()
    assert find_element_by_text(selenium, '1 Instances', timeout=1)

    account = find_element_by_text(selenium, CLOUD_ACCOUNT_NAME, timeout=0.5)
    with return_url(selenium):
        account.click()
        time.sleep(1)

        # now in detail view
        # assert that product identification tags are correctly displayed

        if tag == '':
            assert not product_id_tag_present(selenium, 'RHEL')
            assert not product_id_tag_present(selenium, 'RHOCP')

        if 'rhel' in tag:
            assert product_id_tag_present(selenium, 'RHEL')

        if 'openshift' in tag:
            assert product_id_tag_present(selenium, 'RHOCP')

        assert find_element_by_text(selenium, ec2_ami_id, exact=False)
        assert find_element_by_text(selenium, f'{hours} Hours', exact=False)


def test_reused_image(cloud_account_data, browser_session, ui_acct_list):
    """Multiple instances uses one image should be refelcted properly."""
    selenium = browser_session
    with return_url(selenium):
        events = [1, None]
        hours, spare_min, events = get_expected_hours_in_past_30_days(events)
        num_instances = randint(2, 5)
        hours = hours * num_instances + (spare_min * num_instances) // 60
        ec2_ami_id = 'ami-{}'.format(randint(1000, 99999))

        for _ in range(num_instances):
            cloud_account_data('', events, ec2_ami_id=ec2_ami_id)
        selenium.refresh()
        account = find_element_by_text(selenium, CLOUD_ACCOUNT_NAME,
                                       timeout=0.5)
        assert find_element_by_text(
            selenium,
            f'{num_instances} Instances',
            exact=False)
        account.click()
        time.sleep(1)
        assert find_element_by_text(selenium, ec2_ami_id, exact=False)
        assert find_element_by_text(selenium, f'{hours} Hours', exact=False)


@pytest.mark.parametrize(
    'events', (
        # started two days ago, turned off 1 day ago
        [2, 1],
        # started 45 days ago, turned off 25 days ago
        # then started again and turned off again,
        # finally turned on and left on
        [45, 29, 15, 14, 1, None],
    )
)
def test_multiple_accounts(
        events,
        drop_account_data,
        ui_user,
        ui_dashboard,
        browser_session):
    """Test that having multiple accounts does not interfere with detail view.

    :id: 8bc0e630-2f52-4c73-a46d-355a7f79e339
    :description: Test that having many accounts does not change how detail
        view works for a given individual account.
    :steps:
        1) Given a user and several cloud accounts, mock usage for an image
            associated with one of the accounts.
        2) Assert the accounts with no usage have no detail view.
        3) Navigate to the account detail view of the active account.
        4) Assert that the image is listed.
        5) Assert that the image has the correct number of hours displayed.
    :expectedresults:
        Only accounts with usage have detail views and having multiple accounts
        does not degrade any use of the detail view.
    """
    selenium = browser_session
    with return_url(selenium):

        ec2_ami_id = 'ami-{}'.format(randint(1000, 99999))
        hours, spare_min, events = get_expected_hours_in_past_30_days(events)
        accts = []
        num_accounts = 3
        active_account_indx = randint(0, num_accounts - 1)

        # inject aws accounts
        for _ in range(num_accounts):
            name = 'cloud_account_{}'.format(randint(1000000, 999999999))
            acct = inject_aws_cloud_account(ui_user['id'], name=name)
            accts.append(acct)

        selenium.refresh()
        time.sleep(1)

        # inject instance activity for the account
        account = accts[active_account_indx]
        inject_instance_data(
            account['id'],
            'rhel',
            events,
            ec2_ami_id=ec2_ami_id
        )
        selenium.refresh()
        time.sleep(1)

        for indx in range(len(accts)):
            acct = accts[indx]
            if indx != active_account_indx:
                account_bar = find_element_by_text(selenium, acct['name'])
                account_bar.click()
                assert find_element_by_text(
                    selenium,
                    'No instances available',
                    exact=False)

        account_bar = find_element_by_text(selenium, account['name'])
        assert account_bar
        account_bar.click()
        time.sleep(1)
        assert find_element_by_text(selenium, ec2_ami_id, exact=False)
        assert find_element_by_text(selenium, f'{hours} Hours', exact=False)
