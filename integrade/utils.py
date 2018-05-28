"""Utility functions."""
import secrets
import string
import uuid
from urllib.parse import urlunparse


def base_url(cfg):
    """Generate the base URL based on the configuration."""
    return urlunparse((cfg['scheme'], cfg['base_url'], '', '', '', ''))


def gen_password(length=20):
    """Generate a random password with letters, digits and punctuation."""
    return ''.join(
        secrets.choice(string.printable)
        for _ in range(length)
    )


def uuid4():
    """Provide unique string identifiers."""
    return str(uuid.uuid4())
