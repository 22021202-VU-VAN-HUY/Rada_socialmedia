# Talent Radar Background Platform Connections

## ROLE: CONTRACTOR

### SCAN REPORT

#### Executive Summary

Talent Radar is a local Python application using FastAPI, SQLAlchemy, Streamlit,
SQLite/Postgres, and a foreground PowerShell crawler that controls Coc Coc with
SendKeys and the clipboard. The existing import adapter and export dashboard are
sound extension points. This upgrade keeps those paths working while adding local
accounts, an explicitly selected existing browser profile, connection management, and scheduled Facebook
collection that does not take keyboard or mouse focus.

#### Current Architecture

- FastAPI owns source registry and import endpoints.
- SQLAlchemy owns source, crawl, raw item, and normalized item persistence.
- Streamlit reads JSON exports directly.
- `scripts/crawl_facebook_coccoc.ps1` proves the Facebook DOM extraction rules but
  requires a foreground Coc Coc window.
- Configuration is environment-driven through Pydantic settings.

#### Constraints And Risks

- Facebook markup and labels can change without notice.
- Playwright supports a persistent browser profile, but a profile directory cannot
  be opened by two browser processes at once.
- The user requires Talent Radar to use the existing Coc Coc profile for Vũ Văn Huy.
  The app must identify it explicitly and must not inspect or export cookie/password files.
- Background collection still requires the Windows user session and a valid
  Facebook login. It does not bypass login, CAPTCHA, checkpoints, or platform rules.
- TikTok and Threads need separate collectors; this release must not claim they can
  be collected.

### RRI REPORT

The user already approved implementation after the architecture discussion, so the
focused RRI is resolved from the repository and conversation.

| ID | Requirement | Resolution |
| --- | --- | --- |
| REQ-001 | Run collection in the background | A worker inside the API polls enabled schedules and starts minimized Coc Coc contexts with the selected profile. |
| REQ-002 | Create and sign in to an account | Local email/password accounts with scrypt hashes and revocable bearer sessions. |
| REQ-003 | Connect individual platforms in Settings | Facebook, TikTok, and Threads connection rows launch persistent platform-specific Coc Coc profiles. |
| REQ-004 | Reuse an authenticated browser session | Reuse Coc Coc `Default` for Vũ Văn Huy without reading or copying cookie/password files. |
| REQ-005 | Collect Facebook posts and comments | Port the proven DOM rules to Playwright and import collected records through the existing adapter. |
| REQ-006 | Schedule and run collection on demand | Per-source interval, enable/disable, max-post settings, and Run now. |
| REQ-007 | Preserve current data and manual crawler | Add tables and services without deleting current exports, imports, or PowerShell fallback. |
| REQ-008 | Make unsupported states honest | TikTok and Threads can be connected, but scheduling returns an adapter-not-available error. |

#### Assumptions

- This is a local Windows application, not a public multi-tenant SaaS.
- One API worker instance operates on the local database.
- Coc Coc is installed at the standard path unless overridden.
- The user closes the login browser before confirming or starting collection.
- Collection is limited to content the connected account is permitted to view.

### VISION

Talent Radar should behave like a quiet local collection app: open it, sign in, link
a platform once, choose a source and interval, and let the API continue collection
after the dashboard is closed. Settings makes connection state explicit. Jobs make
failures actionable, especially expired sessions and unsupported adapters.

Success means:

- Registration, login, logout, and session restoration work.
- Each user can see and modify only their own connections and schedules.
- Connecting Facebook opens the exact configured Coc Coc profile and verifies login.
- A due or manually triggered Facebook schedule creates a job and stores an export.
- The resulting posts/comments enter the existing normalized data store.
- The UI clearly reports disconnected, pending, connected, running, failed, and
  reauthentication-required states.

### BLUEPRINT

#### Data

- `users`: local identity and scrypt password hash.
- `auth_sessions`: hashed opaque tokens with expiry and revocation.
- `platform_connections`: per-user/platform profile path and connection status.
- `collection_schedules`: per-user source, interval, limits, and next run.
- `collection_jobs`: immutable run history plus counts, output path, and error.

#### Services

- `auth`: password hashing, token creation, authentication, and revocation.
- `browser_profiles`: existing-profile discovery, explicit Coc Coc launch, and login verification.
- `facebook_collector`: Playwright persistent-context collection.
- `collection`: schedule CRUD, job execution, export, and import.
- `background_worker`: due-schedule polling with graceful lifecycle shutdown.

#### API

- `/auth/register`, `/auth/login`, `/auth/me`, `/auth/logout`
- `/connections`, `/connections/{platform}/connect|confirm|disconnect`
- `/schedules`, `/schedules/{id}`, `/schedules/{id}/run-now`
- `/jobs`

#### Interface

Streamlit owns authentication state and calls the API. It provides Overview,
Posts, Comments, Runs, and Settings views. Settings contains connection actions and
schedule management; no password or browser cookie is exposed to the UI.

#### Operations

`scripts/start_talent_radar.ps1` starts the API (and worker) plus dashboard as hidden
processes and records their PIDs. `scripts/stop_talent_radar.ps1` stops only those
recorded processes. Windows Task Scheduler can invoke the start script at logon.

### CONTRACT

#### Acceptance Criteria

- AC-001: A new user can register, receive a session, load `/auth/me`, and log out.
- AC-002: Passwords and bearer tokens are not stored in plaintext.
- AC-003: User A cannot list, run, update, or delete User B's schedules/connections.
- AC-004: Connect opens the correct platform URL with Coc Coc `Default` for Vũ Văn Huy.
- AC-004B: Confirm rejects a closed browser, visible login form, or Facebook checkpoint.
- AC-005: Confirm marks a pending connection connected; disconnect disables its schedules.
- AC-006: Worker claims due schedules once and records terminal job status.
- AC-007: Facebook collection writes a compatible JSON export and imports its records.
- AC-008: Login-required and unsupported-platform failures are visible and actionable.
- AC-009: Existing import adapter tests remain green.
- AC-010: Dashboard is usable at desktop and narrow viewport widths.

