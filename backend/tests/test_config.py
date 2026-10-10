import pytest

from app.config import Settings


def test_cors_origins_accept_exact_preview_and_local_origins(monkeypatch):
    monkeypatch.setenv(
        "CORS_ALLOWED_ORIGINS",
        "https://yuk-zavod-ai-preview.onrender.com, http://localhost:8080, http://127.0.0.1:8080",
    )

    settings = Settings.from_env()

    assert settings.cors_allowed_origins == (
        "https://yuk-zavod-ai-preview.onrender.com",
        "http://localhost:8080",
        "http://127.0.0.1:8080",
    )


@pytest.mark.parametrize(
    "value",
    [
        "*",
        "https://*.onrender.com",
        "https://preview.onrender.com/path",
        "https://user@preview.onrender.com",
        "ftp://preview.onrender.com",
        "https://preview.onrender.com,",
        "https://preview.onrender.com:bad",
    ],
)
def test_cors_origins_reject_non_origins_and_wildcards(monkeypatch, value):
    monkeypatch.setenv("CORS_ALLOWED_ORIGINS", value)

    with pytest.raises(ValueError, match="CORS_ALLOWED_ORIGINS"):
        Settings.from_env()


def test_empty_cors_origins_disable_cross_origin_requests(monkeypatch):
    monkeypatch.setenv("CORS_ALLOWED_ORIGINS", "")

    assert Settings.from_env().cors_allowed_origins == ()
