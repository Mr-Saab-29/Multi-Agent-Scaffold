import pytest


@pytest.fixture(autouse=True)
def force_fallback_llm(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "")
    monkeypatch.setenv("GEMINI_MODEL", "gemini-2.5-flash-lite")

    from app.core.config import get_settings
    from app.api.routes import runner

    get_settings.cache_clear()
    runner._settings = get_settings()
    yield
    get_settings.cache_clear()
