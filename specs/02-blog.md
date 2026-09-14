# 02: Blog

Status: Draft

## Why?

bwh.tech/blog has likes and comments. Comments publish instantly, and there is no control panel. Before this module, the likes and comments were in a Turso database, and you hid a comment with SQL in `turso db shell`.

The Blog module stores the likes and comments in OS. You moderate comments, see stats, and get an email for new comments.

## What?

- OS stores the likes and comments. The blog's Netlify functions call the OS API.
- A Comments page, grouped by post. Hide, unhide, and delete comments, one at a time or in bulk.
- An Overview page with totals, comments per week, and top posts.
- An email when a person comments.

### Decisions

| Topic | Decision |
|---|---|
| Storage | Doctypes in OS: `BWH Blog Post` and `BWH Blog Comment`. There is no Turso database. The `BWH` prefix prevents a clash with the doctypes of the `frappe/blog` app. |
| Blog path | Astro island, then a Netlify function, then the OS API. This is the same path as the newsletter signup. The API key never goes to the browser. |
| API user | The `OS Signup API` user that the signup already uses. The role can add subscribers, comments, and likes, and nothing else. |
| Rate limits | Frappe `@rate_limit`, keyed on the reader IP that the function passes. Likes also have a limit for each IP and post. A 429 from OS becomes a 429 from the function. |
| Bot checks | The functions keep the honeypot and the 3 second minimum fill time. A bot gets a fake success and nothing goes to OS. |
| Email | The functions drop the email before a comment goes to the browser. OS sends the email to the functions only for the avatar color. |
| Moderation | Comments publish instantly. OS hides, unhides, and deletes after. There is no approve-first queue. |
| Delete | A hard delete, after a confirmation dialog. |
| Post titles | From `rss.xml`, cached in Redis for 1 hour, and set when OS makes the post. A post that is not in the feed shows its post id. |
| Loading | The Comments page reads the doctypes with `useList`: all comments, newest first, with a cap of 2,000. Grouping, filters, and search run in the browser. |
| Updates | The page joins the Frappe `list_update` room of both doctypes and reloads when a comment or a like changes. There is no Refresh button. |
| Notifications | `after_insert` on `BWH Blog Comment` sends the email through the `email_account` in `Mailing Settings`. |

### Out of scope for v1

- A Posts page. Posts with no comments do not show.
- Approve-first moderation.
- Block an email.
- Reply as the author.
- Edit a comment body.
- Unique commenters, return commenters, commenters who are subscribers, and posts with no engagement.

## How?

### Data model

All doctypes go in a new module, `Blog`.

**BWH Blog Post**

| Field | Type | Notes |
|---|---|---|
| post_id | Data, unique | `category/slug`, for example `stories/one-year`. Also the document name. |
| title | Data | From the feed when OS makes the post |
| likes | Int, read only | One `UPDATE ... SET likes = likes + 1`, so parallel likes do not overwrite each other |

OS makes the post on its first like or comment.

**BWH Blog Comment**

The name is an autoincrement number. The blog uses it as the comment id. `creation` is the comment time.

| Field | Type | Notes |
|---|---|---|
| post | Link: BWH Blog Post | |
| commenter_name | Data | Max 60 characters |
| email | Data (Email) | Lowercased. Never shown on the blog. |
| hidden | Check | Hidden comments do not show on the blog |
| body | Text | Plain text. Max 2,000 characters. |

### API

Put the methods in `bwh_os/blog/api.py`.

Website methods. The `OS Signup API` role and System Manager can call them.

| Method | Limits | Action |
|---|---|---|
| `get_engagement(post_id)` (GET) | | Returns the likes and the first 200 visible comments, oldest first |
| `add_comment(post_id, name, email, body, ip)` (POST) | 3 in 10 minutes and 10 in a day for each IP. 500 visible comments for each post. | Makes the post if needed, inserts the comment, and returns it |
| `like_post(post_id, ip)` (POST) | 30 in an hour for each IP. 3 in a day for each IP and post. | Makes the post if needed, adds a like, and returns the total |

`bwh_os.mailing.api.subscribe` also gets limits: 5 in 10 minutes and 20 in a day for each `consent_ip`.

OS methods. Only System Manager can call them.

