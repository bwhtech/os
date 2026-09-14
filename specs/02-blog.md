# 02: Blog

Status: Draft

## Why?

bwh.tech/blog has likes and comments. Comments publish instantly, and there is no control panel. To hide a comment today, you run SQL in `turso db shell`. There are no stats and no alert when a person comments.

The Blog module lets you moderate comments, see engagement stats, and get an email for new comments.

## What?

- A Comments page, grouped by post. Hide, unhide, and delete comments, one at a time or in bulk.
- An Overview page with totals, comments per week, and top posts.
- An email when new comments arrive.

### How the blog works

The blog is the Astro site in `bwhtech_blog`. Netlify hosts it. Three Netlify functions read and write a Turso (libSQL) database:

| Function | Action |
|---|---|
| `netlify/functions/engagement.ts` (GET) | Returns the likes and the visible comments of a post. It removes the email before the response. |
| `netlify/functions/comment.ts` (POST) | Checks a honeypot and a 3 second minimum fill time, validates the fields, limits by IP, and inserts the comment. The comment is visible at once. |
| `netlify/functions/like.ts` (POST) | Adds 1 to the like count of a post. There is no unlike. |

The schema is in `db/schema.sql`:

- `comments(id, post_id, name, email, body, created_at, hidden)`. `id` is `AUTOINCREMENT`. `created_at` is Unix seconds. `hidden` is 0 or 1. The public read path uses `hidden = 0`.
- `post_likes(post_id, likes, updated_at)`. One row for each post.
- `rate_limits`. Internal to the functions. OS does not use this table.

The post id is `<category>/<slug>`, for example `stories/the-frappeverse-2026-experience`. The database has no post titles. `https://bwh.tech/rss.xml` has the title and the link of each published post. The link is `https://bwh.tech/blog/<post_id>/`.

There are two Turso databases. The dev database is in the blog `.env`. The production database is `bwhtech-blog-prod`. Its credentials are Netlify secrets.

### Decisions

| Topic | Decision |
|---|---|
| Data | OS reads and writes Turso live. There are no comment doctypes. This is an exception to the principle "a page never waits on a live third-party call". A copy of the comments would drift, and the data is small. |
| Turso client | Plain `requests` to the Turso HTTP API (`POST <url>/v2/pipeline`). There is no new Python dependency. |
| Token | A full-access token for each database, made for OS only. Hide and delete are writes, and Turso tokens cannot be limited to one table. Netlify keeps its own token, so you can revoke each token alone. |
| Environments | Each site has its own credentials in `Blog Settings`. The dev site uses the dev database. The production site uses `bwhtech-blog-prod`. |
| Database host | Blog pages show the database host in the page header, so you always know which database you act on. |
| Moderation | Comments publish instantly. OS hides, unhides, and deletes after. There is no approve-first queue. |
| Delete | A hard `DELETE`, after a confirmation dialog. `AUTOINCREMENT` never reuses an id, so a delete does not break the notification watermark. The public site uses the id only as a Vue list key. |
| Post titles | From `rss.xml`, cached in Redis for 1 hour. A post that is not in the feed shows its post id. |
| Loading | The Comments page loads all comments in one query, newest first, with a cap of 2,000. Grouping, filters, and search run in the browser. |
| Notifications | A scheduler job reads `WHERE id > <watermark>` every 5 minutes and sends one email for all new comments. The email goes through the `email_account` in `Mailing Settings`. |
| Access | System Manager only, like the rest of `/os`. Each API method checks the role again. |
| Names | The module is `Blog`. Frappe v16 no longer has the blog doctypes. The `frappe/blog` app also has a `Blog Settings` doctype, so do not install that app on this site. |

### Out of scope for v1

- A Posts page. Posts with no comments do not show.
- Approve-first moderation. This needs a blog change: `hidden` starts as 1, and the form says the comment waits for approval.
- Block an email. This needs a `blocked_emails` table and a check in `comment.ts`.
- Reply as the author. This needs an `is_author` column, a badge in `CommentList.vue`, and an insert path from OS.
- Edit a comment body.
- Unique commenters, return commenters, commenters who are subscribers, and posts with no engagement.
- Lazy load of comments for each post. Change to this when the cap is too small.

