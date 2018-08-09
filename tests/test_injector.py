"""Test the injector utility used to run remote code."""
from unittest.mock import patch

import pytest

from integrade import injector


def test_data_injection():
    """The code gets data injected into it."""
    code = 'global result;result = x + 1'

    with patch('integrade.injector.subprocess.run') as run:
        run.return_value.returncode = 0
        run.return_value.stdout = b''
        injector.run_remote_python(code, x=41)

    args, kwargs = run.call_args
    code = kwargs['input'].decode('utf8')
    globals = {}
    exec(code, globals)
    assert globals['result'] == 42


def test_requires_oc():
    """The injector should make sure the OC client is installed."""
    with patch('integrade.injector.subprocess.run') as run:
        with patch('integrade.injector.which') as which:
            which.return_value = False
            with pytest.raises(EnvironmentError):
                injector.run_remote_python('code')
    assert not run.called
