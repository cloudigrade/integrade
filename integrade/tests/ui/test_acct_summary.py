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

import pytest

from .utils import find_element_by_text


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