## How?

### Data model

All doctypes go in a new module, `Blog`.

**Blog Settings** (single doctype)

| Field | Type | Notes |
|---|---|---|
| turso_url | Data | The `libsql://` URL from the Turso dashboard. OS also accepts `turso://`. |
| turso_token | Password | A full-access database token |
| notify_new_comments | Check | |
| notify_email | Data (Email) | Gets the new comment email. The default is the email of the user who turns on notifications. |
| last_notified_comment_id | Int, read only | The watermark |

When `notify_new_comments` changes to on and the watermark is empty, `validate` sets the watermark to `MAX(id)`. This prevents an email for all old comments.

### Turso client

Put the client in `bwh_os/blog/turso.py`.

- `pipeline(statements)` sends all statements in one request and returns one result for each statement.
- The request goes to `https://<host>/v2/pipeline` with `Authorization: Bearer <token>`. Change `libsql://` and `turso://` to `https://`.
- The body is `{"requests": [{"type": "execute", "stmt": {...}}, ..., {"type": "close"}]}`.
- Send each argument with its type, for example `{"type": "integer", "value": "42"}`. Never put a value into the SQL text.
- The response gives each cell with its type. Change `integer` values to `int` and `null` to `None`.
- A response with `"type": "error"` raises `TursoError` with the message. A timeout is 10 seconds.
- Missing settings raise `TursoNotConfiguredError`.

### API

Put the methods in `bwh_os/blog/api.py`. Each method checks the System Manager role.

`get_comments()`

- Runs `SELECT id, post_id, name, email, body, created_at, hidden FROM comments ORDER BY created_at DESC, id DESC LIMIT 2001` and `SELECT post_id, likes FROM post_likes` in one pipeline.
- Returns `{"db_host", "truncated", "posts": [{"post_id", "title", "url", "likes", "comments": [...]}]}`.
- `truncated` is true when the query returns 2,001 rows. The method drops the last row.
- Orders posts by their newest comment.

`set_hidden(ids, hidden)`

- Validates that `ids` is a list of integers and `hidden` is 0 or 1.
- Runs `UPDATE comments SET hidden = ? WHERE id IN (...)`.

`delete_comments(ids)`

- Validates that `ids` is a list of integers.
- Runs `DELETE FROM comments WHERE id IN (...)`.

`get_overview()`

Runs these statements in one pipeline:

1. Total, visible, and hidden comments: `SELECT COUNT(*), SUM(hidden = 0), SUM(hidden) FROM comments`.
2. Total likes: `SELECT COALESCE(SUM(likes), 0) FROM post_likes`.
3. Comments per week for the last 12 weeks. Group by the start of the week in Python and fill empty weeks with 0.
4. Top 5 posts by comments: `GROUP BY post_id ORDER BY COUNT(*) DESC LIMIT 5`.
5. Top 5 posts by likes: `ORDER BY likes DESC LIMIT 5`.

`test_connection()`

- Runs `SELECT 1` and returns the database host.

### Notifications

Put the job in `bwh_os/blog/notifications.py`. It runs every 5 minutes (`*/5 * * * *`).

1. If `notify_new_comments` is off, stop.
2. If the watermark is empty, set it to `MAX(id)` and stop.
3. Get `SELECT ... FROM comments WHERE id > ? ORDER BY id LIMIT 50`.
4. If there are no rows, stop.
5. Send one email to `notify_email` with `frappe.sendmail` through the `Mailing Settings` email account. Group the comments by post. Show the post title, the name, the time, and the body of each comment. Escape the name and the body.
6. Add a "Moderate in OS" link to `/os/blog/comments?post=<post_id>` for each post.
7. Set the watermark to the highest id in the rows.

If there are more than 50 new comments, the next run sends the rest.

### OS pages

The sidebar gets a **Blog** section with two pages.

**Overview** (`/blog`)

- Number cards: comments, hidden comments, and likes.
- A bar chart of comments per week for the last 12 weeks. Use the same frappe-ui charts as the Dashboard.
- Two short lists: top posts by comments and top posts by likes. Each post links to its group on the Comments page.

