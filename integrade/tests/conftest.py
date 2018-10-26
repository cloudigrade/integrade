"""Pytest customizations and fixtures for cloudigrade tests."""
import atexit
import os
import subprocess
from multiprocessing import Pool
from time import time
from urllib.parse import urljoin

import pytest

from integrade import api, config, exceptions
from integrade.tests import urls, utils
from integrade.tests.aws_utils import (
    delete_bucket_and_cloudtrail,
    terminate_instance,
)


@pytest.fixture
def create_user_account():
    """Create a factory to create user accounts.

    This fixture creates a factory (a function) which will create a user
    account. Repeated calls will create return new users. All users created
    with this factory will delete any cloud accounts associated with the users
    after the test has run.

    Optional arguments can be passed as a dictionary:
        {'username': 'str', 'password': 'str', 'email': 'str'}

    If none are provided, values will be generated and returned.
    """
    users = []

    def factory(**kwargs):
        """Create a user, add it to our list of users, and return it."""
        user = utils.create_user_account(**kwargs)
        users.append(user)
        return user

    yield factory

    client = api.Client()

    for user in users:
        auth = utils.get_auth(user)
        while client.get(urls.CLOUD_ACCOUNT, auth=auth).json()['results']:
            account = client.get(
                urls.CLOUD_ACCOUNT, auth=auth).json()['results'][0]
            client.delete(urljoin(urls.CLOUD_ACCOUNT, str(account['id'])))


@pytest.fixture(scope='session', autouse=True)
def check_superuser():
    """Ensure that we have a valid superuser for the test run."""
    try:
        config.get_config()
        client = api.Client(response_handler=api.echo_handler)
        response = client.get(urls.AUTH_ME)
        assert response.status_code == 200, response.url
    except (AssertionError, exceptions.MissingConfigurationError) as e:
        pytest.fail('Super user creation must have failed. '
                    f'Error: {repr(e)}')


@pytest.fixture(scope='session', autouse=True)
def capture_logs():
    """Capture logs from openshift after test session."""
    yield
    if os.environ.get('SAVE_CLOUDIGRADE_LOGS'):
        subprocess.run(['scripts/save-openshift-logs.sh'],
                       stdout=subprocess.PIPE,
                       stderr=subprocess.PIPE,
                       timeout=60
                       )


T = 0
TIMINGS = {}


def timemetric(name):
    """Create a timer context to record blocks of time."""
    return TimeMetricContext(name)


class TimeMetricContext:
    """Conext manager meausure the time blocks of code take.

    Each timer is given a name and all of the timers of the same name are added
    up and the total time can be reported at the end of the test via the
    report_timers() atexit callback.
    """

    def __init__(self, name):
        """Remember what named timer we're adding to."""
        self.name = name

    def __enter__(self):
        """Mark the time at the start of the timer entry."""
        self.start = time()

    def __exit__(self, *args):
        """Add the elapsed time to the appropriate timer."""
        self.end = time()
        TIMINGS.setdefault(self.name, 0)
        TIMINGS[self.name] += self.end - self.start


@atexit.register
def report_timers():
    """Report results of all timers."""
    for t in TIMINGS:
        print(f'Timer "{t}": {TIMINGS[t]:.2f}s')


@pytest.fixture()
def drop_account_data():
    """Drop non-user data from the database.

    We do not drop user data because we want to keep our super user, and tests
    should create new users. There is deduplicatoin of ARNs used to create
    cloud accounts, however, and we would like to re-use test data across
    different tests. For this reason, we can drop account data before a test
    runs by using this fixture.

    The side effect is that these tests cannot be run in parallel with any
    other tests. For that reason, mark any test using this fixture with
    "@pytest.mark.serial_only".
    """
    # global T
    # start = time()
    with timemetric('drop_account_data()'):
        utils.drop_account_data()
    # end = time()
    # T += (end - start)
    # print(f'T={T}')


@pytest.fixture()
def instances_to_terminate():
    """Provide list to test to indicate instances that should be terminated.

    We must know what aws profile to use, so append tuples of (aws_profile,
    instance_id) to the list.

    The cleanup code will run after the test even if it fails, so instance ids
    should be added to the list immediately after creation, so if something
    fails, they can be cleaned up.
    """
    instances_to_terminate = []

    yield instances_to_terminate

    if instances_to_terminate:
        with Pool() as p:
            p.map(
                terminate_instance, instances_to_terminate)


@pytest.fixture
def chrome_options(chrome_options):
    """Pass no sandbox to Chrome when running on Travis."""
    if not os.environ.get('UITEST_SHOW'):
        chrome_options.add_argument('headless')
    if os.environ.get('TRAVIS', 'false') == 'true':
        chrome_options.add_argument('--no-sandbox')
    return chrome_options


@pytest.fixture
def firefox_options(firefox_options):
    """Pass no sandbox to Chrome when running on Travis."""
    if not os.environ.get('UITEST_SHOW'):
        firefox_options.add_argument('-headless')
    return firefox_options


@pytest.fixture
def selenium(selenium):
    """Override pytest-selenium default by changing the browser window size."""
    selenium.set_window_size(1200, 800)
    return selenium


@pytest.fixture()
def cloudtrails_to_delete():
    """Provide list to test to indicate cloudtrails that should be terminated.

    We must know what aws profile to use, so append tuples of (aws_profile,
    cloudtrail_name) to the list.
    """
    cloudtrails_to_delete = []

    yield cloudtrails_to_delete

    utils.delete_cloudtrails(cloudtrails_to_delete)


@pytest.fixture()
def cloudtrails_and_buckets_to_delete():
    """Provide list to test to indicate cloudtrails and buckets to delete.

    We must know what aws profile to use, so append tuples of (aws_profile,
    cloudtrail_name, s3_bucket_name) to the list.
    """
    to_delete = []

    yield to_delete

    if to_delete:
        with Pool() as p:
            p.map(
                delete_bucket_and_cloudtrail, to_delete)
