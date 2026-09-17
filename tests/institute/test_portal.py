import time
from typing import Any
from urllib.parse import parse_qs, urlsplit

import httpx
import pytest
from cryptography.fernet import Fernet
from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette.responses import Response

from app.institute.application import create_portal
from app.institute.auth import CookieSession
from app.institute.config import PortalSettings
from app.institute.supabase import SupabaseFailure, SupabaseGateway

COURSE = {
    "id": "10000000-0000-0000-0000-000000000001",
    "slug": "architecture-of-the-mind",
    "title": "Architecture of the Mind",
    "status": "active",
    "total_weeks": 5,
}
LESSON = {
    "id": "20000000-0000-0000-0000-000000000001",
    "week_number": 1,
    "title": "Mind Over Matter",
    "description": "PLACEHOLDER",
    "notes": "PLACEHOLDER",
    "reflection_questions": "PLACEHOLDER",
}


class FakeGateway:
    def __init__(self) -> None:
        self.student_status = "active"
        self.enrolled = True
        self.registered = True
        self.failed_user = False
        self.failed_verify = False
        self.failed_refresh = False
        self.failed_logout = False
        self.failed_network = False
        self.refreshed = False
        self.revoked = False
        self.verified = False
        self.sent_redirect = ""
        self.queries: list[tuple[str, dict[str, str]]] = []

    def session(self) -> dict[str, Any]:
        return {
            "access_token": "verified-access-token",
            "refresh_token": "private-refresh-token",
            "expires_in": 3600,
        }

    async def user(self, token: str) -> dict[str, str]:
        if self.failed_network:
            raise SupabaseFailure(503)
        if self.failed_user:
            raise SupabaseFailure(401)
        return {"id": "student-auth-uuid", "email_confirmed_at": "2026-01-01T00:00:00Z"}

    async def send_link(self, email: str, redirect: str) -> None:
        self.sent_redirect = redirect

    async def verify(self, token_hash: str) -> dict[str, Any]:
        if self.failed_verify:
            raise SupabaseFailure(403)
        self.verified = True
        return self.session()

    async def refresh(self, token: str) -> dict[str, Any]:
        if self.failed_refresh:
            raise SupabaseFailure(400)
        self.refreshed = True
        return self.session()

    async def logout(self, token: str) -> None:
        if self.failed_logout:
            raise SupabaseFailure(503)
        self.revoked = True

    async def rows(self, table: str, token: str, **query: str) -> list[dict[str, Any]]:
        self.queries.append((table, query))
        if table == "students":
            return (
                [{"id": "student-uuid", "student_id": "RI-001", "status": self.student_status}]
                if self.registered
                else []
            )
        if table == "courses":
            if "slug" in query:
                return [COURSE] if self.enrolled else []
            return [
                COURSE,
                {
                    "slug": "future-course",
                    "title": "Future Course",
                    "status": "coming_soon",
                    "total_weeks": 5,
                },
            ]
        if table == "enrollments":
            return [{"id": "enrollment-uuid"}] if self.enrolled else []
        if table == "lessons":
            return [LESSON] if "id" not in query or query["id"] == f"eq.{LESSON['id']}" else []
        raise AssertionError(table)


@pytest.fixture
def portal() -> tuple[TestClient, FakeGateway, PortalSettings]:
    settings = PortalSettings(
        supabase_url="https://example.supabase.co",
        supabase_publishable_key="sb_publishable_test",
        institute_cookie_key=Fernet.generate_key().decode(),
        institute_origin="https://testserver",
        _env_file=None,
    )
    application = create_portal(settings)
    gateway = FakeGateway()
    application.state.gateway = gateway
    host = FastAPI()
    host.mount("/institute", application)
    with TestClient(host, base_url="https://testserver", follow_redirects=False) as client:
        yield client, gateway, settings


def sign_in(client: TestClient, settings: PortalSettings, expired: bool = False) -> None:
    response = Response()
    cookies = CookieSession(settings)
    cookies.write(
        response,
        "access",
        {"token": "verified-access-token", "expires": time.time() + (-10 if expired else 3600)},
        2592000,
    )
    cookies.write(response, "refresh", {"token": "private-refresh-token"}, 2592000)
    for header in response.headers.getlist("set-cookie"):
        name, value = header.split(";", 1)[0].split("=", 1)
        client.cookies.set(name, value, domain="testserver.local", path="/institute")


@pytest.mark.parametrize("path", ["/portal", "/architecture-of-the-mind"])
def test_logged_out_cannot_access_content(portal, path):
    client, gateway, _ = portal
    response = client.get("/institute" + path)
    assert response.status_code == 303
    assert response.headers["location"] == "/institute?reason=session"
    assert "Mind Over Matter" not in response.text
    assert not gateway.queries


