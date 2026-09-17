# Ruach Institute portal — implementation and setup

The V1 is implemented in this repository and is **not deployed**. On September 16, the local environment was configured for the `ruach-auth` Supabase project and public sign-up was disabled. The four tables, RLS policies, seeded courses/lessons, Data API schema exposure, and production/local callback URLs have now been applied to that project. Anonymous live API reads were denied for all four tables, and seven database seed/privilege checks passed. One approved passwordless test student and active Architecture of the Mind enrollment have now been created (student ID `RI-TEST-001`). Temporary Gmail SMTP is saved and enabled, and the custom Magic Link subject/body have been saved and independently verified. After correcting SMTP credentials, the real Magic Link request succeeded with HTTP 200 on September 16 at 23:44:56 UTC. Inbox receipt and following the link in the same browser remain to be verified. The current workspace is AeroSOC Navigator, an unrelated FastAPI application; no Ruach website source or deployment credentials were present. The public Ruach URL could not be reached from the development environment. Its actual framework, fonts, and hosting remain unverified.

## Integration and files

The existing FastAPI app now mounts an isolated application at `/institute`. The root response and `/api/v1` API remain intact. This is a server-rendered Jinja application with a small CSS/JavaScript layer; there is no React bundle or new frontend framework. It uses system Arial/Helvetica and Georgia, with configurable tokens at the top of `app/institute/static/portal.css`.

Created:

- `app/institute/application.py`: application factory, portal-scoped security headers, safe error handling, session refresh persistence, access-log filtering.
- `app/institute/config.py`, `auth.py`, `supabase.py`: environment configuration, encrypted cookie/session handling, centralized authorization, Supabase HTTP boundary.
- `app/institute/routes.py`, `media.py`, `__init__.py`: routes and private R2 audio/PDF streaming with per-request authorization.
- `app/institute/templates/{base,login,portal,course,components,error}.html`: reusable server-rendered UI.
- `app/institute/static/{portal.css,portal.js,favicon.svg}`: responsive styles, progressive loading/audio controls, favicon.
- `app/institute/.env.example`: required variable names only.
- `supabase/migrations/202609160001_institute.sql`: transactional schema, grants, RLS, private authorization helpers, and two-course/five-week seed.
- `supabase/admin/enroll_student.sql`: guarded administrative enrollment transaction.
- `supabase/templates/magic-link.html`: student sign-in email installed and verified in Supabase.
- `scripts/institute/create_auth_user.py`: optional local administrative helper; creates a passwordless Auth user without sending email.
- `tests/institute/test_portal.py`, `tests/institute/check_rls.mjs`: route/authentication tests and executable PostgreSQL RLS tests.
- This setup guide.

Modified:

- `app/main.py`: mount the isolated portal.
- `pyproject.toml`: add Jinja2, cryptography, and email-validator; include nested application packages and template/static assets in wheels.
- `app/core/logging.py`: fix a pre-existing import incompatible with the declared python-json-logger 2.x dependency, which prevented the host application from starting.
- `.gitignore`: ignore generated Python package metadata.
- `README.md`: link to this portal's setup guide.

No existing course content, other untracked work, or unrelated business logic was changed.

## Routes

| Route | Purpose |
| --- | --- |
| `GET /institute` | Login; FastAPI canonicalizes the mounted root to `/institute/` |
| `POST /institute/auth/login` | Validate email and request a Magic Link |
| `GET /institute/auth/callback` | Verify one-time email token and establish cookies |
| `POST /institute/auth/logout` | Revoke this Supabase session and clear cookies |
| `GET /institute/portal` | Approved-student dashboard |
| `GET /institute/architecture-of-the-mind` | Enrolled-student course page |
| `GET /institute/{slug}` | Same protected course rendering for future course data |
| `GET /institute/media/{lesson_uuid}/audio` | Authorized R2 audio streaming with byte-range support; 404 until configured |

| `GET /institute/media/{lesson_uuid}/notes` | Authorized inline PDF stream |

Authenticated users without an active student record or valid enrollment receive a 403 access state. Missing, tampered, or expired sessions redirect to login. Missing configuration and connection failures fail closed with a generic 503 page. Unconfigured login remains viewable.

## Supabase setup

Use a dedicated Supabase project for Ruach where possible. These steps require project administrator access. Public sign-up is disabled in `ruach-auth`. Database setup and callback URLs below have already been applied there; do not re-run the one-time migration. Temporary Gmail SMTP and the Magic Link template are now applied. These instructions also serve as the reproducible setup guide for a new project.

