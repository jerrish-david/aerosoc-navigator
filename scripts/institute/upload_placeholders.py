"""Upload placeholder assets to an existing PRIVATE R2 bucket; never overwrite files.

Run from the repository root with: .venv/bin/python -m scripts.institute.upload_placeholders
Use a temporary, bucket-scoped Object Read & Write credential, not the portal read key.
"""

import argparse
from getpass import getpass
from pathlib import Path
from uuid import UUID

from botocore.exceptions import ClientError
from pydantic import SecretStr

from app.institute.config import PortalSettings
from app.institute.media import object_key, r2_client


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--account-id", required=True)
    parser.add_argument(
        "--lesson-id",
        required=True,
        type=UUID,
        help="The actual Week 1 institute.lessons UUID from Supabase",
    )
    parser.add_argument("--bucket", default="ruach-institute-media")
    args = parser.parse_args()
    settings = PortalSettings(
        _env_file=None,
        r2_account_id=args.account_id,
        r2_bucket=args.bucket,
        r2_access_key_id=SecretStr(getpass("R2 upload Access Key ID: ")),
        r2_secret_access_key=SecretStr(getpass("R2 upload Secret Access Key: ")),
    )
    if not settings.media_configured:
        raise SystemExit("Both upload credentials are required.")
    client = r2_client(settings)
    root = Path(__file__).resolve().parents[2]
    assets = [
        ("audio", root / "cloudflare/placeholders/placeholder-audio.wav", "audio/wav"),
        ("notes", root / "output/pdf/ruach-week-01-placeholder-notes.pdf", "application/pdf"),
    ]
    for kind, path, content_type in assets:
        key = object_key(args.lesson_id, kind)  # type: ignore[arg-type]
        try:
            client.put_object(
                Bucket=args.bucket,
                Key=key,
                Body=path.read_bytes(),
                ContentType=content_type,
                CacheControl="private, no-store",
                Metadata={"placeholder": "true"},
                IfNoneMatch="*",
            )
            result = client.head_object(Bucket=args.bucket, Key=key)
            if result["ContentLength"] != path.stat().st_size:
                raise SystemExit(f"Upload verification failed: {key}")
            print(f"Uploaded and verified: {key}")
        except ClientError as error:
            if error.response["ResponseMetadata"]["HTTPStatusCode"] == 412:
                print(f"Skipped existing object: {key}")
            else:
                raise SystemExit(
                    "R2 upload failed; check the bucket and credential scope."
                ) from None


if __name__ == "__main__":
    main()
