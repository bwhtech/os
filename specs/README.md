# BWH OS

BWH OS is the control panel for BWH. It is a frappe-ui app at `/os` inside the `bwh_os` Frappe app.

## Why?

BWH runs a YouTube channel, cohorts on school.bwh.tech, open-source products, and client work. The data for these lives in many tools. There is no email list, no single view of the content pipeline, and no fast way to do bulk actions on YouTube.

BWH OS puts this work in one place. BWH owns the data. One person (Hussain) uses it. There are no teams, assignees, or approval flows.

## Principles

- Use frappe-ui components for all UI: lists, dialogs, calendar, editor, and charts. Write custom UI only when frappe-ui has no component, and build it from frappe-ui parts.
- Frappe doctypes are the source of truth. Integrations pull data into doctypes. A page never waits on a live third-party call to render.
- Only users with the System Manager role can open `/os`.
- Each module is one section in the sidebar.
- Each spec splits work into tracer-bullet slices. A slice goes through all layers (doctype, API, UI) and you can demo it alone.

## Shell

The frontend copies the wiring from `apps/bwh_hive`:

| Part | Source in bwh_hive | Change for bwh_os |
|---|---|---|
| Vite config | `frontend/vite.config.ts` | `frontendRoute: '/os'`, build into `bwh_os/public/frontend` and `bwh_os/www/os.html`, proxy port 8000 |
| Router | `frontend/src/router.ts` | `createWebHistory('/os')` |
| Boot context | `bwh_hive/www/hive.py` | `bwh_os/www/os.py` |
| Route rule | `website_route_rules` in `hooks.py` | `/os/<path:app_path>` to `os` |
| Ignored build output | `.gitignore` | `bwh_os/public/frontend/`, `bwh_os/www/os.html` |

The layout uses the frappe-ui `Sidebar` in a `DesktopShell`. A `CommandPalette` comes later.

The dev site is `bwhos.localhost`. Production runs on a Frappe Cloud bench. The site is not decided yet, so specs do not depend on a domain.

## Modules

### 1. Email List

Collect subscribers from bwh.tech, deliver lead magnets, and write and send newsletters. See [01-email-list.md](01-email-list.md).

### 2. Blog

Store the likes and comments of bwh.tech/blog, moderate comments, see stats, and get an email for new comments. See [02-blog.md](02-blog.md).

### 3. Videos

Track each video from idea to publish, alone or in an ordered series. Write the research, script, and description, and attach files. See [03-videos.md](03-videos.md).

### 4. Social Posts

Write a post once, preview it per platform, and publish it to LinkedIn and X at a set time. Posts and videos share one calendar. See [04-social-posts.md](04-social-posts.md).

### 5. YouTube Integration

Connect the channel with OAuth and sync videos into `YouTube Video`. Do bulk actions that YouTube Studio does not have:

- Find and replace text in descriptions, for example the 92 dead bwh.live links.
- Add or update a call to action, for example the email list link, on many videos at once.
- Show videos with missing chapters, playlists, or end screens.

### 6. LMS Integration

Read data from school.bwh.tech: live cohorts, seats sold against capacity, and revenue per batch.

### 7. GitHub Integration

Show the health of the core products (buzz, commera): stars, open issues, open pull requests, and releases.

## Specs

| # | Spec | Status |
|---|---|---|
| 01 | [Email List](01-email-list.md) | Draft |
| 02 | [Blog](02-blog.md) | Draft |
| 03 | Content Pipeline | Not started |
| 04 | [Social Posts](04-social-posts.md) | Draft |
| 05 | YouTube Integration | Not started |
| 06 | LMS Integration | Not started |
| 07 | GitHub Integration | Not started |
