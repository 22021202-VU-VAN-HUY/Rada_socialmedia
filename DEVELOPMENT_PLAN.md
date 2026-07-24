# Talent Radar Collection Plan

## Product Goal

Run a local, account-based collection app that can retain authenticated platform
profiles and collect authorized Facebook posts, comments, and replies in the
background.

Only platform connection, collection, storage, import, scheduling, and review are in
scope.

## Delivered

- Local accounts with scrypt password hashes and revocable opaque sessions.
- Per-user Facebook, TikTok, and Threads connection records.
- Existing Coc Coc profile selection, currently `Default` for Vũ Văn Huy.
- Active Facebook login verification before a connection can become connected.
- Playwright Facebook collection without SendKeys, clipboard access, or foreground
  keyboard/mouse control.
- Per-source schedules, Run now, job history, error state, and reauthentication state.
- JSON export followed by import into raw and normalized records.
- Authenticated Streamlit views for overview, posts, comments, runs, and settings.
- Hidden local launcher plus an optional Windows logon task installer.
- Manual foreground PowerShell crawler retained as fallback.

## Collection Contract

### Post

- `external_id`
- `author`
- `group`
- `content`
- `reaction_count`
- `reported_comment_count`
- `collected_comment_count`
- `url`

### Comment Or Reply

- `external_id`
- `parent_external_id`
- `author`
- `published_label`
- `content`
- `is_reply`
- `parent_author`
- `permalink`

## Operational Rules

- A platform uses the configured existing Coc Coc profile.
- Coc Coc needs one restart through `Open Talent Radar.cmd` when migrating from a
  normally opened browser to launcher-managed mode.
- After migration, localhost, platform login, verification, and collection share
  the same Coc Coc process through local port `9223`.
- `data/coccoc_huy_user_data` is a junction to the real User Data directory, not a
  copied browser profile.
- The login window remains open while Confirm verifies Facebook `/me`.
- The worker attaches a background tab without closing the localhost tab.
- A disconnected connection disables its schedules but preserves the profile.
- Deleting a schedule is a soft delete so collection history remains traceable.
- TikTok and Threads cannot be scheduled until their collectors are implemented.

## Next Collection Work

1. Add Facebook fixture captures and selector regression tests.
2. Add resumable group checkpoints for long collection jobs.
3. Add configurable comment/reply expansion limits.
4. Add retry policy with bounded backoff for temporary navigation failures.
5. Package the local launcher as a signed Windows tray application.

## Completion Criteria

- Accounts cannot access another account's connections, schedules, or jobs.
- Passwords and bearer tokens are never stored in plaintext.
- Facebook login is verified and persists in the selected existing profile.
- A due schedule produces one job, one export, and imported records.
- Login expiry changes the connection to `reauth_required`.
- The dashboard reports queued, running, completed, failed, and disconnected states.
