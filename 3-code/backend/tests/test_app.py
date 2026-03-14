"""Tests for the FastAPI application skeleton (TASK-fastapi-app-skeleton).

Covers:
- REQ-SEC-localhost-binding: default 127.0.0.1, configurable override
- Startup URL display
- Health check endpoint
- API v1 prefix routing
"""

import os
from unittest.mock import patch

import pytest
from httpx import ASGITransport, AsyncClient

from local_tts.app import create_app


@pytest.fixture
def app():
    return create_app()


@pytest.fixture
async def client(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


class TestHealthEndpoint:
    @pytest.mark.anyio
    async def test_health_returns_ok(self, client):
        response = await client.get("/api/v1/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}

    @pytest.mark.anyio
    async def test_api_v1_prefix(self, client):
        """Health endpoint is only available under /api/v1/."""
        response = await client.get("/health")
        assert response.status_code == 404


class TestLocalhostBinding:
    """REQ-SEC-localhost-binding acceptance criteria."""

    def test_default_host_is_localhost(self):
        """Given default configuration, the host is 127.0.0.1."""
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("LOCAL_TTS_HOST", None)
            # Re-import to pick up default
            import importlib
            import local_tts.config as config_mod
            importlib.reload(config_mod)
            assert config_mod.HOST == "127.0.0.1"

    def test_default_port_is_8000(self):
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("LOCAL_TTS_PORT", None)
            import importlib
            import local_tts.config as config_mod
            importlib.reload(config_mod)
            assert config_mod.PORT == 8000

    def test_host_override_via_env(self):
        """Given the user explicitly sets a different bind address, it is respected."""
        with patch.dict(os.environ, {"LOCAL_TTS_HOST": "0.0.0.0"}):
            import importlib
            import local_tts.config as config_mod
            importlib.reload(config_mod)
            assert config_mod.HOST == "0.0.0.0"

    def test_port_override_via_env(self):
        with patch.dict(os.environ, {"LOCAL_TTS_PORT": "9000"}):
            import importlib
            import local_tts.config as config_mod
            importlib.reload(config_mod)
            assert config_mod.PORT == 9000


class TestStartupUrlDisplay:
    def test_main_prints_url(self, capsys):
        """On startup, the UI URL is displayed to the user."""
        with patch("uvicorn.run"):
            import importlib
            import local_tts.config as config_mod
            with patch.dict(os.environ, {}, clear=False):
                os.environ.pop("LOCAL_TTS_HOST", None)
                os.environ.pop("LOCAL_TTS_PORT", None)
                importlib.reload(config_mod)

            from local_tts.__main__ import main
            main()

        captured = capsys.readouterr()
        assert "http://127.0.0.1:8000" in captured.out

    def test_main_passes_host_and_port_to_uvicorn(self):
        """Uvicorn is started with the configured host and port."""
        with patch.dict(os.environ, {"LOCAL_TTS_HOST": "0.0.0.0", "LOCAL_TTS_PORT": "9999"}):
            import importlib
            import local_tts.config as config_mod
            importlib.reload(config_mod)

            with patch("uvicorn.run") as mock_run:
                from local_tts.__main__ import main
                main()

            mock_run.assert_called_once_with(
                "local_tts.app:app",
                host="0.0.0.0",
                port=9999,
                log_level="info",
            )


class TestAppFactory:
    def test_create_app_returns_fastapi_instance(self):
        app = create_app()
        from fastapi import FastAPI
        assert isinstance(app, FastAPI)

    def test_create_app_has_api_routes(self):
        app = create_app()
        paths = [route.path for route in app.routes]
        assert "/api/v1/health" in paths