def test_login_and_headers(portal):
    client, _, _ = portal
    response = client.get("/institute/", follow_redirects=True)
    assert response.status_code == 200
    assert 'type="email"' in response.text and 'type="password"' not in response.text
    assert "no-store" in response.headers["cache-control"]
    assert "noindex" in response.headers["x-robots-tag"]
    assert "frame-ancestors 'none'" in response.headers["content-security-policy"]
    assert response.headers["referrer-policy"] == "same-origin"


def test_approved_student_dashboard_and_course(portal):
    client, gateway, settings = portal
    sign_in(client, settings)
    dashboard = client.get("/institute/portal")
    assert dashboard.status_code == 200
    assert dashboard.text.count('class="course-card ') == 2
    assert 'href="/institute/architecture-of-the-mind"' in dashboard.text
    assert 'href="/institute/future-course"' not in dashboard.text
    course = client.get("/institute/architecture-of-the-mind")
    assert course.status_code == 200
    assert "Mind Over Matter" in course.text
    assert course.text.count('class="week-section') == 5
    assert course.text.count("LOCKED") == 4
    assert (
        course.text.index('aria-label="NOTES"')
        < course.text.index('aria-label="Audio"')
        < course.text.index('aria-label="REFLECTION QUESTIONS"')
    )
    assert "private-refresh-token" not in course.text
    assert "verified-access-token" not in course.text
    assert all(q["status"] == "eq.published" for table, q in gateway.queries if table == "lessons")


@pytest.mark.parametrize("mode", ["unregistered", "inactive", "pending", "unenrolled"])
def test_authorization_denies_without_fetching_lessons(portal, mode):
    client, gateway, settings = portal
    sign_in(client, settings)
    if mode == "unregistered":
        gateway.registered = False
    elif mode == "unenrolled":
        gateway.enrolled = False
    else:
        gateway.student_status = mode
    response = client.get("/institute/architecture-of-the-mind")
    assert response.status_code == 403
    assert "Mind Over Matter" not in response.text
    assert not any(table == "lessons" for table, _ in gateway.queries)


def test_callback_and_logout(portal):
    client, gateway, _ = portal
    sent = client.post(
        "/institute/auth/login",
        data={"email": "student@example.com"},
        headers={"origin": "https://testserver"},
    )
    assert sent.status_code == 200 and "Check your inbox" in sent.text
    state = parse_qs(urlsplit(gateway.sent_redirect).query)["state"][0]
    response = client.get(
        "/institute/auth/callback", params={"state": state, "token_hash": "one-time-hash"}
    )
    assert response.status_code == 303 and response.headers["location"] == "/institute/portal"
    assert response.headers["referrer-policy"] == "no-referrer"
    assert gateway.verified
    cookies = response.headers.get_list("set-cookie")
    assert all(
        "HttpOnly" in cookie and "Secure" in cookie and "SameSite=lax" in cookie
        for cookie in cookies
    )
    assert all("private-refresh-token" not in cookie for cookie in cookies)
    assert client.get("/institute/portal").status_code == 200
    out = client.post("/institute/auth/logout", headers={"origin": "https://testserver"})
    assert out.status_code == 303 and gateway.revoked
    assert client.get("/institute/portal").status_code == 303


@pytest.mark.parametrize("mode", ["missing_state", "wrong_state", "expired_link"])
def test_invalid_link_fails_safely(portal, mode):
    client, gateway, _ = portal
    client.post(
        "/institute/auth/login",
        data={"email": "student@example.com"},
        headers={"origin": "https://testserver"},
    )
    state = parse_qs(urlsplit(gateway.sent_redirect).query)["state"][0]
    gateway.failed_verify = mode == "expired_link"
    if mode == "wrong_state":
        state = "attacker-state"
    if mode == "missing_state":
        state = ""
    response = client.get(
        "/institute/auth/callback", params={"state": state, "token_hash": "sensitive-token"}
    )
    assert response.headers["location"] == "/institute?reason=link"
    assert "sensitive-token" not in response.text
    assert not gateway.verified


def test_expired_access_refreshes_and_invalid_refresh_redirects(portal):
    client, gateway, settings = portal
    sign_in(client, settings, expired=True)
    response = client.get("/institute/portal")
    assert response.status_code == 200 and gateway.refreshed
    assert any("ruach-access" in c for c in response.headers.get_list("set-cookie"))
    sign_in(client, settings, expired=True)
    gateway.failed_refresh = True
    assert client.get("/institute/portal").status_code == 303


