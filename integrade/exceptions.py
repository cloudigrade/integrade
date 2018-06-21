"""Custom exceptions defined by Integrade."""


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
