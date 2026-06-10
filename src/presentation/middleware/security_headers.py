from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):

    @staticmethod
    def _build_csp(path: str) -> str:
        if path.startswith("/api/docs") or path.startswith("/api/redoc") or path == "/openapi.json":
            return "; ".join(
                [
                    "default-src 'self'",
                    "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net",
                    "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net",
                    "img-src 'self' data: https://fastapi.tiangolo.com",
                    "font-src 'self' https://cdn.jsdelivr.net",
                    "connect-src 'self'",
                ]
            )
        return "default-src 'self'"

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        response = await call_next(request)
        response.headers.update(
            {
                "X-Content-Type-Options": "nosniff",
                "X-Frame-Options": "DENY",
                "X-XSS-Protection": "1; mode=block",
                "Referrer-Policy": "strict-origin-when-cross-origin",
                "Permissions-Policy": "geolocation=(), microphone=()",
                "Strict-Transport-Security": "max-age=63072000; includeSubDomains; preload",
                "Content-Security-Policy": self._build_csp(request.url.path),
            }
        )
        return response
