"""Tests for account summary list.

:caseautomation: automated
:casecomponent: ui
:caseimportance: high
:caselevel: integration
:requirement: Cloud Meter
:testtype: functional
:upstream: yes
"""
import datetime
import time

import pytest

from integrade.injector import inject_instance_data
from integrade.tests.api.v1.test_list_accounts import create_cloud_account
from integrade.tests.utils import get_auth

from .utils import find_element_by_text


@pytest.fixture
def cloud_account(ui_user, drop_account_data, cloudtrails_to_delete):
    """Create a cloud account, return the auth object and account details."""
    create_response = create_cloud_account(get_auth(ui_user), 0, 'mine')
    return create_response


@pytest.fixture
def cloud_account_data(selenium, cloud_account):
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
        selenium.refresh()
        time.sleep(1)
    return factory


def test_empty(cloud_account_data, selenium, ui_acct_list):
    """Accounts should show 0 images and instances when empty for period."""
    assert find_element_by_text(selenium, '0 Images')
    assert find_element_by_text(selenium, '0 Instances')


@pytest.mark.parametrize(
    'start', (45, 31, 30, 29, 28, 15))
def test_running_start_times(start, cloud_account_data, selenium,
                             ui_acct_list):
    """At various start times instances should be counted for the period."""
    cloud_account_data('', [start])
    assert find_element_by_text(selenium, '1 Images')
    assert find_element_by_text(selenium, '1 Instances')


@pytest.mark.parametrize(
    'tag', ('', 'rhel', 'openshift', 'rhel,openshift'))
def test_running_tags(tag, cloud_account_data, selenium, ui_acct_list):
    """Tags should not affect counts."""
    cloud_account_data(tag, [10])
    assert find_element_by_text(selenium, '1 Images')
    assert find_element_by_text(selenium, '1 Instances')


def test_reused_image(cloud_account_data, selenium, ui_acct_list):
    """Multiple instances uses one image should be refelcted properly."""
    cloud_account_data('', [10], ec2_ami_id='image1')
    cloud_account_data('', [10], ec2_ami_id='image1')
    cloud_account_data('', [10], ec2_ami_id='image1')

    assert find_element_by_text(selenium, '1 Images')
    assert find_element_by_text(selenium, '3 Instances')


@pytest.mark.skip(reason='http://gitlab.com/cloudigrade/frontigrade/issues/67')
def test_last_event_time(cloud_account_data, selenium, ui_acct_list):
    """Multiple instances using a single image should be reflected properly."""
    when = datetime.datetime(2018, 8, 10, 9, 51)
    expected = 'Created 9:51AM, August 10th 2018'

    cloud_account_data('', [when], ec2_ami_id='image1')
    assert find_element_by_text(selenium, expected), selenium.page_source