1. In **SQL Editor**, run `supabase/migrations/202609160001_institute.sql` once as the project administrator. The transaction creates new `institute` and `institute_private` schemas; it intentionally fails if they already exist instead of overwriting an existing system. When using the Supabase CLI migration runner, apply the same checked-in migration through your normal process.
2. In **Project Settings → Data API → Exposed schemas**, add `institute`, preserving existing entries. Do **not** expose `institute_private` or `auth`. The portal explicitly sends `Accept-Profile: institute` on its PostgREST requests.
3. In **Authentication → Sign In / Providers**, enable Email and disable **Allow new users to sign up**. Do not enable anonymous sign-in. The application also sends `create_user: false` for every login request. There are no password fields or password-reset flows.
4. In **Authentication → URL Configuration**, set Site URL to `https://ruach.zionencounter.com/institute`. Add `https://ruach.zionencounter.com/institute/auth/callback?state=*` to redirect URLs. The query wildcard accommodates a server-generated anti-CSRF nonce; the server always constructs the destination from its configured origin. Do not add broad host-wide wildcards.
5. In **Authentication → Email Templates → Magic Link**, set the subject to **Your Ruach Institute sign-in link** and use `supabase/templates/magic-link.html` for the body. The prepared copy is below. Keep `.RedirectTo`, including its `state` query parameter. Do not substitute `.ConfirmationURL` or a hardcoded callback URL:

   ```html
   <p>Dear student,</p>
   <p>Please find below the link to access your Ruach Institute student portal.</p>
   <p><a href="{{ .RedirectTo }}&amp;token_hash={{ .TokenHash }}&amp;type=email">Access your student portal</a></p>
   <p>This link can only be used once. Please open it in the same browser where you requested it.</p>
   <p>If you did not request this email, you can safely ignore it.</p>
   <p>Warm regards,<br>Ruach Institute</p>
   ```

6. Configure **Custom SMTP** with a verified sender before inviting the class. Supabase's default email service is unsuitable for general production delivery. Disable email-provider link tracking so it does not rewrite one-time links. Set Magic Link expiry to at most one hour and retain Supabase's email resend/rate limits. Test an actual delivered link: its URL must contain both `state` and `token_hash`.
7. Retain the default refresh-token reuse grace period for concurrent browser requests. Configure session time limits as appropriate for your Supabase plan. No custom password settings are needed.
8. Obtain the project HTTPS URL and publishable key from **Project Settings → API Keys**. A legacy anon key also works. Never put a service-role/secret key in the publishable-key setting.

Temporary Gmail SMTP is saved and enabled: sender and username `jerrish.github@gmail.com`, sender name `Ruach Institute`, host `smtp.gmail.com`, port `465`, resend interval `60` seconds. The user entered the Google app password directly in Supabase; no app password was collected or saved locally. The custom Magic Link subject and body were saved and independently checked against the local template. The approved test student (`RI-TEST-001`) was provisioned and enrolled through the Auth admin and Data APIs without assigning a password. Its auth ID is `2b923db1-78f3-46c6-a2fe-c51b53010f13`. Initial requests failed with Google SMTP 535/5.7.8. After the user updated the credentials, the real browser Magic Link request succeeded with HTTP 200 at 2026-09-16 23:44:56 UTC (Auth log 4e97c05f-fe98-4e98-8792-a83b594cc33d). Inbox receipt and the authenticated portal flow still require the user to open the link in the same Codex browser.

The email flow follows Supabase's [passwordless email guidance](https://supabase.com/docs/guides/auth/auth-email-passwordless), and the server-only cookie approach uses its [session guidance](https://supabase.com/docs/guides/auth/sessions). Review the [custom SMTP requirements](https://supabase.com/docs/guides/auth/auth-smtp) when configuring mail.

## Environment

Add these four entries to the project root `.env` locally and to your runtime secret/environment settings in production. The example file contains no values or credentials.

| Variable | Required value |
| --- | --- |
| `SUPABASE_URL` | Project HTTPS URL, with no `/auth` or `/rest` suffix |
| `SUPABASE_PUBLISHABLE_KEY` | Publishable key or legacy anon key |
| `INSTITUTE_COOKIE_KEY` | A persistent Fernet encryption key, shared by all application instances |
| `INSTITUTE_ORIGIN` | `https://ruach.zionencounter.com` with no trailing slash/path |

Generate the cookie key once in a private terminal and save its output in your secret manager:

```sh
python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'
```

Do not regenerate it on each start. Rotating it signs all browsers out. The portal does **not** require `SUPABASE_SERVICE_ROLE_KEY`. The optional provisioning helper asks for an administrator credential interactively and never stores it. Do not add that key to the web application's environment.

For local email testing use `INSTITUTE_ORIGIN=http://127.0.0.1:8765` and add `http://127.0.0.1:8765/institute/auth/callback?state=*` to the Supabase redirect list. HTTP cookies are allowed only for localhost/127.0.0.1; production requires HTTPS. Use a separate development Supabase project.

