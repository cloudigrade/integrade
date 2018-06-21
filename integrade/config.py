"""Tools to manage global configuration of integrade."""
import os
from copy import deepcopy

from xdg import BaseDirectory

import yaml

from integrade import exceptions


# `get_config` uses this as a cache. It is intentionally a global. This design
# lets us do interesting things like flush the cache at run time or completely
# avoid a config file by fetching values from the UI.
_CONFIG = None
_AWS_CONFIG = None


def get_config():
    """Return a copy of the global config dictionary.

    This method makes use of a cache. If the cache is empty, the configuration
    file is parsed and the cache is populated. Otherwise, a copy of the cached
    configuration object is returned.

    :returns: A copy of the global integrade configuration object.
    """
    global _CONFIG  # pylint:disable=global-statement
    if _CONFIG is None:
        _CONFIG = {}
        _CONFIG['api_version'] = os.environ.get(
            'CLOUDIGRADE_API_VERSION', 'v1')
        _CONFIG['base_url'] = os.environ.get('CLOUDIGRADE_BASE_URL', '')
        # expect CLOUDIGRADE_CUSTOMER_ROLE_ARNS to be a whitespace delimitted
        # list of valid ARNs, each tied to a different AWS account
        _CONFIG['valid_roles'] = os.environ.get(
            'CLOUDIGRADE_CUSTOMER_ROLE_ARNS', '')
        if len(_CONFIG['valid_roles']) > 0:
            _CONFIG['valid_roles'] = _CONFIG['valid_roles'].split()
        else:
            _CONFIG['valid_roles'] = []
        if _CONFIG['base_url'] == '':
            raise exceptions.BaseUrlNotFound(
                'Make sure you have $CLOUDIGRADE_BASE_URL set in in'
                ' your environment.'
            )
        _CONFIG['superuser_token'] = os.environ.get('CLOUDIGRADE_TOKEN', None)
        if os.environ.get('USE_HTTPS', 'false').lower() == 'true':
            _CONFIG['scheme'] = 'https'
        else:
            _CONFIG['scheme'] = 'http'
        if os.environ.get('SSL_VERIFY', 'false').lower() == 'true':
            _CONFIG['ssl-verify'] = True
        else:
            _CONFIG['ssl-verify'] = False
    return deepcopy(_CONFIG)


def get_aws_config():
    """Return a copy of the global config dictionary.

    This method makes use of a cache. If the cache is empty, the configuration
    file is parsed and the cache is populated. Otherwise, a copy of the cached
    configuration object is returned.

    :returns: A copy of the global AWS configuration object.
    """
    global _AWS_CONFIG  # pylint:disable=global-statement
    if _AWS_CONFIG is None:
        with open(_get_config_file_path('integrade', 'aws_config.yaml')) as f:
            _AWS_CONFIG = yaml.load(f)
    return deepcopy(_AWS_CONFIG)


def _get_config_file_path(xdg_config_dir, xdg_config_file):
    """Search ``XDG_CONFIG_DIRS`` for a config file and return the first found.

    Search each of the standard XDG configuration directories for a
    configuration file. Return as soon as a configuration file is found. Beware
    that by the time client code attempts to open the file, it may be gone or
    otherwise inaccessible.

    :param xdg_config_dir: A string. The name of the directory that is suffixed
        to the end of each of the ``XDG_CONFIG_DIRS`` paths.
    :param xdg_config_file: A string. The name of the configuration file that
        is being searched for.
    :returns: A string. A path to a configuration file.
    :raises integrade.exceptions.ConfigFileNotFoundError: If the requested
        configuration file cannot be found.
    """
    path = BaseDirectory.load_first_config(xdg_config_dir, xdg_config_file)
    if path and os.path.isfile(path):
        return path
    raise exceptions.ConfigFileNotFoundError(
        'Integrade is unable to find an AWS configuration file. The following '
        '(XDG compliant) paths have been searched: ' + ', '.join([
            os.path.join(config_dir, xdg_config_dir, xdg_config_file)
            for config_dir in BaseDirectory.xdg_config_dirs
        ])
    )
