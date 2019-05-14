"""Tools to manage global configuration of integrade."""

import os
from copy import deepcopy

import urllib3

import yaml

from integrade import exceptions


# Suppress HTTPS warnings against our test server without a cert
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


# `get_config` uses this as a cache. It is intentionally a global. This design
# lets us do interesting things like flush the cache at run time or completely
# avoid a config file by fetching values from the UI.
_CONFIG = None
_AWS_CONFIG = None


def get_config(need_base_url=True):
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

        ref_slug = os.environ.get('CI_COMMIT_REF_SLUG', '')
        cloudtrail_prefix = os.getenv('CLOUDTRAIL_PREFIX',
                                      f'review-{ref_slug}')

        # The location of the API endpoints and UI may be configured directly
        # with `CLOUDIGRADE_BASE_URL` -OR- we can determine a location based
        # on `CI_COMMIT_REF_SLUG` which comes from Gitlab CI and is our
        # current branch name.

        _CONFIG['base_url'] = os.getenv(
            'CLOUDIGRADE_BASE_URL',
            f'review-{ref_slug}.5a9f.insights-dev.openshiftapps.com',
        )

        _CONFIG['openshift_prefix'] = os.getenv(
            'OPENSHIFT_PREFIX',
            f'c-review-{ref_slug[:29]}-',
        )

        credentials = os.getenv(
            'CLOUDIGRADE_CREDENTIALS', 'mpierce@redhat.com:redhat'
        )
        _CONFIG['credentials'] = tuple(credentials.split(':'))

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
            profile['cloudtrail_name'] = f'{cloudtrail_prefix[:-1]}{acct_num}'
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
        path = os.path.join(os.path.dirname(__file__),
                            'aws_image_config.yaml')
        with open(path) as f:
            _AWS_CONFIG = yaml.load(f)
    return deepcopy(_AWS_CONFIG)
