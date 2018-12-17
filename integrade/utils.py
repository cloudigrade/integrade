"""Utility functions."""
import math
import os
import secrets
import string
import time
import uuid
from datetime import datetime
from urllib.parse import urlunparse

from flaky import flaky as _flaky


def get_expected_hours_in_past_30_days(events):
    """Given a list of events, return the number of hours of runtime.

    A list terminating in None will indicate that the instance is still
    running. For example [12, 10, 2, None] would indicate that the instance
    was turned on 12 days ago, turned off 10 days ago, turned on 2 days ago,
    and is still running.

    :returns: tuple of (hours, minutes, events). Only whole hours are
        displayed by UI, but several instances of the same image may accumulate
        enough minutes to form extra hours. This should be handled by the
        caller. The events are returned with any None items removed, as the
        integrade.injector.inject_instance_data does not use or understand
        None objects in the list of events.
    """
    hours = 0
    spare_min = 0
    utc_tomorrow = datetime.utcnow().date() > datetime.now().date()
    for i in range(1, len(events), 2):
        start = events[i - 1]
        end = events[i]
        these_hours, these_min = get_time_lapsed_in_past_30_days(start, end)
        hours += these_hours
        spare_min += these_min
    if None in events:
        events.remove(None)
    if utc_tomorrow:
        hours = hours - 24
    return hours, spare_min, events


def get_time_lapsed_in_past_30_days(start, end):
    """Get the number of hours and minutes in the past 30 days.

    The result is the number of hours and minutes of runtime total expected.

    None as the end argument indicates the instance is still running. start is
    capped at 30.

    The start and end arguments are an int number of days in the past in which
    the start or end event took place. For example, start and end values of 10
    and 3, respectively, would mean the machine was started 10 days ago and
    ended 3 days ago, and had run for 1 week (7 days, the difference of start
    and end).
    """
    utc_offset_hours = 0
    if start > 30:
        start = 30
    if start == 30:
        utc_offset_hours = (time.localtime().tm_gmtoff) / (60 * 60)
    if end is None:
        utc_offset_hours -= (time.localtime().tm_gmtoff) / (60 * 60)
        hours = (start * 24) + utc_offset_hours + time.localtime().tm_hour
        t = time.localtime()
        spare_min = t.tm_min + (t.tm_sec / 60)
        return int(hours), int(spare_min)
    elif end > 30:
        end = 30
    hours = (start - end) * 24

    return int(max(0, hours)), 0


def round_hours(hours, minutes):
    """Given a number of hours and minutes an instance ran, round up."""
    return math.ceil(hours + minutes / 60)


def base_url(cfg):
    """Generate the base URL based on the configuration."""
    return urlunparse((cfg['scheme'], cfg['base_url'], '', '', '', ''))


def gen_password(length=20):
    """Generate a random password with letters, digits and punctuation."""
    chars = string.ascii_letters + string.digits + string.punctuation
    return ''.join(
        secrets.choice(chars)
        for _ in range(length)
    )


def uuid4():
    """Provide unique string identifiers."""
    return str(uuid.uuid4())


def flaky(*args, **kwargs):
    """Wrap tests as flaky only on CI."""
    if os.environ.get('CI'):
        return _flaky(*args, **kwargs)
    else:
        return lambda f: f
