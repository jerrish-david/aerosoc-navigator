import logging
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from starlette.middleware.base import RequestResponseEndpoint
from starlette.responses import JSONResponse, RedirectResponse, Response
from starlette.staticfiles import StaticFiles
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.institute.auth import AccessFailure, CookieSession
from app.institute.config import PortalSettings, get_portal_settings
from app.institute.media import R2MediaProvider
from app.institute.routes import MESSAGES, render, router
from app.institute.supabase import SupabaseFailure, SupabaseGateway

logger = logging.getLogger("ruach.portal")


class PortalAccessLogFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        # Uvicorn otherwise includes the one-time token hash in its request-line log.
        return "/institute" not in record.getMessage()


class PortalHeaders:
    """Headers are scoped to the mounted portal, including error and static responses."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        async def secure_send(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))
                headers.extend(
                    [
                        (b"cache-control", b"private, no-store, max-age=0"),
                        (b"x-robots-tag", b"noindex, nofollow, noarchive"),
                        (b"x-content-type-options", b"nosniff"),
                        (
                            b"referrer-policy",
                            # Native form POSTs need their real Origin for CSRF checks.
                            # Callback URLs contain one-time tokens and must never be referred.
                            b"no-referrer"
                            if scope.get("path", "").endswith("/auth/callback")
                            else b"same-origin",
                        ),
                        (b"permissions-policy", b"camera=(), microphone=(), geolocation=()"),
                        (
                            b"content-security-policy",
                            (
                                b"default-src 'none'; script-src 'self'; "
                                b"style-src 'self'; img-src 'self'; font-src 'self'; connect-src 'self'; "
                                b"media-src 'self'; form-action 'self'; base-uri 'none'; frame-ancestors 'none'"
                            ),
                        ),
                    ]
                )
                message["headers"] = headers
            await send(message)

        await self.app(scope, receive, secure_send)


class PortalApplication(FastAPI):
    def build_middleware_stack(self) -> ASGIApp:
        # Wrap outside ServerErrorMiddleware so unexpected errors also remain private.
        return PortalHeaders(super().build_middleware_stack())


def create_portal(settings: PortalSettings | None = None) -> FastAPI:
    access_logger = logging.getLogger("uvicorn.access")
    if not any(isinstance(item, PortalAccessLogFilter) for item in access_logger.filters):
        access_logger.addFilter(PortalAccessLogFilter())
    app = PortalApplication(docs_url=None, redoc_url=None, openapi_url=None, debug=False)
    app.state.settings = settings or get_portal_settings()
    app.state.gateway = SupabaseGateway(app.state.settings)
    app.state.media = R2MediaProvider(app.state.settings)

    @app.middleware("http")
    async def persist_refreshed_session(
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        response = await call_next(request)
        session = getattr(request.state, "new_session", None)
        if session:
            CookieSession(app.state.settings).establish(response, session)
        return response

    @app.exception_handler(AccessFailure)
    async def access_error(request: Request, error: AccessFailure) -> Response:
        if error.status == 401:
            request.state.new_session = None
            response = RedirectResponse("/institute?reason=session", 303)
            CookieSession(app.state.settings).clear(response)
            return response
        title, detail = MESSAGES[error.reason]
        return render(
            request,
            "error.html",
            error.status,
            title=title,
            detail=detail,
            signed_in=bool(getattr(request.state, "auth_user_id", None)),
        )

    @app.exception_handler(SupabaseFailure)
    async def upstream_error(request: Request, error: SupabaseFailure) -> Response:
        logger.warning("portal_upstream_failure status=%s", error.status)
        title, detail = MESSAGES["unavailable"]
        return render(request, "error.html", 503, title=title, detail=detail)

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, error: RequestValidationError) -> Response:
        return JSONResponse({"message": "Resource unavailable."}, status_code=404)

    @app.exception_handler(Exception)
    async def unexpected_error(request: Request, error: Exception) -> Response:
        # Do not log request URLs, exception bodies, credentials, or student details.
        logger.error("portal_unexpected_failure")
        title, detail = MESSAGES["unavailable"]
        return render(request, "error.html", 503, title=title, detail=detail)

    app.mount("/static", StaticFiles(directory=Path(__file__).parent / "static"), name="static")
    app.include_router(router)
    return app
