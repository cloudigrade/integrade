"""Tools to manage global configuration of integrade."""

import os
from copy import deepcopy

from xdg import BaseDirectory

import yaml

from integrade import exceptions, injector, utils


# `get_config` uses this as a cache. It is intentionally a global. This design
# lets us do interesting things like flush the cache at run time or completely
# avoid a config file by fetching values from the UI.
_CONFIG = None
_AWS_CONFIG = None


def get_config(create_superuser=True, need_base_url=True):
    """Return a copy of the global config dictionary.

    This method makes use of a cache. If the cache is empty, the configuration
    file is parsed and the cache is populated. Otherwise, a copy of the cached
    configuration object is returned.

    :returns: A copy of the global integrade configuration object.
    """
    global _CONFIG  # pylint:disable=global-statement
    if _CONFIG is None:
        _CONFIG = {}
        _CONFIG['api_version'] = os.getenv('CLOUDIGRADE_API_VERSION', 'v1')
        _CONFIG['cloudigrade_s3_bucket'] = os.getenv('AWS_S3_BUCKET_NAME')

        cloudtrail_prefix = os.getenv('CLOUDTRAIL_PREFIX')
        ref_slug = os.environ.get('CI_COMMIT_REF_SLUG', '')

        # The location of the API endpoints and UI may be configured directly
        # with `CLOUDIGRADE_BASE_URL` -OR- we can determine a location based
        # on `CI_COMMIT_REF_SLUG` which comes from Gitlab CI and is our
        # current branch name.

        _CONFIG['base_url'] = os.getenv(
            'CLOUDIGRADE_BASE_URL',
            f'review-{ref_slug}.1b13.insights.openshiftapps.com',
        )

        _CONFIG['openshift_prefix'] = os.getenv(
            'OPENSHIFT_PREFIX',
            f'c-review-{ref_slug[:29]}-',
        )

        # pull all customer roles out of environ

        def is_role(string):
            return string.startswith('CLOUDIGRADE_ROLE_')

        def profile_name(string): return string.replace(
            'CLOUDIGRADE_ROLE_', '')

        profiles = [{'arn': os.environ.get(role),
                     'name': profile_name(role)}
                    for role in filter(is_role, os.environ.keys())
                    ]
        profiles.sort(key=lambda p: p['name'])
        _CONFIG['aws_profiles'] = profiles

        missing_config_errors = []

        try:
            aws_image_config = get_aws_image_config()
        except exceptions.ConfigFileNotFoundError:
            aws_image_config = {}

        for i, profile in enumerate(_CONFIG['aws_profiles']):
            profile_name = profile['name'].upper()
            acct_arn = profile['arn']
            acct_num = [
                num for num in filter(
                    str.isdigit,
                    acct_arn.split(':'))][0]
            profile['account_number'] = acct_num
            profile['cloudtrail_name'] = f'{cloudtrail_prefix}{acct_num}'
            profile['access_key_id'] = os.environ.get(
                f'AWS_ACCESS_KEY_ID_{profile_name}')
            profile['images'] = aws_image_config.get('profiles', {}).get(
                profile_name, {}).get('images', [])

            if i == 0:
                if not profile['access_key_id']:
                    missing_config_errors.append(
                        f'Could not find AWS access key id for {profile_name}')

        if _CONFIG['base_url'] == '' and need_base_url:
            missing_config_errors.append(
                'Could not find $CLOUDIGRADE_BASE_URL set in in'
                ' your environment.'
            )
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
        super_username = os.environ.get(
            'CLOUDIGRADE_USER', utils.uuid4()
        )
        _CONFIG['super_user_name'] = super_username
        super_password = os.environ.get(
            'CLOUDIGRADE_PASSWORD', utils.gen_password()
        )
        _CONFIG['super_user_password'] = super_password
        token = os.environ.get('CLOUDIGRADE_TOKEN', False)
        if not token and create_superuser:
            try:
                token = injector.make_super_user(
                    super_username, super_password)
            except RuntimeError as e:
                raise exceptions.MissingConfigurationError(
                    'Could not create a super user or token, error:\n'
                    f'{repr(e)}'
                )
        _CONFIG['superuser_token'] = token
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