## Approve and enroll each student

The permanent identity link is `students.auth_user_id → auth.users.id`. An email submitted by a browser or user-editable metadata never grants access.

1. Create the Auth account for the verified, approved student. An existing Auth account can be reused. To create a new account without a password or sending an invitation, run from the repository root after installing dependencies:

   ```sh
   python scripts/institute/create_auth_user.py
   ```

   Enter the approved email and a service-role key at the hidden prompt. The helper calls Supabase's administrative create-user endpoint with `email_confirm: true`. It sends no mail, grants no course access, and does not accept or store passwords. Marking an email confirmed here is an administrator action based on an already approved roster; the student must still prove email ownership with a Magic Link to get a session. If the account already exists, use it rather than repeatedly creating it.

2. Open `supabase/admin/enroll_student.sql` in SQL Editor. Replace the two marked values with the approved email and a unique student ID such as `RI-001`, then run it as administrator. It resolves the existing Auth UUID, inserts the active student, and enrolls them in Architecture of the Mind atomically. Missing Auth users, missing courses, and duplicates fail instead of silently changing another record.
3. Tell the student to visit `/institute` and request their link. No portal self-registration is available.

To pause all access, set the student's `status` to `inactive`. To pause only a course, set that enrollment's `status` to `inactive`. Changes affect subsequent reads immediately through RLS. Do not delete Auth users as the normal way to pause access.

## Database authorization

Tables live in the `institute` schema:

| Table | Purpose / read policy |
| --- | --- |
| `students` | Approved roster; read only one's own limited identity/status columns with a live session. Email and timestamps are not granted to authenticated clients. |
| `courses` | Course catalog; active students see coming-soon metadata and active courses in which they are actively enrolled. |
| `enrollments` | Student/course foreign keys; active students read only their own enrollment rows. |
| `lessons` | Week content; only `published` lessons for an actively enrolled student in an active course. Locked rows cannot be queried directly. |

RLS is enabled on every table, with no client write grants or write policies. Anonymous clients have no access to the schema. Definer helpers have an empty search path, fully qualified table references, restricted execution grants, and derive identity from `auth.uid()` rather than accepting a client student ID. They check the JWT's `session_id` against `auth.sessions`, so a revoked session cannot continue reading through PostgREST with its old JWT. Supabase administrative roles intentionally bypass RLS and must remain trusted.

The migration seeds precisely two courses and five lessons. Only Week 1 is published. The server queries only published lessons and constructs locked sections from `total_weeks`; it never reads their text into the HTML. To add a future course, insert its course record, lesson records, and enrollments through administration. To unlock a week, publish that lesson through administration. No separate page implementation is required.

## Authentication and request flow

1. Same-origin POST validates email and sends Supabase an OTP/Magic Link request with user creation disabled. Existing and unknown accounts get the same confirmation text.
2. An encrypted, short-lived login-state cookie binds the link to the requesting browser. The callback checks it before exchanging the token hash with `/auth/v1/verify`. Link scanners without that cookie cannot consume the token through this callback.
3. Supabase access and refresh tokens are stored in separate encrypted, HttpOnly, Secure, SameSite=Lax cookies scoped to `/institute`. Tokens never enter HTML, JavaScript, or localStorage. Cookie lifetime is 30 days; refresh occurs on server requests when the access token is near expiry.
4. Every protected request validates the user with Supabase, then reads their approved student status using their JWT. Course pages also check course availability and active enrollment. Database RLS independently enforces the same boundary.
5. Logout is a same-origin POST. It revokes the local Supabase session before clearing cookies. Network failure is reported instead of falsely claiming successful logout.

No arbitrary `next` URL is accepted. The Magic Link must be opened in the browser used to request it; cross-device use requires requesting a new link there. Supabase tokens and full request bodies are not logged. The Uvicorn portal access filter removes callback request-line logging, but **proxy/CDN/APM logs must also omit query strings**.

## Deployment

This implementation requires a Python/ASGI runtime; it cannot be placed on static-only hosting or directly copied into WordPress. If the actual Ruach site uses another stack, keep its current host and reverse proxy only `/institute` and `/institute/*` to this application. Preserve the full path, HTTPS host, query string, cookies, and Origin header. Do not cache portal responses at a CDN or proxy.

Install/build with the project's Python 3.11+ environment:

```sh
python -m venv .venv
.venv/bin/pip install -e '.[dev]'
.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8765 --no-access-log
```

The existing Dockerfile already copies `app/`, including the portal. Normal `docker compose up --build` also runs the unrelated scaffold database, which the institute portal does not use. Configure `APP_DEBUG=false` in production and supply the four institute variables. Serve through your existing TLS reverse proxy. Route only the portal prefix from the Ruach domain, leaving unrelated AeroSOC endpoints private.

