"""Unit tests for :mod:`integrade.utils`."""
from integrade.utils import uuid4


def test_uuid4():
    """Test we get a unique string each time we call uuid4()."""
    assert isinstance(uuid4(), str)
    assert uuid4() != uuid4()
