"""Unit tests for :mod:`integrade.config`."""
import os
import random
import time
from unittest import mock

import pytest

import xdg

import yaml

from integrade import config, exceptions, injector, utils

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
            deployment_prefix = random.choice([
                'aardvark',
                'aardvark-',
                'flying-aardvark-',
                '42',
                utils.uuid4(),
            ])
            os.environ['CLOUDIGRADE_TOKEN'] = token
            os.environ['CLOUDIGRADE_BASE_URL'] = 'example.com'
            os.environ['CLOUDIGRADE_ROLE_CUSTOMER1'] = '{}:{}:{}'.format(
                utils.uuid4(), account_number, utils.uuid4())
            os.environ['DEPLOYMENT_PREFIX'] = deployment_prefix
            os.environ['AWS_ACCESS_KEY_ID_CUSTOMER1'] = utils.uuid4()
            os.environ['USE_HTTPS'] = use_https
            os.environ['SSL_VERIFY'] = 'True' if ssl else 'False'
            cfg = config.get_config()
            bucket_name = f'{deployment_prefix}-cloudigrade-s3'
            assert cfg['superuser_token'] == token
            assert cfg['base_url'] == 'example.com'
            assert cfg['scheme'] == protocol
            assert cfg['ssl-verify'] == ssl
            assert cfg['api_version'] == 'v1'
            assert len(cfg['aws_profiles']) == 1
            assert cfg['aws_profiles'][0]['name'] == 'CUSTOMER1'
            assert cfg['aws_profiles'][0]['cloudtrail_name'] == (
                f'{deployment_prefix}{account_number}'
            )
            assert cfg['cloudigrade_s3_bucket'] == bucket_name


def test_negative_super_user_creation_fails():
    """Test that if super user creation fails, we get the right exception.

    If no super user token is provided, then config.get_config will call
    injector.make_super_user. If this fails, we want config.get_config
    to bail out with as informative of a message as possible, so tests
    can fail more gracefully and we can know what happened.

    This test ensures that if injector.make_super_user throws a RuntimeError,
    that config.get_config raises an exceptions.MissingConfigurationError so
    so that integrade.tests.conftest.check_superuser can catch that and let
    the user know what happened.
    """
    with mock.patch.object(config, '_CONFIG', None):
        with mock.patch.dict(os.environ, {}, clear=True):
            account_number = int(time.time())
            os.environ['CLOUDIGRADE_USER'] = 'bob'
            os.environ['CLOUDIGRADE_PASSWORD'] = 'bob123'
            os.environ['CLOUDIGRADE_BASE_URL'] = 'example.com'
            os.environ['CLOUDIGRADE_ROLE_CUSTOMER1'] = '{}:{}:{}'.format(
                utils.uuid4(), account_number, utils.uuid4())
            os.environ['DEPLOYMENT_PREFIX'] = 'flying-aardvark-'
            os.environ['AWS_ACCESS_KEY_ID_CUSTOMER1'] = utils.uuid4()
            with mock.patch.object(
                    injector, 'make_super_user') as make_super_user:
                make_super_user.side_effect = RuntimeError()
                with pytest.raises(exceptions.MissingConfigurationError):
                    config.get_config()


def test_negative_get_config_missing():
    """If a base url is specified in the environment, we use it."""
    with mock.patch.object(config, '_CONFIG', None):
        with mock.patch.dict(os.environ, {}, clear=True):
            with mock.patch.object(
                    injector, 'make_super_user') as make_super_user:
                make_super_user.return_value = utils.uuid4()
                os.environ['CLOUDIGRADE_ROLE_CUSTOMER1'] = '{}:{}:{}'.format(
                    utils.uuid4(), '1234', utils.uuid4())
                try:
                    config.get_config()
                except exceptions.MissingConfigurationError as e:
                    msg = str(e)
                    msg.replace('\n', ' ')
                    assert 'CLOUDIGRADE_BASE_URL' in msg
                    assert 'AWS access key id' in msg


def test_get_aws_image_config():
    """Test that the aws image config function parses the yaml correctly."""
    aws_image_config = yaml.load(MOCK_AWS_CONFIG)
    with mock.patch.object(config, '_CONFIG', {'fake': 'config'}):
        with mock.patch.object(xdg.BaseDirectory, 'load_config_paths') as lcp:
            lcp.return_value = ('fake_path',)
            with mock.patch.object(os.path, 'isfile') as isfile:
                isfile.return_value = True
                with mock.patch('builtins.open', mock.mock_open(
                        read_data=MOCK_AWS_CONFIG)):
                    assert config.get_aws_image_config() == aws_image_config


def test_raise_exception_missing_aws_image_config():
    """Test that when no aws_image_config file is present, an error is raised.

    This only occurs when the config.get_aws_image_config() function is called.
    """
    with mock.patch.object(config, '_AWS_CONFIG', None):
        with mock.patch.object(xdg.BaseDirectory, 'load_config_paths') as lcp:
            lcp.return_value = ('fake_path',)
            with mock.patch.object(os.path, 'isfile') as isfile:
                isfile.return_value = False
                with pytest.raises(exceptions.ConfigFileNotFoundError):
                    # pylint:disable=protected-access
                    config._get_config_file_path(utils.uuid4(), utils.uuid4())
        assert isfile.call_count == 1