| Method | Action |
|---|---|
| `set_hidden(ids, hidden)` (POST) | Saves each comment, so the realtime update goes out |
| `delete_comments(ids)` (POST) | Deletes each comment |
| `get_overview()` (GET) | Comment activity (total, last 30 days against the 30 before, per week), hidden count, total likes, and the top 10 posts by comments and by likes |

### Blog repo

The functions in `bwhtech_blog/netlify/functions/` call OS through `netlify/lib/frappe.ts`:

- `engagement.ts` calls `get_engagement` and drops the email in `toPublicComment`.
- `comment.ts` checks the bot signals, validates the fields, and calls `add_comment`.
- `like.ts` calls `like_post`.
- `subscribe.ts` calls `subscribe`.

The functions need only `FRAPPE_URL` and `FRAPPE_API_TOKEN`.

### Notifications

In slice 5, `BWH Blog Comment.after_insert` sends an email if notifications are on. The email shows the post title, the name, the time, and the body. It has a "Moderate in OS" link to `/os/blog/comments?post=<post_id>`. `Mailing Settings` gets a toggle and a recipient email for blog notifications.

### OS pages

The sidebar gets a **Blog** section.

**Comments** (`/blog/comments`)

The layout follows the Tasks recipe in frappe-ui (`docs/components/recipes/TasksDesktop.vue`):

- One group for each post, ordered by the newest comment. The group header shows the post title, `12 comments · 3 hidden · 48 likes`, and Collapse or Expand on hover. A link icon opens the post on bwh.tech.
- A group starts open if it has a comment from the last 7 days, or if the `post` query parameter names it. Other groups start closed.
- Each group is a `List` from `frappe-ui/list` in feed mode.
- Each row shows an `Avatar` with initials, the name, the email, the time, and the body clamped to 3 lines with "Show more". Render the body as text. Never use `v-html`. A hidden comment is dimmed and has a `Hidden` badge.

Slice 2 adds a filter bar with `TabButtons` (All, Visible, Hidden) and search, a row menu, and selection with a bar for bulk actions. Slice 3 adds Delete with a confirmation dialog.

**Overview** (`/blog/overview`)

- Number cards: comments in the last 30 days, all comments, hidden comments, and likes.
- A bar chart of comments per week for the last 12 weeks.
- Two horizontal bar charts: the top 10 posts by comments and by likes, most first. Click a bar to open the comments of the post.
- The page reloads on `list_update`, like the Comments page.

### Local development

1. On `bwhos.localhost`, make a user with only the `OS Signup API` role and generate its API keys.
2. In `bwhtech_blog/.env`, set `FRAPPE_URL=http://bwhos.localhost:8000` and `FRAPPE_API_TOKEN=<key>:<secret>`.
3. Run `netlify dev --target-port 4321 --command "astro dev logs --follow"`.
4. Post a comment on a local post. See the comment in OS.

## Slices

Each slice goes through all layers. Merge each slice alone.

### 1. Store likes and comments in OS

- Add the `Blog` module, `BWH Blog Post`, and `BWH Blog Comment`.
- Add the website methods with rate limits, and add rate limits to `subscribe`.
- Change the Netlify functions to call OS. Remove Turso from the blog repo.
- Add the grouped Comments page without actions. It reads the doctypes with `useList` and reloads on `list_update`.
- Demo: comment and like on a local post, see the comment and the likes in OS.

### 2. Hide and unhide

- Add `set_hidden`, the row menu, selection, and the selection bar with Hide and Unhide.
- Add the All, Visible, and Hidden tabs and search.
- Demo: hide a comment in OS, reload the post, see that the comment is gone.

### 3. Delete

- Add `delete_comments`, the Delete action, and the confirmation dialog.
- Demo: delete two comments in bulk, see that they are gone from OS and from the post.

### 4. Overview

- Add `get_overview` and the Overview page.
- Demo: open Overview, see the totals, the weekly chart, and the top posts.

### 5. New comment email

- Add the notification settings and the `after_insert` email.
- Demo: turn on notifications, post a comment on the local blog, get the email in Mailpit, click "Moderate in OS".

## Open questions

- Production Turso data: copy the existing likes and comments into OS once, before the new functions go live.