def test_forged_session_and_remote_invalid_user(portal):
    client, gateway, settings = portal
    client.cookies.set("__Secure-ruach-access", "forged")
    assert client.get("/institute/portal").status_code == 303
    client.cookies.clear()
    sign_in(client, settings)
    gateway.failed_user = True
    assert client.get("/institute/portal").status_code == 303
    assert not gateway.queries


def test_csrf_and_invalid_email(portal):
    client, gateway, _ = portal
    for action in ("login", "logout"):
        response = client.post(
            f"/institute/auth/{action}",
            data={"email": "student@example.com"},
            headers={"origin": "https://attacker.example"},
        )
        assert response.status_code == 403
    assert not gateway.sent_redirect and not gateway.revoked
    invalid = client.post(
        "/institute/auth/login",
        data={"email": "not-an-email"},
        headers={"origin": "https://testserver"},
    )
    assert invalid.status_code == 422 and 'aria-invalid="true"' in invalid.text


def test_network_and_logout_failure_do_not_claim_success(portal):
    client, gateway, settings = portal
    sign_in(client, settings)
    gateway.failed_network = True
    response = client.get("/institute/portal")
    assert response.status_code == 503 and "Temporarily unavailable" in response.text
    gateway.failed_network = False
    gateway.failed_logout = True
    response = client.post("/institute/auth/logout", headers={"origin": "https://testserver"})
    assert response.status_code == 503 and "Sign-out could not be completed" in response.text
    assert not gateway.revoked


def test_media_is_authorized_and_unavailable(portal):
    client, _, settings = portal
    path = f"/institute/media/{LESSON['id']}/audio"
    assert client.get(path).status_code == 303
    sign_in(client, settings)
    assert client.get(path).status_code == 404
    assert (
        client.get("/institute/media/20000000-0000-0000-0000-000000000002/audio").status_code == 404
    )


@pytest.mark.asyncio
async def test_supabase_http_contract(monkeypatch):
    settings = PortalSettings(
        supabase_url="https://example.supabase.co",
        supabase_publishable_key="public-key",
        _env_file=None,
    )
    captured = []

    def handler(request):
        captured.append(request)
        return httpx.Response(200, json=[])

    original = httpx.AsyncClient
    monkeypatch.setattr(
        httpx,
        "AsyncClient",
        lambda **kwargs: original(transport=httpx.MockTransport(handler), **kwargs),
    )
    gateway = SupabaseGateway(settings)
    await gateway.send_link(
        "student@example.com", "https://testserver/institute/auth/callback?state=test"
    )
    assert b'"create_user":false' in captured[0].content.replace(b" ", b"")
    await gateway.rows("students", "student-jwt", select="id")
    assert captured[1].headers["accept-profile"] == "institute"
    assert captured[1].headers["authorization"] == "Bearer student-jwt"
    assert captured[1].headers["apikey"] == "public-key"


def test_portal_fails_closed_without_configuration():
    app = FastAPI()
    app.mount("/institute", create_portal(PortalSettings(_env_file=None)))
    with TestClient(app, base_url="https://ruach.zionencounter.com") as client:
        assert client.get("/institute/").status_code == 200
        assert client.get("/institute/portal").status_code == 503


def test_invalid_identity_after_refresh_clears_new_session(portal):
    client, gateway, settings = portal
    sign_in(client, settings, expired=True)
    gateway.failed_user = True
    response = client.get("/institute/portal")
    assert response.status_code == 303 and gateway.refreshed
    assert all("Max-Age=0" in value for value in response.headers.get_list("set-cookie"))


def test_unexpected_errors_are_generic_and_never_cacheable(portal):
    client, gateway, _ = portal

    async def broken_request(*args, **kwargs):
        raise RuntimeError("Sensitive upstream detail must not be rendered")

    gateway.send_link = broken_request
    # The ASGI error middleware sends a safe response before re-raising for server logging.
    with TestClient(
        client.app, base_url="https://testserver", raise_server_exceptions=False
    ) as safe_client:
        response = safe_client.post(
            "/institute/auth/login",
            data={"email": "student@example.com"},
            headers={"origin": "https://testserver"},
        )
    assert response.status_code == 503
    assert "Sensitive upstream detail" not in response.text
    assert "no-store" in response.headers["cache-control"]
    assert "noindex" in response.headers["x-robots-tag"]


