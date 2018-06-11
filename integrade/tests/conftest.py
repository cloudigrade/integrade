"""Pytest customizations and fixtures for cloudigrae tests."""
import subprocess
from shutil import which

import pytest


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
        result = subprocess.run(['bash',
                                 '-c',
                                 'oc rsh -c postgresql $(oc get pods'
                                 ' -o jsonpath="{.items[*].metadata.name}" -l'
                                 ' name=postgresql) scl enable rh-postgresql96'
                                 ' -- psql -d cloudigrade -c'
                                 ' "truncate account_account cascade;"'],
                                stdout=subprocess.PIPE)
        assert result.returncode == 0
    else:
        pytest.skip('Must be able to drop account data for this test to work.'
                    'Make sure the "oc" client is in your PATH.')
