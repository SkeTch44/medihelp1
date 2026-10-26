from app.prescription_service import ALLOWED_MIME

def test_only_expected_upload_mime_types_are_allowed():
    assert "image/jpeg" in ALLOWED_MIME
    assert "image/png" in ALLOWED_MIME
    assert "application/pdf" in ALLOWED_MIME
    assert "text/html" not in ALLOWED_MIME
