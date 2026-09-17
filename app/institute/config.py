import re
from functools import lru_cache
from urllib.parse import urlsplit

from cryptography.fernet import Fernet
from pydantic import SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class PortalSettings(BaseSettings):
    supabase_url: str = ""
    supabase_publishable_key: str = ""
    institute_cookie_key: str = ""
    institute_origin: str = "https://ruach.zionencounter.com"
    r2_account_id: str = ""
    r2_bucket: str = "ruach-institute-media"
    r2_access_key_id: SecretStr = SecretStr("")
    r2_secret_access_key: SecretStr = SecretStr("")
    institute_media_placeholders: bool = True

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @model_validator(mode="after")
    def validate_configuration(self) -> "PortalSettings":
        origin = urlsplit(self.institute_origin)
        local = origin.hostname in {"localhost", "127.0.0.1"}
        if (origin.scheme != "https" and not (local and origin.scheme == "http")) or (
            not origin.netloc or origin.path or origin.query or origin.fragment or origin.username
        ):
            raise ValueError("INSTITUTE_ORIGIN must be an HTTPS origin (HTTP only on localhost)")
        if self.supabase_url and urlsplit(self.supabase_url).scheme != "https":
            raise ValueError("SUPABASE_URL must use HTTPS")
        if self.institute_cookie_key:
            Fernet(self.institute_cookie_key.encode())
        if self.r2_account_id and not re.fullmatch(r"[a-f0-9]{32}", self.r2_account_id):
            raise ValueError("R2_ACCOUNT_ID must be the Cloudflare account ID")
        if not re.fullmatch(r"[a-z0-9][a-z0-9-]{1,61}[a-z0-9]", self.r2_bucket):
            raise ValueError("R2_BUCKET must be a valid bucket name")
        return self

    @property
    def media_configured(self) -> bool:
        return bool(
            self.r2_account_id
            and self.r2_access_key_id.get_secret_value()
            and self.r2_secret_access_key.get_secret_value()
        )

    @property
    def configured(self) -> bool:
        return bool(
            self.supabase_url and self.supabase_publishable_key and self.institute_cookie_key
        )

    @property
    def secure_cookies(self) -> bool:
        return self.institute_origin.startswith("https://")


@lru_cache
def get_portal_settings() -> PortalSettings:
    return PortalSettings()
