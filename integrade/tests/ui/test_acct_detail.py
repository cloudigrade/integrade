"""Tests for account summary list.

:caseautomation: automated
:casecomponent: ui
:caseimportance: high
:caselevel: integration
:requirement: Cloud Meter
:testtype: functional
:upstream: yes
"""
import random
import time
from random import randint, shuffle

import pytest

from integrade.constants import (
    CLOUD_ACCESS_AMI_NAME,
    CLOUD_ACCOUNT_NAME,
    MARKETPLACE_AMI_NAME,
)
from integrade.injector import (
    inject_aws_cloud_account,
    inject_instance_data,
)
from integrade.utils import (
    get_expected_hours_in_past_30_days,
    round_hours,
)

from .utils import (
    elem_parent,
    find_element_by_text,
    find_elements_by_text,
    get_el_text,
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


def inject_reasons(browser, account, list_of_reasons):
    """Inject the data based on the reason/reasons supplied."""
    ec2_ami_id = str(random.randint(100000, 999999999999))
    instance_id = str(randint(100000, 999999999999))
    image_type = ''
    if 'rhocp_detail_detected' in list_of_reasons:
        list_of_reasons.remove('rhocp_detail_detected')
        image_type = 'openshift'
    if 'is_cloud_access' in list_of_reasons:
        image_type = 'openshift'
        text = CLOUD_ACCESS_AMI_NAME
    elif 'is_marketplace' in list_of_reasons:
        text = MARKETPLACE_AMI_NAME
    else:
        text = ec2_ami_id
    rhel_reasons = {reason: True for reason in list_of_reasons}
    inject_instance_data(
        account['id'],
        image_type,
        [5, 1],
        ec2_ami_id=ec2_ami_id,
        instance_id=instance_id,
        **rhel_reasons
    )
    browser.refresh()
    find_element_by_text(browser, 'Hank', timeout=10).click()
    find_element_by_text(browser, text, timeout=10).click()


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
    account = find_element_by_text(selenium, CLOUD_ACCOUNT_NAME, timeout=1)
    account.click()
    assert find_element_by_text(
        selenium,
        'No instances available',
        exact=False,
        timeout=5,
    )
    # assert we are still on the account summary view
    assert find_element_by_text(selenium, CLOUD_ACCOUNT_NAME)


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

    instance_id = 'i-{}'.format(randint(1000, 99999))
    ec2_ami_id = 'ami-{}'.format(randint(1000, 99999))
    hours, spare_min, events = get_expected_hours_in_past_30_days(events)
    hours = round_hours(hours, spare_min)
    cloud_account_data(
        'rhel',
        events,
        instance_id=instance_id,
        ec2_ami_id=ec2_ami_id,
    )
    selenium.refresh()
    account = find_element_by_text(selenium, CLOUD_ACCOUNT_NAME, timeout=2)

    with return_url(selenium):
        account.click()
        time.sleep(1)
        assert find_element_by_text(selenium, ec2_ami_id, exact=False,
                                    timeout=0.5)
        info_bar = browser_session.find_element_by_css_selector(
            '.cloudmeter-list-view-card'
        )
        assert find_element_by_text(info_bar, f'{hours}RHEL', exact=False), \
            f'seen: {info_bar.get_attribute("innerText")}, ' \
            f'expected: {hours} RHEL'


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
    hours = round_hours(hours, spare_min)
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

        rhel = 0
        rhocp = 0

        if 'rhel' in tag:
            rhel = hours
        if 'openshift' in tag:
            rhocp = hours

        assert find_element_by_text(selenium, f'{rhel}RHEL', exact=False)
        assert find_element_by_text(selenium, f'{rhocp}RHOCP', exact=False)

        assert find_element_by_text(selenium, ec2_ami_id, exact=False)


@pytest.mark.parametrize('tag', ['rhel', 'openshift'])
@pytest.mark.parametrize('flagged', [True, False],
                         ids=['flagged', 'notflagged'])
def test_image_flagging(cloud_account_data, browser_session,
                        ui_acct_list, tag, flagged):
    """Flagging images should negate the detected states w/ proper indication.

    :id: 5c9b8d7c-9b0d-43b5-ab1a-220556adf99c
    :description: Test flagging both detected and undetected states for RHEL
        and Openshfit.
    :steps:
        1) Given a user and cloud account, mock an image with some usage for
           each combination of RHEL and Openshift being detected or undetected
           by cloudigrade.
        2) For each tag flag the detected state
    :expectedresults:
        - For either detected or undetected states the label should appear
        - Once flagged, a flag should be added
        - The graph should be updated with new data
    """
    selenium = browser_session

    instance_id = 'i-{}'.format(randint(1000, 99999))
    ec2_ami_id = 'ami-{}'.format(randint(1000, 99999))
    hours, spare_min, events = get_expected_hours_in_past_30_days([2, 1])
    hours = round_hours(hours, spare_min)
    cloud_account_data(
        tag,
        events,
        instance_id=instance_id,
        ec2_ami_id=ec2_ami_id,
        challenged=flagged,
    )
    selenium.refresh()
    assert find_element_by_text(selenium, '1 Instances', timeout=1)

    account = find_element_by_text(selenium, CLOUD_ACCOUNT_NAME, timeout=0.5)
    with return_url(selenium):
        account.click()
        time.sleep(1)

        if 'rhel' == tag:
            label = 'RHEL'
        elif 'openshift' == tag:
            label = 'RHOCP'
        else:
            raise RuntimeError(
                'Test did not expect tag parameter: %r' % (tag,)
            )

        if flagged:
            check = 'Flagged for review'
        else:
            check = 'Flag for review'

        ctn = selenium.find_element_by_css_selector('.list-view-pf-main-info')
        assert product_id_tag_present(selenium, label)
        assert bool(ctn.find_elements_by_class_name('fa-flag')) == flagged

        image_id_el = find_element_by_text(selenium, ec2_ami_id)
        image_id_el.click()
        time.sleep(0.1)
        info = elem_parent(
            find_element_by_text(ctn, f'{label}', exact=False)
        )
        tags_before = len(find_elements_by_text(ctn, label))
        hours_before = get_el_text(info)

        find_element_by_text(selenium, check, selector='label').click()
        time.sleep(1)

        info = elem_parent(
            find_element_by_text(ctn, f'{label}', exact=False)
        )
        tags_after = len(find_elements_by_text(ctn, label))
        hours_after = get_el_text(info)

        assert bool(ctn.find_elements_by_class_name('fa-flag')) != flagged
        assert tags_after == tags_before
        assert hours_before != hours_after


def test_flag_icons_on_challenged_accounts(cloud_account_data, browser_session,
                                           ui_acct_list):
    """Presence of flag icon should correlate across accounts and images.

    :id: DC7F8495-FDFE-4B55-8B95-858E8021FA7A
    :description: Check that flags ARE or ARE NOT present for accounts
        accurately representing the status of their images
        (challenged/not challenged)

    :steps:
        1) Given a user with accounts, mock an account with images for
        each combination of RHEL / Openshift and disputed / undisputed.
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
    flagged = False
    instance_id = 'i-{}'.format(randint(1000, 99999))
    ec2_ami_id = 'ami-{}'.format(randint(1000, 99999))
    hours, spare_min, events = get_expected_hours_in_past_30_days([2, 1])
    hours = round_hours(hours, spare_min)
    long_css_selector = '.cloudmeter-accountview-list-view-item'
    cloud_account_data(
        'rhel',
        events,
        instance_id=instance_id,
        ec2_ami_id=ec2_ami_id,
        challenged=flagged,
    )
    selenium.refresh()
    time.sleep(0.5)
    # There are no flags on the account when nothing has been challenged
    ctn = selenium.find_element_by_css_selector(long_css_selector)
    assert bool(ctn.find_elements_by_class_name('fa-flag')) == flagged
    account = find_element_by_text(selenium, CLOUD_ACCOUNT_NAME, timeout=0.5)
    with return_url(selenium):
        account.click()
        time.sleep(1)

        # Challenge current tag
        check = 'Flag for review'
        image_id_el = find_element_by_text(selenium, ec2_ami_id)
        image_id_el.click()
        time.sleep(0.1)
        find_element_by_text(selenium, check, selector='label').click()

    # Go back to accounts page and see that flagging matches
    # (currently one flagged)
    time.sleep(1)
    ctn = selenium.find_element_by_css_selector(long_css_selector)
    flags = ctn.find_elements_by_class_name('fa-flag')
    assert bool(flags) != flagged
    assert len(flags) == 1

    # Challenge the other tag (so both are challenged)
    account = find_element_by_text(selenium, CLOUD_ACCOUNT_NAME, timeout=0.5)
    with return_url(selenium):
        account.click()
        time.sleep(1)
        image_id_el = find_element_by_text(selenium, ec2_ami_id)
        image_id_el.click()
        time.sleep(0.5)
        find_element_by_text(selenium, check, selector='label').click()

    # Go back to accounts page and see that flagging matches
    # (currently two flagged)
    time.sleep(1)
    ctn = selenium.find_element_by_css_selector(long_css_selector)
    flags = ctn.find_elements_by_class_name('fa-flag')
    assert bool(flags) != flagged
    assert len(flags) == 2

    # Check flagging where 1 image flagged for RHEL and 1 other image
    # flagged for RHOCP
    # Create second image in same account
    second_ec2_ami_id = 'ami-{}'.format(randint(1000, 99999))
    cloud_account_data(
        'rhocp',
        [5],
        instance_id='i-{}'.format(randint(1000, 99999)),
        ec2_ami_id=second_ec2_ami_id,
    )
    selenium.refresh()
    time.sleep(0.5)
    account = find_element_by_text(selenium, CLOUD_ACCOUNT_NAME, timeout=0.5)
    with return_url(selenium):
        account.click()
        time.sleep(1)

        # Unchallenge second flagged item in first image
        image_id_el = find_element_by_text(selenium, ec2_ami_id)
        image_id_el.click()
        time.sleep(0.5)
        find_element_by_text(selenium,
                             'Flagged for review', selector='label').click()
        time.sleep(1)
        image_id_el.click()
        time.sleep(0.5)

        # Challenge second item in second image
        second_image_id_el = find_element_by_text(selenium, second_ec2_ami_id)
        second_image_id_el.click()
        time.sleep(0.5)
        find_element_by_text(selenium, check, selector='label').click()

    # Go back to the accounts page and be sure that both are flagged
    time.sleep(1)
    ctn = selenium.find_element_by_css_selector(long_css_selector)
    flags = ctn.find_elements_by_class_name('fa-flag')
    assert len(flags) == 2


def test_reused_image(cloud_account_data, browser_session, ui_acct_list):
    """Multiple instances uses one image should be reflected properly."""
    selenium = browser_session
    with return_url(selenium):
        events = [1, None]
        hours, spare_min, events = get_expected_hours_in_past_30_days(events)
        num_instances = randint(2, 5)
        hours = round_hours(hours * num_instances, spare_min * num_instances)
        ec2_ami_id = 'ami-{}'.format(randint(1000, 99999))

        for _ in range(num_instances):
            cloud_account_data('rhel', events, ec2_ami_id=ec2_ami_id)
        selenium.refresh()
        account = find_element_by_text(selenium, CLOUD_ACCOUNT_NAME,
                                       timeout=0.5)
        assert find_element_by_text(
            selenium,
            f'{num_instances} Instances',
            exact=False)
        account.click()

        time.sleep(1)

        ctn = selenium.find_element_by_css_selector('.list-view-pf-main-info')
        hours_el = find_element_by_text(ctn, f'RHEL', exact=False)
        hours_txt = hours_el.get_attribute('innerText')

        assert find_element_by_text(selenium, ec2_ami_id, exact=False)
        label = f'{hours}RHEL'
        assert find_element_by_text(selenium, label, exact=False),\
            f'"{hours} RHEL" expected; instead, saw "{hours_txt}"'


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
        hours = round_hours(hours, spare_min)
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
        ctn = selenium.find_element_by_css_selector('.list-view-pf-main-info')
        hours_el = find_element_by_text(ctn, f'RHEL', exact=False)
        hours_txt = hours_el.get_attribute('innerText')

        assert find_element_by_text(ctn, ec2_ami_id, exact=False)
        label = f'{hours}RHEL'
        assert find_element_by_text(ctn, label, exact=False),\
            f'"{hours} RHEL" expected; instead, saw "{hours_txt}"'


def test_reasons(cloud_account_data, browser_session,
                 ui_acct_list, drop_account_data, ui_user):
    """Test that when RHEL/RHOCP is detected, reasons for detection display.

    :id: c00be604-7428-4320-b9c7-e51bdb9e194d
    :description: When RHEL/RHOCP are detected, one or more reasons are
        returned with the inspection_json. The reasons should be visible
        in the account details. No reason should display if neither is
        detected. No negative reasons ever display.
    :steps:
        1) Given a user with an account, mock images with RHEL detected with
        each of the following 'reasons' and combinations thereof
        (1, 2, 3, and all 4 of the reasons):
            * rhel_enabled_repos_found
            * rhel_product_certs_found
            * rhel_release_files_found
            * rhel_signed_packages_found
        2) Given a user with an account, mock images with RHOCP detected with
        the following 'reason':
            * openshift_detected
    :expectedresults:
        When either is detected, a reason or reasons will display.
        When nothing is detected for either, no reasons will display.
    """
    selenium = browser_session
    account = inject_aws_cloud_account(ui_user['id'], name='Hank')
    repos = 'rhel_enabled_repos_found'
    certs = 'rhel_product_certs_found'
    files = 'rhel_release_files_found'
    pkges = 'rhel_signed_packages_found'
    certificate = 'product certificate is detected in /etc/pki/product'
    repositories = 'Active RHEL repositories are detected'
    packages = 'repositories are signed by the Red Hat GPG key'
    rhel_files = 'information is found in one or more /etc/*-release files'

    # Check for Cloud Access reason
    is_cloud_access = 'is_cloud_access'
    inject_reasons(selenium, account, [is_cloud_access])
    container_text = 'Red Hat Enterprise Linux is detected'
    ctn = find_element_by_text(selenium, container_text, timeout=10)
    el = ctn.find_element_by_xpath('..')
    cloud_access_reason = 'Cloud Access enabled subscriptions are found'
    assert find_element_by_text(el, cloud_access_reason, exact=False)

    #  Check for Marketplace reason
    is_marketplace = 'is_marketplace'
    inject_reasons(selenium, account, [is_marketplace])
    container_text = 'Red Hat Enterprise Linux is not detected'
    ctn = find_element_by_text(selenium, container_text, timeout=10)
    el = ctn.find_element_by_xpath('..')
    marketplace_reason = 'products that are billed through AWS Marketplace'
    assert find_element_by_text(el, marketplace_reason, exact=False)

    # Check for Openshift reason
    rhocp_reason = 'rhocp_detail_detected'
    inject_reasons(selenium, account, [rhocp_reason])
    container_text = 'Red Hat OpenShift Container Platform is detected'
    ctn = find_element_by_text(selenium, container_text, timeout=10)
    el = ctn.find_element_by_xpath('..')
    openshift_reason = 'cloudigrade-ocp-present custom tag is found'
    assert find_element_by_text(el, openshift_reason, exact=False)

    # Check for RHEL reasons
    reasons = [repos, certs, files, pkges]
    shuffle(reasons)  # randomized to reduce number of tests
    reasons_to_inject = []
    counter = 4
    for num in range(1, counter + 1):
        reasons_to_inject = reasons[:num]
        inject_reasons(selenium, account, reasons_to_inject)
        ctn = find_element_by_text(
                selenium,
                'Red Hat Enterprise Linux is detected',
                exact=False
                )
        if certs in reasons_to_inject:
            el = ctn.find_element_by_xpath('..')
            assert find_element_by_text(el, certificate, exact=False)
        if repos in reasons_to_inject:
            el = ctn.find_element_by_xpath('..')
            assert find_element_by_text(el, repositories, exact=False)
        if packages in reasons_to_inject:
            el = ctn.find_element_by_xpath('..')
            assert find_element_by_text(el, packages, exact=False)
        if files in reasons_to_inject:
            el = ctn.find_element_by_xpath('..')
            assert find_element_by_text(el, rhel_files, exact=False)
        # Check that no other reasons appear
        list_ctn = ctn.find_elements_by_xpath(
                        "//*[@class='cloudmeter-list']/li")
        assert len(list_ctn) == num
