"""Checks wrapper cannot mistake upstream fixture-only mode for compression."""
import importlib.util
from pathlib import Path
import pytest
path=Path(__file__).resolve().parents[1]/'scripts/test_upstream_token_optimizer.py'
spec=importlib.util.spec_from_file_location('test_external_upstream',path)
mod=importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

def test_measured_fixture_counts_and_failure():
    s=mod.summarize({'results':[{'category':'git','status':'pass','raw_tokens':100,'compressed_tokens':40},
                                 {'category':'git','status':'FAIL','raw_tokens':50,'compressed_tokens':50}]})
    assert (s['passed'],s['failed'],s['removed'])==(1,1,60)
def test_no_compressor_is_invalid():
    with pytest.raises(ValueError,match='compressor not active'):
        mod.summarize({'results':[{'category':'git','status':'no_compressor','raw_tokens':5,'compressed_tokens':5}]})
def test_empty_fixture_run_invalid():
    with pytest.raises(ValueError):mod.summarize({'results':[]})
def test_html_escapes_script_in_example():
    s=mod.summarize({'results':[{'category':'git','status':'pass','raw_tokens':15,'compressed_tokens':4}]})
    page=mod.html_report(s,[],{'name':'test','raw':'<script>alert(1)</script>','optimized':'safe','before':15,'after':4,'preserved_required':True})
    assert '<script>alert(1)</script>' not in page and '&lt;script&gt;' in page
