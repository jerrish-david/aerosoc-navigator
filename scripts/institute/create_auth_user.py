"""Provision one approved passwordless Auth user. Does not email or enroll anyone."""

from getpass import getpass

import httpx
from email_validator import EmailNotValidError, validate_email

from app.institute.config import get_portal_settings


def main() -> None:
    settings = get_portal_settings()
    if not settings.supabase_url:
        raise SystemExit("Set SUPABASE_URL in the project .env first.")
    try:
        email = validate_email(
            input("Approved student's email: ").strip(), check_deliverability=False
        ).normalized
    except EmailNotValidError:
        raise SystemExit("Enter a valid approved email address.") from None
    # This credential is never stored, included in shell history, or used by the portal.
    admin_key = getpass("Supabase service-role key (hidden, not stored): ").strip()
    if not admin_key:
        raise SystemExit("An administrator credential is required.")
    try:
        response = httpx.post(
            settings.supabase_url.rstrip("/") + "/auth/v1/admin/users",
            headers={"apikey": admin_key, "Authorization": f"Bearer {admin_key}"},
            json={"email": email, "email_confirm": True},
            timeout=15,
        )
    except httpx.RequestError:
        raise SystemExit("Could not connect. Check the Auth users list before retrying.") from None
    if response.is_error:
        raise SystemExit(
            "User creation failed. Check the Auth users list and administrator access."
        )
    print("Auth user created. Run supabase/admin/enroll_student.sql to grant course access.")


if __name__ == "__main__":
    main()
