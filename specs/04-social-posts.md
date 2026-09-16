# 04: Social Posts

Status: Draft

## Why?

BWH posts on LinkedIn and X by hand, one platform at a time. There is no place to write a post once, see how it looks on each platform, and set a time for it. Scheduled posts do not show next to the videos they promote.

The Social Posts module writes a post once, previews it per platform, and publishes it at a set time. Posts and videos share one calendar.

Postiz (`gitroomhq/postiz-app`, AGPL) is the reference for the domain model, the composer, and the platform quirks. This module takes ideas and platform facts from it, not code.

## What?

- A Social Posts page with a list and a calendar. The tabs are Upcoming, Published, and All.
- A post page (the composer). It has the channel picker, the text parts, the media, a preview per platform, and the publish bar.
- A Channels panel in Settings. It holds the app credentials of each platform and connects an account.
- A background job that publishes each post at its time.

### Decisions

| Topic | Decision |
|---|---|
| Platforms | LinkedIn personal profile first, X second. YouTube has no API for the community tab, so it is out. Module 05 owns YouTube. Discord is dropped. |
| Channels | One `Social Channel` per platform account. Tokens live in the Frappe `Token Cache`, never on the channel. One account per platform in v1. |
| App credentials | `after_migrate` makes one `Connected App` per platform. The Settings panel edits its client id and secret and shows the redirect URI to register. `Connected App` has no autoname, so code finds it by `provider_name`. |
| LinkedIn OAuth | The Frappe `Connected App` web flow, with the scopes `openid profile w_member_social`. LinkedIn gives no refresh token, so the token lasts 60 days. A daily task marks the channel Expired and sends one reminder email seven days before. |
| X OAuth | OAuth 2.0 with PKCE in `bwh_os/social/x_oauth.py`, because `Connected App` cannot do PKCE. The token still goes into `Token Cache`, so the publisher reads tokens one way. |
| Content | Plain text parts. Part 1 is the post. Parts 2 and later are the X thread or the LinkedIn first comment. Global parts apply to every target. A target can switch to its own parts. All parts sit in one `Social Post Part` table, keyed by an empty or a set `channel`. |
| Media | Frappe `File` records attached to the post, private. Up to 4 images or 1 video per part. A LinkedIn comment takes no media. Video uploads go in chunks through `upload_file`. `max_file_size` is 500 MB. |
| Validation | The server is the source of truth: `validate_post` and the strict check before Schedule or Publish. The composer shows the same rules live. X counts weighted characters, and a URL counts as 23. |
| Scheduling | A cron job every minute starts due posts, like newsletters. Set `scheduler_tick_interval` to 60 where possible. Without it, precision is 4 minutes. A Scheduled post can still change. The content locks when publishing starts. |
| Publishing | One background job per post. Each target goes Pending, Publishing, then Published or Failed. A target keeps `publish_attempted_at` and the ids of released parts. A crashed job never posts the same part twice, and a thread resumes where it stopped. |
| Partial failure | Published when every target succeeded. Failed when none did. Partial otherwise. Retry works on one target. A Failed post can go back to Draft. A Partial post is duplicated. |
| Errors | Each write call to a platform is an `Integration Request`. Failures also go to Error Log with the post as reference. Errors are classed as Reconnect, Bad Request, Retryable, or Unconfirmed. |
| Calendar | The frappe-ui experimental `Calendar` on the Social Posts page, in edit mode. It shows posts and `BWH Video.publish_on`. A drag changes `scheduled_at` of a Draft or Scheduled post. A cell click makes a Draft for that day. |
| Statuses | Post: Draft, Scheduled, Publishing, Published, Partial, Failed. Target: Pending, Publishing, Published, Failed. Channel: Connected, Expired, Disconnected. |
| Local OAuth | LinkedIn and X reject `bwhos.localhost` as a redirect host. Set `host_name` to `http://localhost:8000` in `site_config.json` and open `http://localhost:8000/os`, or use a tunnel. |
| frappe-ui | Upgrade to `1.0.0-beta.71` before this module. |
| Not reused | `Social Login Key` only logs a user in and never stores an API token. `Kanban Board` is Desk only. `Scheduled Job Type` runs relative to its last run, not at a set time. |

### Out of scope for v1

- Preferred posting slots and "next free slot".
- Analytics and metrics sync.
- Auto-repost, RSS auto-post, AI thread splitting, short links.
- More than one account per platform.
- The X Premium character limit.
- Deleting a remote post.
- YouTube uploads (module 05).

## How?

### Data model

All doctypes are in the `Social` module. All need System Manager.

