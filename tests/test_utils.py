"""Unit tests for :mod:`integrade.utils`."""
import os
import string
import time
from unittest.mock import patch

from integrade.utils import (
    base_url,
    flaky,
    gen_password,
    get_expected_hours_in_past_30_days,
    uuid4
)


def test_get_expected_hours_in_past_30_days():
    """Test that the utility calculates the hours correctly."""
    # assert that days outside 30 window generate 0 hours
    hours, spare_min, events = get_expected_hours_in_past_30_days([45, 30])
    assert hours == 0
    assert spare_min == 0
    assert events == [45, 30]

    hours, spare_min, events = get_expected_hours_in_past_30_days([45, 44])
    assert hours == 0
    assert spare_min == 0
    assert events == [45, 44]

    # assert that whole days in past work
    hours, spare_min, events = get_expected_hours_in_past_30_days([2, 1])
    assert hours == 24
    assert spare_min == 0
    assert events == [2, 1]

    # assert that multiple whole days in past work
    hours, spare_min, events = get_expected_hours_in_past_30_days([6, 4, 2, 1])
    assert hours == 72
    assert spare_min == 0
    assert events == [6, 4, 2, 1]

    # assert that when we cross the 30 day mark, we only get time
    # in period
    hours, spare_min, events = get_expected_hours_in_past_30_days([40, 29])
    assert hours == 24
    assert spare_min == 0
    assert events == [40, 29]

    # assert that when an instance is still running, the timezone is accounted
    # for because the browser makes the request in UTC of local time, so for
    # example, if it is noon in EST, then it is 4pm in UTC

    # offset is in seconds, convert to hours
    utc_offset = (time.localtime().tm_gmtoff) / (60 * 60)
    current_hours = time.localtime().tm_hour
    current_min = time.localtime().tm_min
    hours, spare_min, events = get_expected_hours_in_past_30_days([0, None])
    assert hours == current_hours - utc_offset
    assert spare_min == current_min
    assert events == [0]

    # Now include previous whole days inside the time period
    # offset is in seconds, convert to hours
    utc_offset = (time.localtime().tm_gmtoff) / (60 * 60)
    current_hours = time.localtime().tm_hour
    current_min = time.localtime().tm_min
    hours, spare_min, events = get_expected_hours_in_past_30_days(
        [5, 4, 0, None])
    assert hours == 24 + current_hours - utc_offset
    assert spare_min == current_min
    assert events == [5, 4, 0]

    # assert that when an instance is still running, but started before the
    # 30 days filter, the timezone is accounted for correctly. For example,
    # if the requests were from a browser using the EST timezone, the
    # beginning would be at 4 AM in UTC and the end is 4 hours later,
    # they cancel out.

    current_hours = time.localtime().tm_hour
    current_min = time.localtime().tm_min
    hours, spare_min, events = get_expected_hours_in_past_30_days([45, None])
    # 24 hours for the past 30 days plus the hours today
    assert hours == (24 * 30) + current_hours
    assert spare_min == current_min
    assert events == [45]


def test_gen_password():
    """Test gen_password generates password with printable string chars."""
    password = gen_password(30)
    assert len(password) == 30
    assert set(password).issubset(string.printable)


def test_uuid4():
    """Test we get a unique string each time we call uuid4()."""
    assert isinstance(uuid4(), str)
    assert uuid4() != uuid4()


def test_base_url():
    """Test base_url returns an URL with scheme and base_url."""
    cfg = {
        'scheme': 'https',
        'base_url': 'test.example.com',
    }
    assert base_url(cfg) == 'https://test.example.com'


def test_flaky():
    """Test that @flaky is only used on CI."""
    orig_ci = os.environ.get('CI')

    def my_function(): pass

    with patch('integrade.utils._flaky') as _flaky:
        os.environ['CI'] = ''
        flaky()(my_function)
        assert not _flaky.called

        os.environ['CI'] = 'yes'
        flaky()(my_function)
        assert _flaky.called

    os.environ['CI'] = orig_ci or ''
