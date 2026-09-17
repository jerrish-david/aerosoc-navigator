import secrets
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlencode
from uuid import UUID

from fastapi import APIRouter, Request
from pydantic import BaseModel, EmailStr, ValidationError
from starlette.responses import HTMLResponse, JSONResponse, RedirectResponse, Response
from starlette.templating import Jinja2Templates

from app.institute.auth import (
    AccessFailure,
    CookieSession,
    authenticate,
    authorize_course,
    authorize_student,
    enforce_origin,
    new_login_state,
)
from app.institute.media import MediaKind, R2MediaProvider
from app.institute.supabase import SupabaseFailure

router = APIRouter()
templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))

MESSAGES = {
    "session": ("Your session has ended", "Please sign in again to continue."),
    "link": (
        "This link is no longer available",
        "Request a new link and open it in the browser you used to sign in.",
    ),
    "unregistered": (
        "Access not yet available",
        "Your account is not registered with Ruach Institute. Please contact the institute.",
    ),
    "inactive": (
        "Your access is paused",
        "Your student account is not active. Please contact the institute.",
    ),
    "enrollment": (
        "Course access unavailable",
        "You are not enrolled in this course, or the course is not currently available.",
    ),
    "unavailable": (
        "Temporarily unavailable",
        "We couldn’t connect to the student portal. Please try again shortly.",
    ),
    "request": ("Please try again", "Return to the sign-in page and try again."),
    "rate": (
        "Please wait a moment",
        "Too many sign-in attempts. Please wait a minute before trying again.",
    ),
    "email": ("Check your email address", "Enter a valid email address."),
    "logout": (
        "Sign-out could not be completed",
        "Please try signing out again. Your session is still active.",
    ),
}


def render(request: Request, template: str, status: int = 200, **context: Any) -> Response:
    return templates.TemplateResponse(
        request=request,
        name=template,
        context=context,
        status_code=status,
    )


async def form_values(request: Request) -> dict[str, str]:
    if request.headers.get("content-type", "").split(";")[0] != "application/x-www-form-urlencoded":
        raise AccessFailure("request", 415)
    chunks = bytearray()
    async for chunk in request.stream():
        chunks.extend(chunk)
        if len(chunks) > 4096:
            raise AccessFailure("request", 413)
    try:
        return {key: value[-1] for key, value in parse_qs(chunks.decode()).items()}
    except UnicodeDecodeError:
        raise AccessFailure("request", 400) from None


class SignInForm(BaseModel):
    email: EmailStr


@router.get("/", response_class=HTMLResponse, include_in_schema=False)
async def login(request: Request) -> Response:
    settings = request.app.state.settings
    reason = request.query_params.get("reason", "")
    if settings.configured and not reason:
        try:
            await authenticate(request, request.app.state.gateway, settings)
            return RedirectResponse("/institute/portal", 303)
        except AccessFailure:
            pass
    message = MESSAGES.get(reason)
    return render(request, "login.html", message=message, sent=False, email="")


@router.post("/auth/login")
async def send_link(request: Request) -> Response:
    settings = request.app.state.settings
    enforce_origin(request, settings)
    values = await form_values(request)
    try:
        form = SignInForm.model_validate(values)
    except ValidationError:
        return render(
            request,
            "login.html",
            422,
            message=MESSAGES["email"],
            sent=False,
            email=values.get("email", "")[:254],
            invalid=True,
        )
    if not settings.configured:
        raise AccessFailure("unavailable", 503)
    state = new_login_state()
    callback = settings.institute_origin + "/institute/auth/callback?" + urlencode({"state": state})
    try:
        await request.app.state.gateway.send_link(str(form.email), callback)
    except SupabaseFailure as error:
        if error.status == 429:
            raise AccessFailure("rate", 429) from None
        # Existing and nonexistent accounts receive the same message to avoid enumeration.
        if error.status not in {400, 422}:
            raise
    response = render(request, "login.html", sent=True, message=None, email="")
    CookieSession(settings).write(response, "login", {"state": state}, 3600)
    return response


@router.get("/auth/callback")
async def callback(request: Request) -> Response:
    settings = request.app.state.settings
    if not settings.configured:
        raise AccessFailure("unavailable", 503)
    cookies = CookieSession(settings)
    pending = cookies.read(request, "login", ttl=3600)
    state = request.query_params.get("state", "")
    token_hash = request.query_params.get("token_hash", "")
    if (
        not pending
        or not secrets.compare_digest(pending.get("state", ""), state)
        or not token_hash
        or len(token_hash) > 512
        or request.query_params.get("error")
    ):
        response = RedirectResponse("/institute?reason=link", 303)
        return response
    try:
        session = await request.app.state.gateway.verify(token_hash)
    except SupabaseFailure as error:
        if error.status in {400, 401, 403, 422}:
            response = RedirectResponse("/institute?reason=link", 303)
            cookies.clear(response, "login")
            return response
        raise
    response = RedirectResponse("/institute/portal", 303)
    cookies.establish(response, session)
    cookies.clear(response, "login")
    return response


@router.post("/auth/logout")
async def logout(request: Request) -> Response:
    settings = request.app.state.settings
    enforce_origin(request, settings)
    token = await authenticate(request, request.app.state.gateway, settings)
    try:
        await request.app.state.gateway.logout(token)
    except SupabaseFailure as error:
        if error.status not in {401, 403, 404}:
            raise AccessFailure("logout", 503) from None
    response = RedirectResponse("/institute", 303)
    request.state.new_session = None
    CookieSession(settings).clear(response)
    return response


@router.get("/portal", response_class=HTMLResponse)
async def dashboard(request: Request) -> Response:
    gateway = request.app.state.gateway
    session = await authorize_student(request, gateway, request.app.state.settings)
    courses = await gateway.rows(
        "courses",
        session.token,
        select="slug,title,status,total_weeks",
        order="created_at.asc",
    )
    return render(request, "portal.html", student=session.student, courses=courses)


@router.get("/media/{lesson_id}/{kind}")
async def media_source(request: Request, lesson_id: UUID, kind: MediaKind) -> Response:
    gateway = request.app.state.gateway
    session = await authorize_student(request, gateway, request.app.state.settings)
    # RLS checks publication, student status, enrollment, and the live auth session.
    lessons = await gateway.rows(
        "lessons",
        session.token,
        select="id",
        id=f"eq.{lesson_id}",
        status="eq.published",
        limit="1",
    )
    if not lessons:
        return JSONResponse({"message": "Audio unavailable."}, status_code=404)
    provider: R2MediaProvider = request.app.state.media
    return await provider.stream(lesson_id, kind, request.headers.get("range"))


@router.get("/{slug}", response_class=HTMLResponse)
async def course_page(request: Request, slug: str) -> Response:
    gateway = request.app.state.gateway
    session = await authorize_student(request, gateway, request.app.state.settings)
    course = await authorize_course(gateway, session, slug)
    lessons = await gateway.rows(
        "lessons",
        session.token,
        select="id,week_number,title,description,notes,reflection_questions",
        course_id=f"eq.{course['id']}",
        status="eq.published",
        order="display_order.asc",
    )
    published = {lesson["week_number"]: lesson for lesson in lessons}
    weeks = [
        {"number": number, "lesson": published.get(number)}
        for number in range(1, course["total_weeks"] + 1)
    ]
    return render(
        request,
        "course.html",
        student=session.student,
        course=course,
        weeks=weeks,
        media_enabled=request.app.state.settings.media_configured,
        media_placeholders=request.app.state.settings.institute_media_placeholders,
    )
