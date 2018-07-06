"""Pytest customizations and fixtures for cloudigrae tests."""
import atexit
import os
import subprocess
from multiprocessing import Pool
from shutil import which

import pytest

from integrade.tests.aws_utils import (
    delete_bucket_and_cloudtrail,
    delete_cloudtrail,
    terminate_instance,
)
from integrade.tests.ui.fixtures import (ui_dashboard,  # noqa: F401
    ui_loginpage, ui_loginpage_empty, ui_user)  # noqa: F401


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
    if which('oc'):
        py_script = b'from account.models import Account;\
        Account.objects.all().delete()'

        result = subprocess.run(['bash',
                                 '-c',
                                 'oc rsh -c cloudigrade-api $(oc get pods'
                                 ' -o jsonpath="{.items[*].metadata.name}" -l'
                                 ' name=cloudigrade-api)'
                                 ' scl enable rh-postgresql96 rh-python36'
                                 ' -- python manage.py shell'],
                                stdout=subprocess.PIPE,
                                input=py_script,
                                timeout=60
                                )
        assert result.returncode == 0
    else:
        pytest.skip('Must be able to drop account data for this test to work.'
                    'Make sure the "oc" client is in your PATH.')


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


# This section with the selenium fixture and its dependencies is a good
# candidate to extract into a reusable library in the near future.

DRIVERS = {}
BROWSERS = os.environ.get('UI_BROWSER', 'Chrome').split(',')


@pytest.fixture(params=BROWSERS)
def selenium(request):
    """Adjust the selenium fixture's browser size."""
    from selenium import webdriver

    force_saucelabs = os.environ.get('UI_USE_SAUCELABS', False)
    browser = request.param

    if browser in DRIVERS:
        return DRIVERS[browser]

    if force_saucelabs or browser in ('MicrosoftEdge', 'InternetExplorer'):
        tunnel = SauceLabsTunnel()
        tunnel.wait()

        cap = {
            'browserName': request.param,
        }
        user = os.environ['SAUCELABS_USERNAME']
        key = os.environ['SAUCELABS_KEY']
        url = _sauce_ondemand_url(user, key)
        driver = webdriver.Remote(desired_capabilities=cap,
                                  command_executor=url)
    elif browser == 'Firefox':
        driver = webdriver.Firefox()
    elif browser == 'Chrome':
        opt = webdriver.ChromeOptions()
        opt.add_argument('--headless')
        opt.add_argument('--no-sandbox')
        opt.add_argument('--disable-dev-shm-usage')
        driver = webdriver.Chrome(options=opt)

    driver.set_window_size(1200, 800)

    atexit.register(driver.close)

    DRIVERS[browser] = driver
    return driver


def _sauce_ondemand_url(saucelabs_user, saucelabs_key):
    """Get sauce ondemand URL for a given user and key."""
    return 'http://{0}:{1}@ondemand.saucelabs.com:80/wd/hub'.format(
        saucelabs_user, saucelabs_key)


class SauceLabsTunnel(object):
    """Manages a secure tunnel for Sauce Labs to reach our server."""

    def __init__(self):
        """Initialize the tunnel as not-ready."""
        self.ready = False

    def wait(self):
        """Start the tunnel and wait for it to be ready before returning."""
        key = os.environ['SAUCELABS_KEY']
        user = os.environ['SAUCELABS_USERNAME']
        args = 'sc --user %s --api-key %s --shared-tunnel' % (user, key)
        args = args.split()

        waiting = 2
        self.processing = subprocess.Popen(args, stdout=subprocess.PIPE)
        for line in self.processing.stdout:
            if b'you may start your tests' in line:
                waiting -= 1
                if waiting == 0:
                    self.ready = True
            if self.ready:
                break

    def close(self):
        """Terminate the saucelabs connections."""
        self.processing.terminate()


@pytest.fixture()
def cloudtrails_to_delete():
    """Provide list to test to indicate cloudtrails that should be terminated.

    We must know what aws profile to use, so append tuples of (aws_profile,
    cloudtrail_name) to the list.
    """
    cloudtrails_to_delete = []

    yield cloudtrails_to_delete

    if cloudtrails_to_delete:
        with Pool() as p:
            p.map(
                delete_cloudtrail, cloudtrails_to_delete)


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
