"""Utility functions."""
import uuid
from urllib.parse import urlunparse


def uuid4():
    """Provide unique string identifiers."""
    return str(uuid.uuid4())


def base_url(cfg):
    """Generate the base URL based on the configuration."""
    return urlunparse((cfg['scheme'], cfg['base_url'], '', '', '', ''))
