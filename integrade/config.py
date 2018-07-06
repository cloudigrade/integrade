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
        # pull all customer roles out of environ

        def is_role(string): return string.startswith('CLOUDIGRADE_ROLE_')

        def profile_name(string): return string.replace(
            'CLOUDIGRADE_ROLE_', '')

        profiles = [{'arn': os.environ.get(role),
                     'name': profile_name(role)}
                    for role in filter(is_role, os.environ.keys())
                    ]
        _CONFIG['aws_profiles'] = profiles

        missing_config_errors = []

        try:
            aws_image_config = get_aws_image_config()
        except exceptions.ConfigFileNotFoundError:
            aws_image_config = {}

        for profile in _CONFIG['aws_profiles']:
            profile_name = profile['name'].upper()
            acct_arn = profile['arn']
            acct_num = [
                num for num in filter(
                    str.isdigit,
                    acct_arn.split(':'))][0]
            profile['account_number'] = acct_num
            profile['cloudtrail_name'] = f'cloudigrade-{acct_num}'
            profile['access_key_id'] = os.environ.get(
                f'AWS_ACCESS_KEY_ID_{profile_name}')
            profile['access_key'] = os.environ.get(
                f'AWS_SECRET_ACCESS_KEY_{profile_name}')
            profile['images'] = aws_image_config.get('profiles', {}).get(
                profile_name, {}).get('images', [])

            if not profile['access_key_id']:
                missing_config_errors.append(
                    f'Could not find AWS access key id for {profile_name}')
            if not profile['access_key']:
                missing_config_errors.append(
                    f'Could not find AWS access key for {profile_name}')
        if _CONFIG['base_url'] == '':
            missing_config_errors.append(
                'Could not find $CLOUDIGRADE_BASE_URL set in in'
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

        if missing_config_errors:
            raise exceptions.MissingConfigurationError(
                '\n'.join(missing_config_errors)
            )
    return deepcopy(_CONFIG)


def get_aws_image_config():
    """Return a copy of the global config dictionary.

    This method makes use of a cache. If the cache is empty, the configuration
    file is parsed and the cache is populated. Otherwise, a copy of the cached
    configuration object is returned.

    :returns: A copy of the global AWS configuration object.
    """
    global _AWS_CONFIG  # pylint:disable=global-statement
    if _AWS_CONFIG is None:
        with open(_get_config_file_path('integrade',
                                        'aws_image_config.yaml')) as f:
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