**Social Channel**

Autoname `format:{provider}-{account_id}`, so a reconnect updates the same row.

| Field | Type | Notes |
|---|---|---|
| provider | Select | LinkedIn, X |
| account_id | Data, read only | LinkedIn `userinfo.sub`, X `users/me.id` |
| display_name | Data | |
| handle | Data | X username. Empty for LinkedIn. |
| avatar_url | Data (URL) | |
| profile_url | Data (URL) | |
| user | Link to User | The user whose `Token Cache` holds the token |
| connected_app | Link to Connected App | |
| token_cache | Link to Token Cache, read only | `{connected_app}-{user}` |
| status | Select | Connected, Expired, Disconnected |
| connected_on | Datetime | |
| expires_on | Datetime | `Token Cache.modified` plus `expires_in` |
| last_error | Small Text | |
| reminder_sent_on | Date | One email per expiry window |

**Social Post**

Autoincrement name.

| Field | Type | Notes |
|---|---|---|
| title | Data | The first 60 characters of global part 1 when empty |
| status | Select | Draft, Scheduled, Publishing, Published, Partial, Failed |
| scheduled_at | Datetime | |
| published_at | Datetime | |
| video | Link to BWH Video | Optional |
| targets | Table of Social Post Target | |
| parts | Table of Social Post Part | |

**Social Post Target** (child)

| Field | Type | Notes |
|---|---|---|
| channel | Link to Social Channel | Unique per post |
| provider | Data, fetched from channel | |
| use_custom_content | Check | The target reads parts with `channel` set to this channel |
| settings | JSON | X: `{"reply_settings": "everyone"}`. LinkedIn: `{}`. |
| status | Select | Pending, Publishing, Published, Failed |
| publish_attempted_at | Datetime | The arm flag |
| released_parts | JSON | `[{"part_no": 1, "id": "...", "url": "..."}]`, written after each part |
| release_id | Data | The id of part 1 |
| release_url | Data (URL) | |
| published_at | Datetime | |
| error | Small Text | |
| error_kind | Select | Empty, Reconnect, Bad Request, Retryable, Unconfirmed |

**Social Post Part** (child)

| Field | Type | Notes |
|---|---|---|
| channel | Link to Social Channel | Empty means global content |
| part_no | Int | From 1 inside its group. Do not use `idx`. |
| text | Long Text | LinkedIn allows 3000 characters |
| media | JSON | `[{"file_url": "/private/files/a.png", "kind": "image"}]` |

Child tables cannot nest. One part table with a `channel` key keeps text in real columns, lets one `PartEditor.vue` bind to the global group or a channel group, and lets the server pick content with one expression: the parts of the channel, or else the global parts. `validate` removes custom rows whose target is gone or has `use_custom_content` off, and renumbers `part_no`.

### Provider layer

Files in `bwh_os/social/providers/`.

`base.py` holds the errors `ReconnectRequired`, `BadRequest`, and `Retryable`, the dataclasses `Media`, `Part`, and `Release`, and the `Provider` class:

| Method | Use |
|---|---|
| `identity(token_cache)` | Account id, name, handle, avatar, profile URL |
| `count(text)` | Length rule of the platform |
| `validate(parts, settings)` | A list of error strings |
| `upload_media(media, post_name)` | Returns the platform media id |
| `post(parts, settings, released, on_release)` | Posts each part not in `released`, calls `on_release` after each |
| `request(method, url, *, post_name, **kwargs)` | HTTP with a 60 s timeout, the auth header from `Token Cache`, an `Integration Request` per write call, and errors mapped to the three classes |

`linkedin.py`

- Limit 3000. Up to 20 images. Video up to 200 MB.
- Identity: `GET https://api.linkedin.com/v2/userinfo`.
- Part 1: `POST https://api.linkedin.com/rest/posts` with the headers `LinkedIn-Version: 202601` and `X-Restli-Protocol-Version: 2.0.0`. The body is `author`, `commentary`, `visibility PUBLIC`, `distribution MAIN_FEED`, `lifecycleState PUBLISHED`, and `content.media` or `content.multiImage`. The post id comes from the `x-restli-id` response header.
- Escape `\ < > # ~ _ | [ ] * ( ) { } @` in `commentary`.
- Parts 2 and later: `POST /rest/socialActions/{urn}/comments`, text only.
- Image: `POST /rest/images?action=initializeUpload`, then one PUT of the whole file. A personal token cannot read image status, so wait 20 s before the post.
- Video: `initializeUpload` with `fileSizeBytes`, PUT each range from `uploadInstructions` and keep the ETag, `finalizeUpload` with the ETags, then poll `GET /rest/videos/{urn}` until `AVAILABLE`, up to 5 minutes.

