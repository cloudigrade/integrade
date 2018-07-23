"""Utility functions."""
import os
import secrets
import string
import uuid
from urllib.parse import urlunparse

from flaky import flaky as _flaky


def base_url(cfg):
    """Generate the base URL based on the configuration."""
    return urlunparse((cfg['scheme'], cfg['base_url'], '', '', '', ''))


def gen_password(length=20):
    """Generate a random password with letters, digits and punctuation."""
    chars = string.ascii_letters + string.digits + string.punctuation
    return ''.join(
        secrets.choice(chars)
        for _ in range(length)
    )


def uuid4():
    """Provide unique string identifiers."""
    return str(uuid.uuid4())


def flaky(*args, **kwargs):
    """Wrap tests as flaky only on CI."""
    if os.environ.get('CI'):
        return _flaky(*args, **kwargs)
    else:
        return lambda f: f
