"""Unit tests for :mod:`integrade.config`."""
import os
from unittest import mock

import pytest

import xdg

import yaml

from integrade import config, exceptions
from integrade.utils import uuid4

MOCK_AWS_CONFIG = """
profiles:
  dev08:
      images:
        rhel1:
            is_rhel: True
            image_id: 'ami-06545667'

        centos1:
            is_rhel: False
            image_id: 'ami-0c523432435'
"""


@pytest.mark.parametrize('ssl', [True, False])
@pytest.mark.parametrize('roles', ['', 'one two three'])
@pytest.mark.parametrize('protocol', ['http', 'https'])
def test_get_config(ssl, protocol, roles):
    """If a base url is specified in the environment, we use it."""
    with mock.patch.object(config, '_CONFIG', None):
        token = uuid4()
        os.environ['CLOUDIGRADE_TOKEN'] = token
        os.environ['CLOUDIGRADE_BASE_URL'] = 'example.com'
        os.environ['CLOUDIGRADE_CUSTOMER_ROLE_ARNS'] = roles
        os.environ['USE_HTTPS'] = 'True' if protocol == 'https' else 'False'
        os.environ['SSL_VERIFY'] = 'True' if ssl else 'False'
        cfg = config.get_config()
        assert cfg['superuser_token'] == token
        assert cfg['base_url'] == 'example.com'
        assert cfg['scheme'] == protocol
        assert cfg['ssl-verify'] == ssl
        assert cfg['api_version'] == 'v1'
        if not roles:
            assert cfg['valid_roles'] == []
        else:
            assert cfg['valid_roles'] == roles.split()


def test_get_aws_config():
    """Test that the get_aws_config function parses the yaml correctly."""
    aws_config = yaml.load(MOCK_AWS_CONFIG)
    with mock.patch.object(xdg.BaseDirectory, 'load_config_paths') as lcp:
        lcp.return_value = ('fake_path',)
        with mock.patch.object(os.path, 'isfile') as isfile:
            isfile.return_value = True
            with mock.patch('builtins.open', mock.mock_open(
                    read_data=MOCK_AWS_CONFIG)):
                assert config.get_aws_config() == aws_config


def test_raise_exception_missing_aws_config():
    """Test that when no aws_config file is present, an exception is raised.

    This only occurs when the config.get_aws_config() function is called.
    """
    with mock.patch.object(config, '_AWS_CONFIG', None):
        with mock.patch.object(xdg.BaseDirectory, 'load_config_paths') as lcp:
            lcp.return_value = ('fake_path',)
            with mock.patch.object(os.path, 'isfile') as isfile:
                isfile.return_value = False
                with pytest.raises(exceptions.ConfigFileNotFoundError):
                    # pylint:disable=protected-access
                    config._get_config_file_path(uuid4(), uuid4())
        assert isfile.call_count == 1
