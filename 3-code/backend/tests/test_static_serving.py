"""Tests for static file serving and SPA fallback (TASK-static-file-serving).

Covers:
- FastAPI serves Vue production build files from STATIC_DIR
- Unknown paths fall back to index.html (SPA client-side routing)
- API routes are not affected by the static mount
- Static serving is skipped when STATIC_DIR does not exist
"""

import textwrap
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient


@pytest.fixture
def static_dir(tmp_path: Path) -> Path:
    """Create a minimal Vue-like production build directory."""
    dist = tmp_path / "dist"
    dist.mkdir()
    (dist / "index.html").write_text(
        "<!doctype html><html><body><div id='app'></div></body></html>"
    )
    assets = dist / "assets"
    assets.mkdir()
    (assets / "app.js").write_text("console.log('app');")
    (assets / "style.css").write_text("body { margin: 0; }")
    return dist


@pytest.fixture
def app_with_static(static_dir: Path, monkeypatch):
    """Create a FastAPI app with STATIC_DIR pointing to a temp dist directory."""
    import local_tts.config as config_mod

    monkeypatch.setattr(config_mod, "STATIC_DIR", static_dir)
    from local_tts.app import create_app

    return create_app()


@pytest.fixture
def app_without_static(tmp_path: Path, monkeypatch):
    """Create a FastAPI app where STATIC_DIR does not exist."""
    import local_tts.config as config_mod

    monkeypatch.setattr(config_mod, "STATIC_DIR", tmp_path / "nonexistent")
    from local_tts.app import create_app

    return create_app()


@pytest.fixture
async def client_with_static(app_with_static):
    transport = ASGITransport(app=app_with_static)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.fixture
async def client_without_static(app_without_static):
    transport = ASGITransport(app=app_without_static)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


class TestStaticFileServing:
    @pytest.mark.anyio
    async def test_serves_index_html_at_root(self, client_with_static):
        response = await client_with_static.get("/")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        assert "<div id='app'></div>" in response.text

    @pytest.mark.anyio
    async def test_serves_js_asset(self, client_with_static):
        response = await client_with_static.get("/assets/app.js")
        assert response.status_code == 200
        assert "console.log" in response.text

    @pytest.mark.anyio
    async def test_serves_css_asset(self, client_with_static):
        response = await client_with_static.get("/assets/style.css")
        assert response.status_code == 200
        assert "margin" in response.text


class TestSPAFallback:
    @pytest.mark.anyio
    async def test_unknown_path_returns_index_html(self, client_with_static):
        """Non-API, non-file paths should return index.html for Vue Router."""
        response = await client_with_static.get("/library")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        assert "<div id='app'></div>" in response.text

    @pytest.mark.anyio
    async def test_nested_unknown_path_returns_index_html(self, client_with_static):
        response = await client_with_static.get("/playback/some-id")
        assert response.status_code == 200
        assert "<div id='app'></div>" in response.text


class TestAPIRoutesUnaffected:
    @pytest.mark.anyio
    async def test_api_health_still_works(self, client_with_static):
        """API routes must not be intercepted by the static mount."""
        response = await client_with_static.get("/api/v1/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}


class TestStaticDirMissing:
    @pytest.mark.anyio
    async def test_api_works_without_static_dir(self, client_without_static):
        """When STATIC_DIR doesn't exist, API routes still function."""
        response = await client_without_static.get("/api/v1/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}

    @pytest.mark.anyio
    async def test_root_returns_404_without_static_dir(self, client_without_static):
        """When STATIC_DIR doesn't exist, root path returns 404 (no static mount)."""
        response = await client_without_static.get("/")
        assert response.status_code == 404
