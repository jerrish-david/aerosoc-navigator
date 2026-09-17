import json
import secrets
import time
from dataclasses import dataclass
from typing import Any

from cryptography.fernet import Fernet, InvalidToken
from fastapi import Request
from starlette.responses import Response

from app.institute.config import PortalSettings
from app.institute.supabase import SupabaseFailure, SupabaseGateway


class AccessFailure(Exception):
    def __init__(self, reason: str, status: int = 403) -> None:
        self.reason = reason
        self.status = status


@dataclass
class StudentSession:
    token: str
    student: dict[str, Any]


class CookieSession:
    def __init__(self, settings: PortalSettings) -> None:
        self.settings = settings
        self.cipher = Fernet(settings.institute_cookie_key.encode())

    def name(self, key: str) -> str:
        prefix = "__Secure-" if self.settings.secure_cookies else ""
        return f"{prefix}ruach-{key}"

    def read(self, request: Request, key: str, ttl: int = 2592000) -> dict[str, Any] | None:
        value = request.cookies.get(self.name(key), "")
        try:
            payload = self.cipher.decrypt(value.encode(), ttl=ttl)
            result: dict[str, Any] = json.loads(payload)
            return result
        except (InvalidToken, ValueError, TypeError):
            return None

    def write(self, response: Response, key: str, value: dict[str, Any], age: int) -> None:
        encrypted = self.cipher.encrypt(json.dumps(value).encode()).decode()
        # Fail closed rather than silently losing an oversized session cookie.
        if len(encrypted) > 3800:
            raise AccessFailure("unavailable", 503)
        response.set_cookie(
            self.name(key),
            encrypted,
            max_age=age,
            httponly=True,
            secure=self.settings.secure_cookies,
            samesite="lax",
            path="/institute",
        )

    def establish(self, response: Response, session: dict[str, Any]) -> None:
        self.write(
            response,
            "access",
            {
                "token": session["access_token"],
                "expires": time.time() + int(session["expires_in"]),
            },
            2592000,
        )
        self.write(response, "refresh", {"token": session["refresh_token"]}, 2592000)

    def clear(self, response: Response, *keys: str) -> None:
        for key in keys or ("access", "refresh", "login"):
            response.delete_cookie(
                self.name(key),
                path="/institute",
                secure=self.settings.secure_cookies,
                httponly=True,
                samesite="lax",
            )


def enforce_origin(request: Request, settings: PortalSettings) -> None:
    if request.headers.get("origin") != settings.institute_origin:
        raise AccessFailure("request", 403)


async def authenticate(
    request: Request,
    gateway: SupabaseGateway,
    settings: PortalSettings,
) -> str:
    if not settings.configured:
        raise AccessFailure("unavailable", 503)
    cookies = CookieSession(settings)
    access = cookies.read(request, "access")
    refresh = cookies.read(request, "refresh")
    if not access or not refresh:
        raise AccessFailure("session", 401)
    try:
        if access["expires"] <= time.time() + 30:
            session = await gateway.refresh(refresh["token"])
            request.state.new_session = session
            token = str(session["access_token"])
        else:
            token = str(access["token"])
        # Never authorize using unverified cookie claims or a decoded JWT alone.
        user = await gateway.user(token)
    except SupabaseFailure as error:
        if error.status in {400, 401, 403}:
            raise AccessFailure("session", 401) from None
        raise
    if not user.get("id") or not user.get("email_confirmed_at"):
        raise AccessFailure("session", 401)
    request.state.auth_user_id = user["id"]
    return token


async def authorize_student(
    request: Request,
    gateway: SupabaseGateway,
    settings: PortalSettings,
) -> StudentSession:
    token = await authenticate(request, gateway, settings)
    students = await gateway.rows(
        "students",
        token,
        select="id,student_id,status",
        auth_user_id=f"eq.{request.state.auth_user_id}",
        limit="1",
    )
    if not students:
        raise AccessFailure("unregistered")
    student = students[0]
    if student["status"] != "active":
        raise AccessFailure("inactive")
    return StudentSession(token, student)


async def authorize_course(
    gateway: SupabaseGateway,
    session: StudentSession,
    slug: str,
) -> dict[str, Any]:
    courses = await gateway.rows(
        "courses",
        session.token,
        select="id,slug,title,status,total_weeks",
        slug=f"eq.{slug}",
        status="eq.active",
        limit="1",
    )
    if not courses:
        raise AccessFailure("enrollment")
    course = courses[0]
    enrollments = await gateway.rows(
        "enrollments",
        session.token,
        select="id",
        student_id=f"eq.{session.student['id']}",
        course_id=f"eq.{course['id']}",
        status="eq.active",
        limit="1",
    )
    if not enrollments:
        raise AccessFailure("enrollment")
    return course


def new_login_state() -> str:
    return secrets.token_urlsafe(32)
