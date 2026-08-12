"""
tests for tools/download_external_data.py

These tests exercise everything that *can* be tested without a real
network call: the SSL-specific error path prints actionable guidance
instead of a bare urllib error, the default is secure (no SSL context
override), and `--insecure` is a real, explicit opt-in rather than a
silent default.
"""

import ssl
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError, URLError

import pytest

import tools.download_external_data as mod


def test_default_run_does_not_weaken_ssl_verification():
    """No context override unless --insecure is explicitly given."""
    captured = []

    def fake_download(target, *, ssl_context):
        captured.append(ssl_context)
        raise SystemExit(0)

    with patch("sys.argv", ["download_external_data.py"]):
        with patch.object(mod, "_download", side_effect=fake_download):
            with pytest.raises(SystemExit):
                mod.main()

    assert captured == [None]


def test_insecure_flag_creates_an_unverified_context():
    captured = []

    def fake_download(target, *, ssl_context):
        captured.append(ssl_context)
        raise SystemExit(0)

    with patch("sys.argv", ["download_external_data.py", "--insecure"]):
        with patch.object(mod, "_download", side_effect=fake_download):
            with pytest.raises(SystemExit):
                mod.main()

    assert len(captured) == 1
    ctx = captured[0]
    assert isinstance(ctx, ssl.SSLContext)
    assert ctx.check_hostname is False
    assert ctx.verify_mode == ssl.CERT_NONE


def test_ssl_certificate_error_gets_actionable_guidance(capsys):
    """The exact error a user reported: a self-signed certificate in the
    chain, the signature of a TLS-intercepting network proxy."""
    cert_err = ssl.SSLCertVerificationError(
        "certificate verify failed: self-signed certificate in "
        "certificate chain (_ssl.c:1000)"
    )
    url_err = URLError(cert_err)

    with patch("sys.argv", ["download_external_data.py"]):
        with patch.object(mod, "_download", side_effect=url_err):
            with pytest.raises(SystemExit) as exc_info:
                mod.main()

    assert exc_info.value.code == 1
    captured = capsys.readouterr()
    # Both likely causes explained, not just the raw urllib error.
    assert "intercepts HTTPS traffic" in captured.err
    assert "Install Certificates.command" in captured.err
    assert "--insecure" in captured.err


def test_http_error_still_reports_the_status_code():
    http_err = HTTPError(mod.URL, 404, "Not Found", {}, None)

    with patch("sys.argv", ["download_external_data.py"]):
        with patch.object(mod, "_download", side_effect=http_err):
            with pytest.raises(SystemExit) as exc_info:
                mod.main()

    assert "404" in str(exc_info.value.code)


def test_non_ssl_url_error_falls_through_to_the_generic_message():
    """A URLError NOT caused by a certificate problem (e.g. DNS failure,
    connection refused) should not get the SSL-specific wall of text."""
    other_err = URLError("Name or service not known")

    with patch("sys.argv", ["download_external_data.py"]):
        with patch.object(mod, "_download", side_effect=other_err):
            with pytest.raises(SystemExit) as exc_info:
                mod.main()

    assert "intercepts HTTPS traffic" not in str(exc_info.value.code)
    assert "Name or service not known" in str(exc_info.value.code)


def test_download_target_is_under_repo_root(tmp_path):
    """Zip path must not depend on the process CWD."""
    captured = []

    def fake_download(target, *, ssl_context):
        captured.append(Path(target))
        raise SystemExit(0)

    with patch("sys.argv", ["download_external_data.py"]):
        with patch.object(mod, "_download", side_effect=fake_download):
            with pytest.raises(SystemExit):
                mod.main()

    assert len(captured) == 1
    assert captured[0].name == "cesdm_external_data.zip"
    assert captured[0].parent == mod._repo_root()
