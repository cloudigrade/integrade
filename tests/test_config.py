"""Unit tests for :mod:`integrade.config`."""
import os
from unittest import mock

import pytest

from integrade import config, exceptions
from integrade.utils import uuid4


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


def test_get_config_negative():
    """Ensure an exception will be raised if a base URL isn't specified."""
    with mock.patch.object(config, '_CONFIG', None):
        with pytest.raises(exceptions.BaseUrlNotFound):
            os.environ.pop('CLOUDIGRADE_BASE_URL')
            config.get_config()