@pytest.fixture
def r2_portal(portal, monkeypatch):
    from app.institute.media import R2MediaProvider

    client, gateway, settings = portal
    settings.r2_account_id = "a" * 32
    from pydantic import SecretStr

    settings.r2_access_key_id = SecretStr("test-key")
    settings.r2_secret_access_key = SecretStr("test-secret")
    mounted = next(route.app for route in client.app.routes if route.path == "/institute")
    mounted.state.media = R2MediaProvider(settings)
    captured = []
    state = {"status": 206, "type": "audio/wav", "closed": False}

    class Bytes(httpx.AsyncByteStream):
        async def __aiter__(self):
            yield b"test"

        async def aclose(self):
            state["closed"] = True

    def handler(request):
        captured.append(request)
        return httpx.Response(
            state["status"],
            headers={
                "content-type": state["type"],
                "content-range": "bytes 0-3/10",
                "content-length": "4",
                "accept-ranges": "bytes",
            },
            stream=Bytes(),
        )

    original = httpx.AsyncClient
    monkeypatch.setattr(
        httpx, "AsyncClient", lambda **kw: original(transport=httpx.MockTransport(handler), **kw)
    )
    return client, gateway, settings, captured, state


def test_r2_range_stream_is_private_and_closes_upstream(r2_portal, caplog):
    caplog.set_level("INFO", logger="httpx")
    client, _, settings, captured, state = r2_portal
    sign_in(client, settings)
    response = client.get(f"/institute/media/{LESSON['id']}/audio", headers={"range": "bytes=0-3"})
    assert response.status_code == 206 and response.content == b"test"
    assert response.headers["content-range"] == "bytes 0-3/10"
    assert "no-store" in response.headers["cache-control"]
    assert captured[0].headers["range"] == "bytes=0-3"
    assert captured[0].url.host == "a" * 32 + ".r2.cloudflarestorage.com"
    assert captured[0].url.path.endswith(f"/lessons/{LESSON['id']}/audio")
    assert "X-Amz-Signature" not in str(response.headers)
    assert state["closed"]
    assert "X-Amz-Signature" not in caplog.text


def test_r2_pdf_and_placeholder_controls(r2_portal):
    client, _, settings, captured, state = r2_portal
    sign_in(client, settings)
    state.update(status=200, type="application/pdf")
    response = client.get(f"/institute/media/{LESSON['id']}/notes")
    assert response.status_code == 200
    assert response.headers["content-disposition"] == 'inline; filename="notes.pdf"'
    assert captured[0].url.path.endswith("/notes.pdf")
    page = client.get("/institute/architecture-of-the-mind").text
    assert "Open placeholder notes (PDF)" in page
    assert f'data-src="/institute/media/{LESSON["id"]}/audio"' in page
    assert "test-secret" not in page
    assert '<audio src=' not in page
    assert 'preload="metadata"' not in page


def test_r2_not_contacted_for_denied_or_invalid_requests(r2_portal):
    client, gateway, settings, captured, _ = r2_portal
    path = f"/institute/media/{LESSON['id']}/audio"
    assert client.get(path).status_code == 303
    sign_in(client, settings)
    gateway.student_status = "inactive"
    assert client.get(path).status_code == 403
    gateway.student_status = "active"
    assert (
        client.get("/institute/media/20000000-0000-0000-0000-000000000002/notes").status_code == 404
    )
    assert client.get(path, headers={"range": "bytes=0-2,5-7"}).status_code == 416
    assert client.get(path.replace("/audio", "/unknown")).status_code == 404
    assert not captured


@pytest.mark.parametrize(
    "status,content_type,expected",
    [
        (404, "text/xml", 404),
        (403, "text/xml", 503),
        (200, "text/html", 503),
        (416, "text/xml", 416),
    ],
)
def test_r2_upstream_errors_do_not_leak_details(r2_portal, status, content_type, expected):
    client, _, settings, _, state = r2_portal
    sign_in(client, settings)
    state.update(status=status, type=content_type)
    response = client.get(f"/institute/media/{LESSON['id']}/audio")
    assert response.status_code == expected
    assert "test-secret" not in response.text and "test-key" not in response.text
    assert state["closed"]


def test_dashboard_placeholder_audio_mime_is_scoped_to_placeholder_mode(r2_portal):
    client, _, settings, _, state = r2_portal
    sign_in(client, settings)
    state.update(status=200, type="application/octet-stream")
    path = f"/institute/media/{LESSON['id']}/audio"
    response = client.get(path)
    assert response.status_code == 200
    assert response.headers["content-type"] == "audio/wav"
    settings.institute_media_placeholders = False
    assert client.get(path).status_code == 503
    assert client.get(path.replace("/audio", "/notes")).status_code == 503