**Comments** (`/blog/comments`)

The layout follows the Tasks recipe in frappe-ui (`docs/components/recipes/TasksDesktop.vue`):

- A filter bar with `TabButtons` (All, Visible, Hidden), a search input, and the comment count. Search matches the name, the email, and the body.
- One group for each post, ordered by the newest comment. The group header is a full-width button with the post title, `12 comments · 3 hidden · 48 likes`, and Collapse or Expand on hover. A link icon opens the post on bwh.tech.
- A group starts open if it has a comment from the last 7 days, or if the `post` query parameter names it. Other groups start closed. Your toggles override the default.
- Each group is a `List` from `frappe-ui/list` in feed mode, with `selectable` and one shared `v-model:selection`.

Each row shows:

- An `Avatar` with the initials of the name.
- The name, the email in a muted color, and the time, for example "2h ago".
- The body, clamped to 3 lines, with an inline "Show more". Render the body as text. Never use `v-html`.
- A `Hidden` badge when the comment is hidden. A hidden row is dimmed.
- A menu with Hide or Unhide, and Delete.

When you select rows, a bar shows `3 selected`, Hide, Unhide, and Delete.

Delete opens a confirmation dialog. For one comment, it shows the name, the post, and the body. For many comments, it shows the count. The dialog says that you cannot undo a delete.

After a hide, an unhide, or a delete, the page loads the comments again. There are no optimistic updates. A failed action shows a toast and changes nothing.

If Turso is not set up, both pages show an empty state with an "Open Blog settings" button. If Turso does not respond, the page shows an error with a Retry button.

If `truncated` is true, the page shows "Showing the latest 2,000 comments".

**Settings**

`AppSettingsDialog` gets a **Blog** group with a **Comments** item:

- The Turso URL and token, and a "Test connection" button. The button shows the database host or the error.
- The notification toggle and the email.

### Local development

1. Copy `TURSO_DATABASE_URL` and `TURSO_AUTH_TOKEN` from the blog `.env` into `Blog Settings` on `bwhos.localhost`.
2. In `bwhtech_blog`, run `netlify dev --target-port 4321 --command "astro dev logs --follow"`.
3. Post a comment on a local post. See the comment in OS.
4. Hide the comment in OS. Reload the post and see that the comment is gone.

### Production setup

1. Run `turso db tokens create bwhtech-blog-prod`.
2. On the production site, set the URL and the token in `Blog Settings`.
3. Click "Test connection" and make sure that the host is `bwhtech-blog-prod`.

### Blog repo change

`db/schema.sql` says "Flip it to 1 rather than deleting, so ids stay stable". Change the comment: OS hides and deletes comments, and `AUTOINCREMENT` never reuses a deleted id.

## Slices

Each slice goes through all layers. Merge each slice alone.

### 1. Settings and read-only comments

- Add the `Blog` module and `Blog Settings`.
- Add the Turso client, `test_connection`, and the Blog settings in `AppSettingsDialog`.
- Add `get_comments`, the RSS title cache, and the grouped Comments page without actions.
- Show the database host in the page header. Show the empty and error states.
- Demo: set the dev database in settings, open Comments, see comments grouped by post with titles.

### 2. Hide and unhide

- Add `set_hidden`, the row menu, selection, and the selection bar with Hide and Unhide.
- Add the All, Visible, and Hidden tabs and search.
- Demo: hide a comment in OS, reload the post under `netlify dev`, see that the comment is gone.

### 3. Delete

- Add `delete_comments`, the Delete action in the row menu and the selection bar, and the confirmation dialog.
- Change the comment in `db/schema.sql` in the blog repo.
- Demo: delete two comments in bulk, see that they are gone from OS and from the post.

### 4. Overview

- Add `get_overview` and the Overview page.
- Demo: open Overview, see the totals, the weekly chart, and the top posts. Click a top post and see its open group.

### 5. New comment email

- Add the notification fields, the watermark on `validate`, and the scheduler job.
- Demo: turn on notifications, post two comments on the local blog, get one email in Mailpit, click "Moderate in OS", see the open group.

## Open questions

None.
