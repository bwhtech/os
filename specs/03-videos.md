# 03: Videos

Status: Built

## Why?

BWH plans YouTube videos in many places. A monthly Frappe Framework series and courses have 10 to 12 videos in a fixed order. There is no single place for the idea, the research, the script, and the files of a video.

The Videos module keeps each video from idea to publish. A video can be a one-off video or part of a series.

## What?

- A Videos page with a board and a list. The tabs are In Progress, Published, and All. In Progress is the default.
- A video page with Research, Script, and Description editors, details, and attachments.
- A Series page with a card for each series.
- A series view. When you open a series, the sidebar changes to the sidebar of that series. It shows the videos in order, and you can drag them to reorder.

A mockup of this module is at https://sketch.netchamp.dev/u/nagariahussain/bwh-os-videos.

### Decisions

| Topic | Decision |
|---|---|
| Statuses | A fixed Select: Idea, Researching, Scripting, Recording, Editing, Thumbnail Pending, Published. A new video is an Idea. The README planned a `Video Stage` doctype. A Select is enough for one person. |
| Series type | There is no type. A course and a monthly series are both a series. |
| Lanes | There are no lanes in v1. |
| Order | `position` on `BWH Video`, from 1, with no gaps. The server sets it. A video that joins a series goes to the end. A video that leaves a series or is deleted closes the gap. |
| Attachments | Frappe `File` records attached to the video. Uploads are private. A link is a `File` with an external URL. Images pasted into an editor are attached to the video too. |
| Editors | frappe-ui `Editor` with `RichTextKit`. The editors and the title save 800 ms after you stop typing. |
| Board | A copy of the bwh_hive board: pointer drag with a preview, Cmd/Ctrl-click to select many cards, edge scroll, and a board that fills the screen. The columns follow the tab, so In Progress has no Published column. |
| Sidebar | A route with a `seriesId` shows `SeriesSidebar` in `AppShell`. The main sidebar has All Videos and Series. It does not list each series. |
| Updates | Pages join the `list_update` room of `BWH Video` and `BWH Video Series`, and reload when one changes. |
| Typecheck | React Email and frappe-ui/editor declare the same Tiptap commands with different types. The React Email editor is a separate typecheck project, `tsconfig.email.json`. The Vue app sees it through `email-editor/api.ts`. |

### Out of scope for v1

- A calendar view.
- Lanes.
- Editable statuses.
- YouTube sync.
- The series sidebar on mobile. On mobile, the Series page lists the videos.

## How?

### Data model

All doctypes are in the `Videos` module.

**BWH Video Series**

| Field | Type | Notes |
|---|---|---|
| title | Data | |
| emoji | Data | Default 🎬 |
| summary | Small Text | |
| notes | Text Editor | Format, cadence, and repo |

**BWH Video**

| Field | Type | Notes |
|---|---|---|
| title | Data | |
| status | Select | Default Idea |
| series | Link to BWH Video Series | Empty for a one-off video |
| position | Int, read only | Set by `SeriesOrder` in `bwh_os/videos/series_order.py` |
| publish_on | Date | |
| youtube_url | Data (URL) | |
| research, script, description | Text Editor | |

Both doctypes use autoincrement names. A save turns the `series` Link into an int, and the copy from the database holds a str. `BWHVideo.series_changed` compares them as text.

### API

All methods are in `bwh_os/videos/api.py` and need System Manager.

| Method | Use |
|---|---|
| `get_series` | Every series with `video_count` and `published_count` |
| `get_attachment_counts` | File and link counts by video, for the board cards |
| `move_video(video, position)` | Put a video at a position in its series |

Other reads and writes use the document API through `useList` and `useDoc`.

### Routes

| Route | Page |
|---|---|
| `/videos` | Board and list |
| `/videos/:videoId` | A one-off video |
| `/series` | Series cards |
| `/series/:seriesId` | Series overview, with the series sidebar |
| `/series/:seriesId/videos/:videoId` | A video in a series, with the series sidebar |

When a video joins or leaves a series, the video page replaces its URL.
