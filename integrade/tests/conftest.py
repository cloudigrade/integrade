"""Pytest customizations and fixtures for cloudigrae tests."""
import subprocess
from multiprocessing import Pool
from shutil import which

import pytest

from integrade.tests.aws_utils import terminate_instance


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
                                stdout=subprocess.PIPE, input=py_script)
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
        num_instances = len(instances_to_terminate)
        with Pool(num_instances) as p:
            p.map(
                terminate_instance, instances_to_terminate)
