"""Pytest customizations and fixtures for cloudigrae tests."""
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


@pytest.fixture
def chrome_options(chrome_options):
    """Pass no sandbox to Chrome when running on Travis."""
    chrome_options.add_argument('headless')
    if os.environ.get('TRAVIS', 'false') == 'true':
        chrome_options.add_argument('--no-sandbox')
    return chrome_options


@pytest.fixture
def firefox_options(firefox_options):
    """Pass no sandbox to Chrome when running on Travis."""
    firefox_options.add_argument('-headless')


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