`x.py`

- Limit 280 weighted. Up to 4 images. Video up to 512 MB.
- Identity: `GET https://api.x.com/2/users/me?user.fields=profile_image_url,username,name`.
- Each part: `POST https://api.x.com/2/tweets` with `text`, `media.media_ids`, `reply_settings`, and `reply.in_reply_to_tweet_id` for parts 2 and later.
- Media: `POST /2/media/upload/initialize`, `POST /2/media/upload/{id}/append` in 1 MB chunks, `POST /2/media/upload/{id}/finalize`, then poll `GET /2/media/upload?command=STATUS` while `processing_info` is present.
- A duplicate text returns 403 and becomes `BadRequest`.

`x_text.py` counts weighted characters: NFC normalize, weight 1 for code points in 0 to 4351, 8192 to 8205, 8208 to 8223, and 8242 to 8247, weight 2 for the rest, 23 for each URL, then divide by 2. `frontend/src/lib/xText.ts` mirrors it. Both use the same test fixtures.

`__init__.py` holds `PROVIDERS` and `get_provider(channel)`.

`bwh_os/social/validation.py` holds `PostValidator`. `SocialPost.validate` runs the structure pass: unique targets, contiguous `part_no`, no orphan custom rows, valid media JSON, at least one target. Schedule, Publish, and `validate_post` run the strict pass: part 1 not empty, length per platform, media count and kind per platform, channel Connected.

### OAuth

`bwh_os/social/oauth_apps.py` has `ensure_connected_apps()`, called from `after_migrate`. It makes one `Connected App` per platform when none exists with that `provider_name`.

| | LinkedIn | X |
|---|---|---|
| authorization_uri | `https://www.linkedin.com/oauth/v2/authorization` | `https://x.com/i/oauth2/authorize` |
| token_uri | `https://www.linkedin.com/oauth/v2/accessToken` | `https://api.x.com/2/oauth2/token` |
| scopes | `openid`, `profile`, `w_member_social` | `tweet.read`, `tweet.write`, `users.read`, `offline.access` |
| redirect | Set by `ConnectedApp.validate` to `/api/method/frappe.integrations.doctype.connected_app.connected_app.callback/<name>` | `/api/method/bwh_os.social.x_oauth.callback` |

LinkedIn:

1. `connect_channel("LinkedIn")` calls `initiate_web_application_flow(user, success_uri="/api/method/bwh_os.social.oauth.linkedin_connected")` and returns the URL.
2. The Frappe callback stores the token in `Token Cache`.
3. `linkedin_connected` reads `userinfo`, upserts the `Social Channel`, and redirects to `/os/social?connected=LinkedIn`.
4. `tokens.get_token(channel)` calls `get_active_token(user)`. `None` raises `ReconnectRequired` and marks the channel Expired.
5. `channels.check_expiry` runs daily. It marks expired channels and sends one reminder when fewer than seven days remain.

X:

1. `x_oauth.start()` makes a verifier, a challenge, and a state. It stores the verifier and the user in `frappe.cache` for 600 s and returns the authorize URL.
2. `x_oauth.callback(code, state)` pops the cache entry, checks the user, exchanges the code with `code_verifier` and HTTP Basic auth, upserts `Token Cache` with `update_data`, reads the identity, upserts the channel, and redirects.
3. `x_oauth.refresh(token_cache)` runs under a file lock when fewer than 120 s remain. X rotates the refresh token.

### Publishing

`bwh_os/social/publisher.py`.

`Publisher(post)`:

| Method | Use |
|---|---|
| `check()` | The strict validation and the channel status |
| `start()` | Draft or Scheduled to Publishing, targets to Pending, then enqueue |
| `enqueue()` | `frappe.enqueue` on the `long` queue, timeout 30 minutes, `job_id social_post::{name}`, `deduplicate`, `enqueue_after_commit` |
| `run()` | Each target inside a savepoint, then `finish()` |
| `publish_target(target)` | The arm flag, media upload, `provider.post`, status |
| `retry_target(target)` | Clears the attempt and the error, keeps `released_parts`, enqueues |
| `finish()` | Post status, a timeline comment, `db_set(notify=True)` |

`Schedule(post)` mirrors `NewsletterSchedule`: `schedule(at)`, `reschedule(at)` for Draft or Scheduled only, `unschedule()`.

