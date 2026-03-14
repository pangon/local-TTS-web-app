"""Shared test configuration and fixtures."""

import pytest


@pytest.fixture(params=["asyncio"])
def anyio_backend(request):
    """Restrict anyio tests to asyncio backend.

    The application uses asyncio (FastAPI/Uvicorn), so trio is not applicable.
    """
    return request.param
