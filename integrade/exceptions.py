"""Custom exceptions defined by Integrade."""


class AWSCredentialsNotFoundError(Exception):
    """Did not find authentication credentials in the environment.

    Specify different profiles' aws authentication credentials by setting
    AWS_ACCESS_KEY_ID_${PROFILE_NAME}, AWS_SECRET_ACCESS_KEY_${PROFILE_NAME},
    and CLOUDIGRADE_ROLE_${PROFILE_NAME} in your environment.
    """


class BaseUrlNotFound(Exception):
    """Was not able to build a base URL with the config information.

    Make sure the environment variable $CLOUDIGRADE_BASE_URL is set.
    Additionally specify http vs. https with $USE_HTTPS=<true/false> and
    $SSL_VERIFY=<true/false> in the case of https.
    """


class TokenNotFound(Exception):
    """Did not find an authentication token in the environment.

    Make sure the environment variable $CLOUDIGRADE_TOKEN is set.
    """


class ConfigFileNotFoundError(Exception):
    """Did not find the requested config file in the expected location.

    Customize this exception with more information about the expected locations
    for the config file.
    """


class MissingConfigurationError(Exception):
    """Some configuration necessary to run integrade is missing.

    Specify the missing configuration items in the exception message.
    """


class EventTimeoutError(Exception):
    """Integrade timed out while waiting for an event to occur.

    It takes time for events to get to cloudigrade, but we cannot wait forever.
    Raise this error if the timeout is exceeded while waiting for an event to
    occur.
    """