#### Out Of Scope

- Official Facebook OAuth/API integration.
- Copying or controlling Huy's everyday Coc Coc profile.
- CAPTCHA/checkpoint bypass or collection of inaccessible/private content.
- Cloud hosting, billing, organization roles, password reset email, or encryption
  key management.
- TikTok and Threads post/comment collectors.

#### Decision Log

- Use Python `hashlib.scrypt` to avoid introducing an auth framework for a local MVP.
- Use opaque database sessions instead of JWT so logout revocation is immediate.
- Run the worker in the FastAPI lifespan to keep deployment simple and observable.
- Use a headed minimized browser because an authenticated social session is more
  reliable than headless operation; it does not require foreground input.
- Retain the PowerShell crawler as a manual fallback.

### TASK GRAPH

| TIP | Depends On | Deliverable |
| --- | --- | --- |
| TIP-001 | Contract | Models, schemas, authentication service and API |
| TIP-002 | TIP-001 | Connection service/API and exact existing Coc Coc profile |
| TIP-003 | TIP-002 | Playwright Facebook collector and export/import bridge |
| TIP-004 | TIP-001, TIP-003 | Schedule/job service and lifecycle worker |
| TIP-005 | TIP-001, TIP-002, TIP-004 | Authenticated Streamlit dashboard |
| TIP-006 | TIP-004, TIP-005 | Background launch scripts, docs, tests, verification |

## ROLE: BUILDER

### Build Notes

Implementation follows the task graph above. Completion and verification evidence is
recorded below after the build.

### COMPLETION REPORT

| TIP | Status | Evidence |
| --- | --- | --- |
| TIP-001 | Complete | New account/session models, scrypt auth service, bearer dependency, and auth API routes. |
| TIP-002 | Complete | Per-user connection models/API and explicit existing-profile launcher. |
| TIP-003 | Complete | Playwright persistent-profile Facebook collector and compatible export/import bridge. |
| TIP-004 | Complete | Schedule/job services, soft-delete history, due polling, and FastAPI lifecycle worker. |
| TIP-005 | Complete | Authenticated Overview, Posts, Comments, Runs, and Settings Streamlit views. |
| TIP-006 | Complete | Hidden start/stop scripts, optional logon-task installer, documentation, and 11 tests. |

#### Files Added

- `src/talent_radar/services/auth.py`
- `src/talent_radar/services/browser_profiles.py`
- `src/talent_radar/services/facebook_collector.py`
- `src/talent_radar/services/collection.py`
- `src/talent_radar/services/background_worker.py`
- `scripts/start_talent_radar.ps1`
- `scripts/stop_talent_radar.ps1`
- `scripts/install_background_task.ps1`
- Auth, browser-profile, and collection tests.

#### Operational Result

- The local `.env` was switched from an unavailable localhost PostgreSQL service to
  the repository's SQLite default.
- API and worker are running at `http://127.0.0.1:8000`.
- Dashboard is running at `http://127.0.0.1:8501`.
- The Windows logon task script was created but not executed, avoiding an unrequested
  system-level change.

### VERIFY REPORT

| Acceptance Criterion | Result | Evidence |
| --- | --- | --- |
| AC-001 | Pass | API smoke test completed register, `/auth/me`, and logout. |
| AC-002 | Pass | Tests assert password and bearer token are not stored in plaintext. |
| AC-003 | Pass | Ownership tests reject cross-user schedule update and enqueue. |
| AC-004 | Pass | Browser-profile tests assert `Default`, account Vũ Văn Huy, and platform URL. |
| AC-004B | Pass | Tests reject a visible Facebook login form and accept an authenticated `/me` page. |
| AC-005 | Pass | Connection API confirms state and disconnect disables related schedules. |
| AC-006 | Pass | Due-schedule test proves only one active job is enqueued. |
| AC-007 | Pass | Mock Facebook job writes JSON and imports one post plus one comment. |
| AC-008 | Pass | Reauthentication and unsupported adapter paths produce explicit states/errors. |
| AC-009 | Pass | Full suite: 11 tests passed, including all original import adapter tests. |
| AC-010 | Partial | Streamlit harness rendered auth, overview, and settings without exceptions; browser viewport screenshots were unavailable because no controllable browser session was exposed. |

#### Commands

```text
python -m compileall -q src tests
python -m pytest -q
git diff --check
```

#### Residual Risks

- A real Facebook login and live collection were not forced during verification,
  because doing so would open an interactive login and may trigger platform
  checkpoints. The user should connect and verify the selected profile through Settings.
- Facebook DOM changes can break extraction selectors.
- Coc Coc is a custom Chromium executable; Playwright documents that custom
  executables may have compatibility differences from bundled Chromium.
- Visual desktop/mobile screenshot review remains outstanding due to unavailable
  browser-control context. Streamlit component-level rendering passed.

### CONNECTION FLOW CORRECTION

User feedback showed that exposing a launcher-managed browser mode was still too
technical. Facebook connection now follows a one-click browser flow:

- Connect opens `facebook.com/me` in a normal tab of Coc Coc `Default`.
- Coc Coc may already be open and displaying localhost.
- A Windows UI Automation monitor reads only the address bar value.
- Facebook login and checkpoint URLs remain pending or require reauthentication.
- A redirect to the signed-in profile marks the connection connected.
- Settings refreshes every three seconds and no longer asks for manual confirmation.