`publish_due_posts` runs every minute. It selects Scheduled posts with `scheduled_at` in the past, sets Publishing in the same transaction, enqueues, and commits per post. `resume_stuck_posts` runs every 5 minutes. It enqueues Publishing posts older than 30 minutes with no job in the queue.

The arm flag: when `publish_attempted_at` is set and `released_parts` is empty, the target becomes Failed with `error_kind Unconfirmed` and no call is made. Otherwise the job sets the flag, commits, and starts work. `on_release` appends to `released_parts` and commits after each part. The provider skips parts already released.

Errors: `ReconnectRequired` marks the channel Expired and the target `Failed / Reconnect`. `BadRequest` gives `Failed / Bad Request`. All else gives `Failed / Retryable` and an Error Log entry.

Video upload from the browser: `frontend/src/lib/chunkedUpload.ts` posts 5 MB chunks in order to `/api/method/upload_file` with `chunk_index`, `total_chunk_count`, `chunk_byte_offset`, and `total_file_size`. The last chunk returns the `File`. Production also needs a larger proxy body limit.

### API

All methods are in `bwh_os/social/api.py` and need System Manager.

| Method | Use |
|---|---|
| `get_channels()` | Channels with days until expiry |
| `get_provider_apps()` | Connected App names, redirect URIs, and whether credentials are set |
| `connect_channel(provider)` | The authorization URL |
| `disconnect_channel(channel)` | Deletes the `Token Cache` and sets Disconnected |
| `validate_post(post)` | Per-target result for an unsaved draft |
| `publish_post(post)` | Publish now |
| `schedule_post(post, scheduled_at)` | |
| `reschedule_post(post, scheduled_at)` | The calendar drag |
| `unschedule_post(post)` | |
| `retry_target(post, target)` | |
| `unlock_post(post)` | Failed to Draft |
| `duplicate_post(post)` | A new Draft with the same parts and targets |

Other reads and writes use the document API through `useList` and `useDoc`.

Scheduler entries in `hooks.py`: `publish_due_posts` under `* * * * *`, `resume_stuck_posts` under `*/5 * * * *`, `check_expiry` under `daily`.

### Routes

| Route | Page |
|---|---|
| `/social` | List and calendar, with `?view=calendar` |
| `/social/:postId` | The composer |

The sidebar gets a Social section with one item, Posts. New Post inserts a Draft with every Connected channel as a target and opens it, so attachments have a document from the start.

### Frontend

Components in `frontend/src/components/social/`:

| Component | Use |
|---|---|
| `SocialPostTable.vue` | Title, channel avatars with a status dot, status badge, time, video link |
| `ChannelPicker.vue` | Avatar toggles. Expired channels are disabled. |
| `ContentTabs.vue` | All channels plus one tab per target, with a Customize switch |
| `PartEditor.vue` | A textarea per part, a live counter against the strictest platform, media, add and remove |
| `MediaPicker.vue` | `FileUploader` for images, `chunkedUpload` for video |
| `TargetSettings.vue` | X reply settings |
| `LinkedInPreview.vue`, `XPreview.vue` | The card per platform, overflow past the limit in a red mark, the thread as stacked cards, server validation errors |
| `PublishBar.vue` | Autosave state, `DateTimePicker`, actions by status |
| `TargetResults.vue` | One row per target with the link, the error, and Retry |
| `SocialCalendar.vue` | The frappe-ui experimental `Calendar` |

The calendar: `config` is Month by default, `isEditMode` on, Day mode off. `rangeChange` drives `useList` on Social Post for `scheduled_at` and `published_at` and on BWH Video for `publish_on`. A post event has `isDraft` when Draft or Scheduled. `update` calls `reschedule_post` or sets `publish_on` on the video. A click opens the post or the video. A cell click inserts a Draft for that date.

Settings: `components/settings/SocialChannelsSettings.vue` under a Social group in `AppSettingsDialog.vue`. Per platform it shows the credentials form, the redirect URI with a copy button, and the channel card with Connect, Reconnect, and Disconnect.

## Slices

Each slice crosses doctype, API, and UI, and ends in a demo.

### Phase 0: frappe-ui 1.0.0-beta.64 to 1.0.0-beta.71

1. Run `yarn add frappe-ui@1.0.0-beta.71` in `frontend`.
2. Run the codemods in `node_modules/frappe-ui/scripts/`.
3. Keep `lucideIcons: true` in `vite.config.ts`. The default is now false.
4. Check the error class export used in `lib/errors.ts`.
5. Fix the charts API in `components/stats/ActivityCards.vue`, `pages/DashboardPage.vue`, `pages/BlogOverviewPage.vue`, the newsletter report, and `components/videos/SeriesStats.vue`.
6. Run `yarn typecheck` and `yarn build`, then open every page.

