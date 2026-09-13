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

### 2. Content Pipeline

Track each video from idea to publish.

- `Video`: title, lane (A: Frappe, B: open source for business), series, stage, target date, publish date, notes.
- `Video Stage`: name and order. You can edit the stages from day one.
- `Video Series`: groups videos, for example "Frappe Framework: Zero to Hero".

The board is a Kanban with one column per stage. frappe-ui has no Kanban component. Build it like the bwh_hive board (`frontend/src/composables/useBoardDrag.ts`) with frappe-ui `Badge` and `ScrollArea`. The calendar view uses `Calendar` from `frappe-ui/experimental`.

### 3. Social Posts

Plan posts for X, LinkedIn, the YouTube community tab, and Discord.

- `Social Post`: platform, text, media, status, scheduled date, and an optional link to a `Video`.

Posts show on the same calendar as videos.

### 4. YouTube Integration

Connect the channel with OAuth and sync videos into `YouTube Video`. Do bulk actions that YouTube Studio does not have:

- Find and replace text in descriptions, for example the 92 dead bwh.live links.
- Add or update a call to action, for example the email list link, on many videos at once.
- Show videos with missing chapters, playlists, or end screens.

### 5. LMS Integration

Read data from school.bwh.tech: live cohorts, seats sold against capacity, and revenue per batch.

### 6. GitHub Integration

Show the health of the core products (buzz, commera): stars, open issues, open pull requests, and releases.

## Specs

| # | Spec | Status |
|---|---|---|
| 01 | [Email List](01-email-list.md) | Draft |
| 02 | Content Pipeline | Not started |
| 03 | Social Posts | Not started |
| 04 | YouTube Integration | Not started |
| 05 | LMS Integration | Not started |
| 06 | GitHub Integration | Not started |
