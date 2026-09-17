# Ruach Institute private R2 storage

Status: R2 is active. The private `ruach-institute-media` bucket was created in Eastern North America with Standard storage and public access disabled. The Week 1 placeholder audio (96,044 bytes) and notes PDF (2,032 bytes) were uploaded. A bucket-only Object Read credential named `ruach-portal-read-only` was created with user approval; its S3 credentials are saved in the ignored, mode-600 local `.env`. The local portal was restarted with R2 enabled.

Live Week 1 lesson UUID: `d9515a54-a2c6-4753-aad0-529ae9341033`. Both objects use the `lessons/<lesson-uuid>/` prefix. Dashboard uploads give the extensionless audio object `application/octet-stream`; the server labels it `audio/wav` only while placeholder mode is enabled. Real recordings must be uploaded with an audio MIME type.

## Bucket

Create `ruach-institute-media` using Standard storage. Keep both the public development
URL (`r2.dev`) and custom domains disabled. No CORS is needed: the FastAPI portal streams
R2 objects through same-origin routes after verifying the session and Supabase RLS.
Supabase remains the database for students, enrollments and lesson publication.

Object layout (the UUID comes from the real Supabase lesson, not a sample UUID):

```
lessons/<lesson-uuid>/audio       Content-Type: audio/wav (placeholder), audio/mpeg (real MP3)
lessons/<lesson-uuid>/notes.pdf   Content-Type: application/pdf
```

Use this read-only query in Supabase SQL Editor to find the Week 1 UUID:

```sql
select l.id, l.week_number, l.title
from institute.lessons l
join institute.courses c on c.id = l.course_id
where c.slug = 'architecture-of-the-mind' and l.week_number = 1;
```

## Credentials and upload

Create a bucket-scoped **Object Read only** R2 credential for the portal. Put its account
ID, Access Key ID and Secret Access Key in the root ignored `.env` using the variable
names in `app/institute/.env.example`. Never put secrets in HTML, JavaScript, Git, or docs.
The S3 credential is separate from a Cloudflare management API token.

Upload the two placeholders from the dashboard, or create a separate temporary
bucket-scoped **Object Read & Write** credential and run:

```sh
.venv/bin/python -m scripts.institute.upload_placeholders --account-id ACCOUNT_ID --lesson-id LESSON_UUID
```

The script prompts privately for upload credentials, refuses to overwrite existing
objects, and checks their sizes after uploading. Revoke the temporary upload credential
when finished. The local assets are a three-second quiet test tone and a one-page PDF
explicitly labeled PLACEHOLDER. The portal labels media as placeholders by default.

The local portal is running with R2 configured. With a properly enrolled test student, verify
playback and seeking, opening the PDF, denial for a locked lesson, and denial after
sign-out or deactivation. Gmail SMTP and the Magic Link template are now configured; an approved test student is enrolled and the latest Magic Link request succeeded with HTTP 200. Inbox receipt and authenticated access remain to be verified.

## Replacing placeholders

Upload actual recordings and notes at the same object keys with correct Content-Type.
After every visible resource is real, set `INSTITUTE_MEDIA_PLACEHOLDERS=false` and restart.
Publishing a lesson remains a separate Supabase status change. Uploading files never
unlocks lessons. To add future lessons, use their own UUID prefixes.

Each request, including audio byte-range requests, checks authorization before touching
R2. Upstream presigned URLs stay server-side. Responses are private/no-store; files are
streamed instead of buffered. This consumes portal-host bandwidth. Inline PDF viewing
is browser-native; it does not prevent an authorized student saving received content.

Reference: https://developers.cloudflare.com/r2/examples/aws/boto3/

## Local validation

29 portal tests pass, including private range streaming, PDF headers, denied requests,
upstream failures, and signed-URL log suppression. Ruff, mypy, Bandit and JavaScript
syntax checks pass. The PDF was rendered and visually checked. Live read-only retrieval matched both originals byte-for-byte, and a 44-byte audio range returned HTTP 206.

Live provider streaming returned audio/wav and application/pdf successfully. Unsigned R2 access was denied (HTTP 400), and logged-out portal requests for both files redirected to sign-in. Supabase Gmail SMTP and the Magic Link template are now configured; the approved test student is enrolled; the SMTP credential issue is resolved and the latest Magic Link request succeeded with HTTP 200; full sign-in awaits opening the email link in the same browser.
