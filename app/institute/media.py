"""Private R2 reads, proxied through the portal after its Supabase RLS check."""

import logging
import re
from collections.abc import AsyncIterator
from typing import Literal
from uuid import UUID

import boto3
import httpx
from botocore.config import Config
from starlette.background import BackgroundTask
from starlette.responses import JSONResponse, Response, StreamingResponse

from app.institute.config import PortalSettings

MediaKind = Literal["audio", "notes"]


class R2RequestLogFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        # HTTPX's INFO request log otherwise exposes the server's signed R2 URL.
        return ".r2.cloudflarestorage.com" not in record.getMessage()


def object_key(lesson_id: UUID, kind: MediaKind) -> str:
    # UUID and a fixed kind prevent user-controlled storage paths.
    return f"lessons/{lesson_id}/{'audio' if kind == 'audio' else 'notes.pdf'}"


def r2_client(settings: PortalSettings):  # type: ignore[no-untyped-def]
    return boto3.client(
        "s3",
        endpoint_url=f"https://{settings.r2_account_id}.r2.cloudflarestorage.com",
        aws_access_key_id=settings.r2_access_key_id.get_secret_value(),
        aws_secret_access_key=settings.r2_secret_access_key.get_secret_value(),
        region_name="auto",
        config=Config(signature_version="s3v4", s3={"addressing_style": "path"}),
    )


class R2MediaProvider:
    def __init__(self, settings: PortalSettings) -> None:
        http_logger = logging.getLogger("httpx")
        if not any(isinstance(item, R2RequestLogFilter) for item in http_logger.filters):
            http_logger.addFilter(R2RequestLogFilter())
        self.settings = settings
        self.client = r2_client(settings) if settings.media_configured else None

    async def stream(self, lesson_id: UUID, kind: MediaKind, byte_range: str | None) -> Response:
        if not self.client:
            return JSONResponse({"message": "Media is not yet available."}, status_code=404)
        if byte_range and not re.fullmatch(r"bytes=(?:[0-9]+-[0-9]*|-[0-9]+)", byte_range):
            return Response(status_code=416)
        # This signed URL stays on the server. Browsers receive only the authorized bytes.
        url = self.client.generate_presigned_url(
            "get_object",
            Params={"Bucket": self.settings.r2_bucket, "Key": object_key(lesson_id, kind)},
            ExpiresIn=60,
        )
        client = httpx.AsyncClient(timeout=httpx.Timeout(30, connect=10), follow_redirects=False)
        try:
            upstream = await client.send(
                client.build_request(
                    "GET",
                    url,
                    headers={"Range": byte_range} if byte_range else {},
                ),
                stream=True,
            )
        except httpx.HTTPError:
            await client.aclose()
            return JSONResponse({"message": "Media temporarily unavailable."}, status_code=503)

        async def close() -> None:
            await upstream.aclose()
            await client.aclose()

        if upstream.status_code not in {200, 206}:
            status = upstream.status_code if upstream.status_code in {404, 416} else 503
            headers = {}
            if status == 416 and "content-range" in upstream.headers:
                headers["content-range"] = upstream.headers["content-range"]
            await close()
            return JSONResponse(
                {"message": "Media unavailable."}, status_code=status, headers=headers
            )
        media_type = upstream.headers.get("content-type", "").split(";")[0].lower()
        # Dashboard uploads assign the extensionless placeholder key a generic type.
        # Our packaged placeholder is WAV; real recordings must have an audio MIME type.
        if (
            kind == "audio"
            and self.settings.institute_media_placeholders
            and media_type == "application/octet-stream"
        ):
            media_type = "audio/wav"
        allowed = {"audio/mpeg", "audio/mp4", "audio/wav", "audio/x-wav", "audio/ogg"}
        if (kind == "notes" and media_type != "application/pdf") or (
            kind == "audio" and media_type not in allowed
        ):
            await close()
            return JSONResponse({"message": "Media unavailable."}, status_code=503)
        headers = {
            name: upstream.headers[name]
            for name in ("content-length", "content-range", "accept-ranges")
            if name in upstream.headers
        }
        headers["content-disposition"] = (
            'inline; filename="notes.pdf"' if kind == "notes" else "inline"
        )

        async def chunks() -> AsyncIterator[bytes]:
            try:
                async for chunk in upstream.aiter_raw():
                    yield chunk
            finally:
                await close()

        return StreamingResponse(
            chunks(),
            status_code=upstream.status_code,
            media_type=media_type,
            headers=headers,
            background=BackgroundTask(close),
        )
