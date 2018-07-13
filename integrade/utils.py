"""Utility functions."""
import secrets
import string
import uuid
from urllib.parse import urlunparse

import boto3


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


def get_primary_account_id():
    """Return the account ID for the primary AWS account."""
    return boto3.client('sts').get_caller_identity().get('Account')
