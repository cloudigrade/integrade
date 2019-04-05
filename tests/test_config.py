"""Unit tests for :mod:`integrade.config`."""
import os
import random
import time
from unittest import mock

import pytest

import yaml

from integrade import config, utils

MOCK_AWS_CONFIG = """
profiles:
  CUSTOMER1:
      images:
        rhel1:
            is_rhel: True
            image_id: 'ami-06545667'

        centos1:
            is_rhel: False
            image_id: 'ami-0c523432435'
"""


@pytest.mark.parametrize('ssl', [True, False])
@pytest.mark.parametrize('protocol', ['http', 'https'])
def test_get_config(ssl, protocol):
    """If a base url is specified in the environment, we use it."""
    with mock.patch.object(config, '_CONFIG', None):
        with mock.patch.dict(os.environ, {}, clear=True):
            token = utils.uuid4()
            use_https = 'True' if protocol == 'https' else 'False'
            account_number = int(time.time())
            cloudtrail_prefix = random.choice([
                'aardvark',
                'aardvark-',
                'flying-aardvark-',
                '42',
                utils.uuid4(),
            ])
            bucket_name = 'flying-aardvark-s3'
            os.environ['CLOUDIGRADE_TOKEN'] = token
            os.environ['CLOUDIGRADE_BASE_URL'] = 'example.com'
            os.environ['AWS_S3_BUCKET_NAME'] = bucket_name
            os.environ['CLOUDIGRADE_ROLE_CUSTOMER1'] = '{}:{}:{}'.format(
                utils.uuid4(), account_number, utils.uuid4())
            os.environ['CLOUDTRAIL_PREFIX'] = cloudtrail_prefix
            os.environ['AWS_ACCESS_KEY_ID_CUSTOMER1'] = utils.uuid4()
            os.environ['USE_HTTPS'] = use_https
            os.environ['SSL_VERIFY'] = 'True' if ssl else 'False'
            cfg = config.get_config()
            assert cfg['base_url'] == 'example.com'
            assert cfg['scheme'] == protocol
            assert cfg['ssl-verify'] == ssl
            assert cfg['api_version'] == 'v1'
            assert len(cfg['aws_profiles']) == 1
            assert cfg['aws_profiles'][0]['name'] == 'CUSTOMER1'
            assert cfg['aws_profiles'][0]['cloudtrail_name'] == (
                f'{cloudtrail_prefix[:-1]}{account_number}'
            )
            assert cfg['cloudigrade_s3_bucket'] == bucket_name


def test_get_aws_image_config():
    """Test that the aws image config function parses the yaml correctly."""
    aws_image_config = yaml.load(MOCK_AWS_CONFIG)
    with mock.patch.object(config, '_CONFIG', {'fake': 'config'}):
        with mock.patch.object(os.path, 'isfile') as isfile:
            isfile.return_value = True
            with mock.patch('builtins.open', mock.mock_open(
                    read_data=MOCK_AWS_CONFIG)):
                config._AWS_CONFIG = None  # reset cache to force reload
                assert config.get_aws_image_config() == aws_image_config
