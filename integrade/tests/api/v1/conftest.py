"""Shared fixtures for api tests."""
from datetime import datetime, time, timedelta

import pytest

from integrade import api, config
from integrade.injector import (
    clear_images,
    direct_count_images,
)
from integrade.tests import urls
from integrade.tests.utils import get_auth
from integrade.utils import uuid4


def get_time_range(offset=0):
    """Create start/end time for parameters to account report API."""
    fmt = '%Y-%m-%dT%H:%MZ'
    tomorrow = datetime.now().date() + timedelta(days=1 + offset)
    end = datetime.combine(tomorrow, time(4, 0, 0))
    start = end - timedelta(days=30)
    return start.strftime(fmt), end.strftime(fmt)


def create_cloud_account(auth, n, cloudtrails_to_delete):
    """Create a cloud account based on configured AWS customer info."""
    client = api.Client(authenticate=False)
    cfg = config.get_config()
    aws_profile = cfg['aws_profiles'][n]
    acct_arn = aws_profile['arn']
    cloud_account = {
        'account_arn': acct_arn,
        'name': uuid4(),
        'resourcetype': 'AwsAccount'
    }
    create_response = client.post(
        urls.CLOUD_ACCOUNT,
        payload=cloud_account,
        auth=auth
    )
    cloudtrails_to_delete.append(
            (aws_profile['name'], aws_profile['cloudtrail_name'])
            )
    assert create_response.status_code == 201
    clear_images(create_response.json()['id'])
    return create_response.json()


@pytest.fixture
def cloud_account(drop_account_data, cloudtrails_to_delete):
    """Create a cloud account, return the auth object and account details."""
    assert direct_count_images() == 0
    auth = get_auth()
    create_response = create_cloud_account(auth, 0, cloudtrails_to_delete)
    return (auth, create_response)
