import importlib.util
from pathlib import Path
import pytest

spec=importlib.util.spec_from_file_location('admin_harness',Path(__file__).resolve().parents[2]/'scripts/admin_browser_harness.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)

@pytest.mark.parametrize('url',[
    'postgresql+psycopg://user@localhost/fluentloop',
    'postgresql+psycopg://user@localhost/fluentloop_m08_local_7560346761',
    'postgresql+psycopg://user@external.example.com/fluentloop_browser_admin_test',
])
def test_historical_browser_harness_rejects_protected_or_external_targets(url):
    with pytest.raises(ValueError):module.disposable(url)

def test_historical_browser_harness_accepts_only_local_disposable_target():
    assert module.disposable('postgresql+psycopg://user@127.0.0.1/fluentloop_browser_admin_test').database=='fluentloop_browser_admin_test'
