"""Unit tests for :mod:`integrade.utils`."""
import os
import string
from unittest.mock import patch

from integrade.utils import base_url, flaky, gen_password, uuid4


def test_gen_password():
    """Test gen_password generates password with printable string chars."""
    password = gen_password(30)
    assert len(password) == 30
    assert set(password).issubset(string.printable)


def test_uuid4():
    """Test we get a unique string each time we call uuid4()."""
    assert isinstance(uuid4(), str)
    assert uuid4() != uuid4()


def test_base_url():
    """Test base_url returns an URL with scheme and base_url."""
    cfg = {
        'scheme': 'https',
        'base_url': 'test.example.com',
    }
    assert base_url(cfg) == 'https://test.example.com'


def test_flaky():
    """Test that @flaky is only used on CI."""
    orig_ci = os.environ.get('CI')

    def my_function(): pass

    with patch('integrade.utils._flaky') as _flaky:
        os.environ['CI'] = ''
        flaky()(my_function)
        assert not _flaky.called

        os.environ['CI'] = 'yes'
        flaky()(my_function)
        assert _flaky.called

    os.environ['CI'] = orig_ci or ''
