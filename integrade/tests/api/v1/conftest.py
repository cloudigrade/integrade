"""Shared fixtures for api tests."""
import pytest

from integrade.injector import direct_count_images
from integrade.tests.utils import (
    create_cloud_account,
    get_auth,
)


@pytest.fixture
def cloud_account(drop_account_data, cloudtrails_to_delete):
    """Create a cloud account, return the auth object and account details."""
    assert direct_count_images() == 0
    auth = get_auth()
    create_response = create_cloud_account(
            auth,
            0,
            cloudtrails_to_delete=cloudtrails_to_delete
        )
    return (auth, create_response)
