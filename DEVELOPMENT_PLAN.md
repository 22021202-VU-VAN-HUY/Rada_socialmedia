# Talent Radar - Facebook collection plan

## Goal

Collect posts, top-level comments, and replies that are visible in an authorized
Coc Coc Facebook session. Store traceable JSON/CSV data with post and comment
permalinks.

Only collection, storage, import, and review of source data are in scope.

## Supported inputs

- A public Facebook post URL.
- A public Facebook group URL.
- The example URLs in `textlinkmau.txt`.
- An already signed-in Coc Coc window selected by its Windows handle.

## Collection flow

1. Activate the selected Coc Coc window.
2. Open the post or group URL in that existing session.
3. Accumulate post permalinks while scrolling a group feed.
4. Open each post and expand visible reply threads.
5. Extract only the post dialog DOM.
6. Save posts and comments to JSON and CSV in `data/exports`.
7. Import the JSON into `RawItem` and `NormalizedItem` records when needed.

## Data contract

### Post

- `external_id`
- `author`
- `group`
- `content`
- `reaction_count`
- `reported_comment_count`
- `collected_comment_count`
- `url`

### Comment or reply

- `external_id`
- `parent_external_id`
- `author`
- `published_label`
- `content`
- `is_reply`
- `parent_author`
- `permalink`

## Guardrails

- Read only content visible in the selected Facebook session.
- Do not inspect cookies, passwords, local storage, or browser profile files.
- Do not like, share, post, message, hide, report, or delete anything.
- Do not bypass login walls, CAPTCHA, group permissions, or Facebook limits.
- Extract only the target post dialog; exclude Messenger, navigation, and feed
  content outside the requested post.

## Near-term work

1. Make Coc Coc window selection explicit when several windows are open.
2. Add retries for slow post dialogs and temporarily unavailable replies.
3. Add checkpoint files so a group crawl can resume after interruption.
4. Add database import commands and duplicate reporting to the dashboard.
5. Add fixture-based parser tests when Facebook changes its accessible labels.

## Completion criteria

- A sample post reports the same comment count in Facebook and the export.
- Replies preserve `parent_external_id`.
- Every stored item has a source post URL or comment permalink.
- Group collection retains links across Facebook's virtualized feed.
- The dashboard displays only collected posts, comments, replies, and run
  metadata.
