import hashlib
import pytest
from vv_toolbox import source_identity as identity

BODY='<div class="tinymce-content"><h2>License</h2><div><a href="https://example.org/terms">Terms</a><p>Attribution required</p></div></div>'

def test_request_tokens_do_not_change_content():
    a='<meta name="csrf-token" content="a">'+BODY
    b='<meta name="csrf-token" content="b">'+BODY
    assert identity.license_content_sha256(a.encode())==identity.license_content_sha256(b.encode())

@pytest.mark.parametrize('modified',[BODY.replace('required','optional'),BODY.replace('/terms','/different'),BODY.replace('</p>',' Extra restriction</p>')])
def test_content_change_rejected(monkeypatch,modified):
    monkeypatch.setattr(identity,'LICENSE_CONTENT_SHA256',identity.license_content_sha256(BODY.encode()))
    with pytest.raises(ValueError): identity.validate_source_identity('LICENSE.html',modified.encode(),'old')

def test_reviewed_content_records_both_identities(monkeypatch):
    monkeypatch.setattr(identity,'LICENSE_CONTENT_SHA256',identity.license_content_sha256(BODY.encode()))
    result=identity.validate_source_identity('LICENSE.html',BODY.encode(),'old')
    assert result['method']=='reviewed-license-content-v1'
    assert result['sha256']==hashlib.sha256(BODY.encode()).hexdigest()
    assert result['legacy_raw_sha256']=='old'

@pytest.mark.parametrize('body',['<p>missing</p>',BODY+BODY,BODY[:-6]])
def test_ambiguous_or_incomplete_section_rejected(body):
    with pytest.raises(ValueError): identity.license_content_sha256(body.encode())

def test_geometry_never_uses_license_exception(monkeypatch):
    monkeypatch.setattr(identity,'LICENSE_CONTENT_SHA256',identity.license_content_sha256(BODY.encode()))
    with pytest.raises(ValueError): identity.validate_source_identity('mesh.zip',BODY.encode(),'old')

def test_legacy_exact_bytes_still_accepted():
    raw=b'legacy archived document'
    assert identity.validate_source_identity('LICENSE.html',raw,hashlib.sha256(raw).hexdigest())['method']=='raw-sha256'