For Nginx, the following locations belong in the existing TLS server block. Use the real internal upstream address and preserve existing locations:

```nginx
location = /institute {
    access_log off;
    return 308 /institute/;
}
location ^~ /institute/ {
    access_log off;
    proxy_pass http://127.0.0.1:8765;
    proxy_set_header Host $host;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_cache off;
}
```

`proxy_pass` deliberately has no trailing path so the prefix is preserved. Configure equivalent privacy protections in any load balancer or APM service. Application responses include `no-store`, `noindex/nofollow`, CSP, frame-ancestors, nosniff, no-referrer, and restrictive Permissions-Policy, scoped to the portal. Keep host-wide HSTS/TLS decisions in the existing host configuration.

Before launch, send a real Magic Link and verify approved, unapproved, inactive, and unenrolled accounts against the configured project; verify logout/session refresh and direct URLs. Do not advertise the portal as production-ready until this deployment acceptance pass is complete.

## Validation and remaining scope

Verified locally: **21 portal tests passed; 17 actual PostgreSQL RLS checks passed**. Browser checks passed for login, dashboard, and course at 1440, 768, 390, and 320 CSS pixels with no horizontal overflow. Automated axe WCAG A/AA checks reported no violations on the three pages at desktop and mobile widths; keyboard navigation and full-height course layout were also checked. Protected-page visual checks used disposable local test fixtures with placeholder content, not an authentication bypass in the application. These checks do not replace manual assistive-technology testing.

The Python wheel built successfully and includes the templates/static assets. MyPy passes for all 62 application source files; Ruff and Bandit pass for the new portal/provisioning code. The full existing suite reports 26 passes and the one unrelated failure described below. Live Supabase configuration and anonymous-access denial have since been verified; real email delivery and authenticated student sign-in remain untested.

Automated portal tests cover logged-out direct URLs; approved dashboard/course access; unapproved, inactive, pending, and unenrolled denial; successful and failed/expired callback; forged cookies and failed identity checks; access-token refresh and expired refresh token; logout and logout network failure; same-origin POST protection; invalid email; unavailable/unauthorized audio; disabled signups in the Supabase HTTP request; RLS profile/JWT headers; and fail-closed missing configuration.

Run `pytest tests/institute -q`. The independent RLS harness runs the actual migration/policies in disposable PGlite PostgreSQL with a minimal Auth schema fixture. It checks cross-student isolation, denied writes/admin columns, locked/cross-course lessons, inactive enrollment/student denial, revoked-session denial, and anonymous denial. It is not a live Supabase integration test:

```sh
npm install --prefix /tmp/ruach-qa @electric-sql/pglite
node tests/institute/check_rls.mjs /tmp/ruach-qa/node_modules/@electric-sql/pglite/dist/index.js
```

The existing repository-wide triage integration test fails independently because its mock recommendation has one citation while the configured minimum is two. That unrelated business logic was left unchanged.

Intentional placeholders: overview; Week 1 description, Notes and Reflection Questions; unreleased weeks; future course; a three-second test tone and one-page placeholder PDF. Until R2 is configured, media remains unavailable. Once configured, playback starts on request and seek/volume activate after metadata loads. The custom player includes play/pause, seek, elapsed/duration and volume behaviors for R2 media.

Prepared locally: private R2 audio/PDF streaming, placeholder assets and an upload helper. The private R2 bucket and Week 1 placeholder objects have been created, the approved read-only credential is configured locally, and live file/range retrieval passed; see [Cloudflare setup](../cloudflare/README.md).

Explicitly deferred: custom document rendering; real course copy/audio/PDFs; grading, quizzes, certificates, payments, discussions, progress tracking, student submissions, notifications, analytics, watermarks/DRM, and an admin interface. R2 files stream through same-origin endpoints; signed upstream URLs and credentials stay on the server. Notes open as an inline PDF in a new tab. A custom PDF viewer remains deferred.

Security limits: authorized browser content can be copied or captured; there is no DRM or claim otherwise. Revoking access cannot erase content already displayed. This V1 has no automatic live-session check while a student remains on an already rendered page; new requests reauthorize. Supabase plan-dependent time-box/inactivity limits take effect on refresh according to Supabase's session behavior. The existing website shares the origin, so its own scripts and hosting must be secured. There is no production auth bypass or demo mode.


## Browser sign-in test correction

A real native form submission exposed that `Referrer-Policy: no-referrer` can cause
browsers to submit `Origin: null`, which the strict origin check correctly rejected.
Normal portal pages now use `same-origin`; token-bearing callback responses retain
`no-referrer`. Strict Origin validation remains unchanged. The next real form POST
reached Supabase and exposed the SMTP credential error above. All 29 portal tests,
Ruff and portal mypy passed after the fix.
