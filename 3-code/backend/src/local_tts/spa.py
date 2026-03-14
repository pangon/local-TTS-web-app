"""SPA-aware static file serving for FastAPI."""

from starlette.staticfiles import StaticFiles
from starlette.types import Receive, Scope, Send


class SPAStaticFiles(StaticFiles):
    """Static file handler that falls back to index.html for unknown paths.

    This enables client-side routing: any request that doesn't match a real
    static file (and isn't an API route) returns index.html so Vue Router
    can handle the path.
    """

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        try:
            await super().__call__(scope, receive, send)
        except Exception:
            # Path not found among static files — serve index.html for SPA routing
            scope["path"] = "/index.html"
            await super().__call__(scope, receive, send)
