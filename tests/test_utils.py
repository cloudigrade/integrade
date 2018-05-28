"""Unit tests for :mod:`integrade.utils`."""
import string

from integrade.utils import base_url, gen_password, uuid4


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
