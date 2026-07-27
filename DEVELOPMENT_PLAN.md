# Talent Radar Collection Plan

## Product Goal

Run a local, account-based collection app that can retain authenticated platform
profiles and collect authorized Facebook posts, comments, and replies in the
background.

Only platform connection, collection, storage, import, manual run configuration, and review are in
scope.

## Delivered

- Local accounts with scrypt password hashes and revocable opaque sessions.
- Per-user Facebook, TikTok, and Threads connection records.
- Existing Coc Coc profile selection, currently `Default` for Vũ Văn Huy.
- Official Facebook OAuth authorization with one-time state, server-side code
  exchange, `/me` verification, and DPAPI-protected token storage.
- Playwright Facebook collection without SendKeys, clipboard access, or foreground
  keyboard/mouse control.
- Saved per-source run configurations, manual Run now, job history, error state,
  and reauthentication state.
- JSON export followed by import into raw and normalized records.
- Authenticated React views for overview, posts, comments, runs, and settings.
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

- Coc Coc `Default` is used to open platform authorization pages.
- Facebook Connect opens Meta's OAuth permission screen, not `facebook.com/me`.
- OAuth state expires after ten minutes and can be consumed only once.
- Facebook becomes connected only after the callback exchanges the code and verifies
  the Facebook account through Graph API `/me`.
- Settings refreshes connection state automatically and has no manual Confirm step.
- A disconnected connection disables its saved run configurations but preserves
  the profile.
- Deleting a run configuration is a soft delete so collection history remains
  traceable.
- TikTok and Threads cannot run until their collectors are implemented.
- Collection jobs are created only by an explicit dashboard action.

## Next Collection Work

1. Add Facebook fixture captures and selector regression tests.
2. Add resumable group checkpoints for long collection jobs.
3. Add configurable comment/reply expansion limits.
4. Add retry policy with bounded backoff for temporary navigation failures.
5. Package the local launcher as a signed Windows tray application.

## Completion Criteria

- Accounts cannot access another account's connections, run configurations, or jobs.
- Passwords and bearer tokens are never stored in plaintext.
- Facebook authorization is verified by OAuth callback; access tokens are never
  stored in plaintext.
- A manual run produces one job, one export, and imported records.
- Login expiry changes the connection to `reauth_required`.
- The dashboard reports queued, running, completed, failed, and disconnected states.