Demo: the app looks the same, and typecheck is clean.

### Phase 1: Channels and LinkedIn connect

| Slice | Work | Demo |
|---|---|---|
| 1.1 | The Social module, `Social Channel`, `ensure_connected_apps`, `get_channels`, `get_provider_apps`, the Settings panel, the sidebar section, a placeholder page | Settings shows LinkedIn and X cards with the redirect URI. Save the client id and secret. |
| 1.2 | `oauth.py`, `tokens.py`, `providers/base.py`, `providers/linkedin.py` identity, `connect_channel`, `disconnect_channel`, the `?connected=` toast | Connect, consent, return with a toast. The card shows the avatar and 60 days. |
| 1.3 | `channels.check_expiry`, the daily hook | Set `expires_on` in the past, run the task, the card turns red. |

### Phase 2: Posts, composer, LinkedIn publishing

| Slice | Work | Demo |
|---|---|---|
| 2.1 | The three post doctypes, `validation.py`, `validate_post`, the list page, the composer with text only, the LinkedIn preview | New Post, type, the counter and the preview update, autosave, Draft in Upcoming. |
| 2.2 | `publisher.py`, LinkedIn post, `publish_post`, `TargetResults.vue`, lock rules | Publish now. The post is on LinkedIn, OS shows the link, an `Integration Request` exists. |
| 2.3 | `Schedule`, `publish_due_posts`, the cron hook, `PublishBar`, `scheduler_tick_interval` | Schedule 3 minutes ahead. It posts alone and the list updates live. |
| 2.4 | LinkedIn comments, `released_parts`, `on_release`, "Add first comment" | A two-part post makes a post and a comment. A retry after a crash posts only the comment. |
| 2.5 | `MediaPicker.vue`, LinkedIn image upload, `multiImage`, media validation | A post with two images. |
| 2.6 | The Customize switch, orphan cleanup, `parts_for(target)` | A custom LinkedIn text publishes. A test covers two channels. |
| 2.7 | `retry_target`, `unlock_post`, the Reconnect badge | Revoke the token, publish, see Failed / Reconnect, reconnect, retry, Published. |

### Phase 3: Video and calendar

| Slice | Work | Demo |
|---|---|---|
| 3.1 | `chunkedUpload.ts`, video progress, LinkedIn video upload, `max_file_size` | A 60 MB mp4 uploads with progress and posts. |
| 3.2 | `SocialCalendar.vue`, the view switch, event mapping, `reschedule_post`, the video picker | Month view shows dashed posts and video bars. Drag a post to tomorrow. Click a day to get a prefilled composer. |

### Phase 4: X

| Slice | Work | Demo |
|---|---|---|
| 4.1 | `x_oauth.py`, X identity, the refresh path, Connect X | The card shows the handle. The token refreshes after 2 hours. |
| 4.2 | `x_text.py`, `xText.ts`, `XPreview.vue`, `TargetSettings.vue`, tweets and threads | A three-tweet thread with "following" reply settings. |
| 4.3 | X media | A tweet with an image, then one with a video. |
| 4.4 | Multi-channel and Partial | LinkedIn and X in one post. A duplicate tweet fails, the post is Partial, Duplicate and publish to X only. |

### Phase 5: Later

Posting slots and "next slot", repost with an offset, metrics sync with charts, a draft post when a `BWH Video` becomes Published, delete a remote post, the X Premium limit.

## Tests

Run `bench --site bwhos.localhost run-tests --app bwh_os --module bwh_os.social.test_social`. The file has `make_channel` and `make_post` factories. It patches `frappe.enqueue`, `Provider.request`, and `tokens.get_token`.

| Phase | Tests |
|---|---|
| 1 | `ensure_connected_apps` is idempotent. `linkedin_connected` upserts the channel. `check_expiry` marks Expired and emails once. The API needs System Manager. |
| 2 | The title comes from part 1. Validation rejects a long text and a missing target. Custom rows go when Customize is off. `parts_for` prefers custom rows. Publish now enqueues once. Due posts enqueue once. One failed target gives Partial. An unconfirmed attempt does not post again. A thread resumes from `released_parts`. A reconnect error marks the channel. A published post is locked. |
| 3 | Reschedule works only for Draft or Scheduled. A video part rejects a second file. |
| 4 | The weighted count fixtures in Python and TypeScript. The callback rejects a bad state. A refresh rotates the token. Thread replies chain ids. |

Browser checks use the `agent-browser` skill: the list, the composer, and the calendar, with no console errors.
