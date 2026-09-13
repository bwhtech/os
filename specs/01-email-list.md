# 01: Email List

Status: Draft

## Why?

BWH has 10.6k YouTube subscribers, 279 LMS users, and 460 Discord members, but no email list. The content monetisation plan (section 3.6) sets a target of 3,000 subscribers in 90 days. Every published dev-education income story in that plan sells to an owned email list.

Kit did not fit. BWH wants its own list with no third-party tool for now.

## What?

- Signup forms that bwh.tech and other sites can use.
- A lead magnet (for example the Missing Frappe Manual PDF) that goes out when a person signs up.
- Single or double opt-in, set on each form.
- One subscriber list with tags. One global unsubscribe.
- CSV import of existing contacts (LMS users, cohort alumni, Discord).
- Newsletters: a block editor, preview, test send, schedule, open and click tracking, and a public web archive.

### Decisions

| Topic | Decision |
|---|---|
| Sending | Frappe Email Queue through a Frappe Email Account on a subdomain of bwh.tech. The provider (SES, Postmark, or other) is decided later. |
| Local email | Mailpit in Docker. The dev Email Account uses its SMTP port, and you read the emails in the Mailpit web UI. |
| Send rate | Each `Newsletter Issue` has an hourly limit. The default comes from `Mailing Settings`. |
| URLs | Build all public links with `frappe.utils.get_url`. Do not hardcode a domain. |
| Opt-in | Each `Signup Form` has a double opt-in checkbox. |
| Signup path | Astro form, then a Netlify function, then the Frappe API. The Frappe API key never goes to the browser. |
| Forms | A `Signup Form` record with an id. The Astro component takes the id. There is no drag-and-drop form builder. |
| Incentive | An email with a download link that has a token. The link serves a private file. Each download is logged. |
| Segments | One list with tags. Unsubscribe removes the person from all sends. |
| Import | CSV rows import as Active, with tags. |
| Editor | An `EmailEditor.vue` wrapper around `@react-email/editor`. The spike in slice 7 passed. See [Editor](#editor). |

### Out of scope for v1

- Drip or automation sequences.
- Bounce and complaint processing. This needs a webhook from the email provider.
- Captcha (for example Cloudflare Turnstile). The Netlify function already has a honeypot and a rate limit.
- Live sync of new LMS users.
- Segments based on opens or clicks.
- More than one list.

## How?

### Data model

All doctypes go in a new module, `Mailing`.

**Mailing Settings** (single doctype)

| Field | Type | Notes |
|---|---|---|
| email_account | Link: Email Account | Sends all list email |
| default_hourly_limit | Int | Default 500. New issues copy this value. |
| company_name | Data | BWH Technologies LLP |
| gstin | Data | |
| postal_address | Small Text | Shown in the email footer |

**Subscriber**

| Field | Type | Notes |
|---|---|---|
| email | Data (Email), unique | Also the document name |
| first_name | Data | |
| status | Select | Pending, Active, Unsubscribed, Bounced |
| tags | Table MultiSelect | Rows of `Subscriber Tag Item`, a child table that links to `Subscriber Tag` |
| source_form | Link: Signup Form | The first form the person used. Empty for manual add and import. |
| source_url | Small Text | The page where the person signed up. Data is too short for long URLs. |
| utm | JSON | UTM parameters and referrer |
| consent_ip | Data | |
| subscribed_on | Datetime | |
| confirmed_on | Datetime | |
| unsubscribed_on | Datetime | |
| token | Data, hidden | Random value for confirm, unsubscribe, and download links |

**Subscriber Tag**: name only.

**Signup Form**

| Field | Type | Notes |
|---|---|---|
| title | Data | |
| form_id | Data, unique | Slug that the Astro component uses |
| is_active | Check | |
| collect_name | Check | Adds `collectName` to the embed snippet. The site does not read this field. |
| double_opt_in | Check | |
| tags | Table MultiSelect | Tags to add on signup |
| lead_magnet | Link: Lead Magnet | Optional |
| success_message | Small Text | Shown on the site after submit |
| confirm_subject, confirm_body | Data, Text Editor | Used when double opt-in is on |
| welcome_subject, welcome_body | Data, Text Editor | Sent when the subscriber becomes Active |

The form page in OS also shows the signup count, the confirm rate, and the embed snippet.

**Lead Magnet**: title, description, file (private Attach).

**Lead Magnet Download**: lead_magnet, subscriber, downloaded_on. The lead magnet page lists the last 100 downloads with the subscriber.

**Newsletter Issue**

| Field | Type | Notes |
|---|---|---|
| subject | Data | |
| preview_text | Data | |
| content_json | JSON | Editor document |
| content_html | Code (HTML) | Email-safe HTML. The editor makes it in the browser and OS saves it with `content_json`. Code, because Frappe sanitizes Long Text and removes `<html>`, `<head>`, and `<body>`. |
| theme | Select | Frappe UI (default), Basic, Minimal. Frappe UI uses the frappe-ui light tokens as hex colors. |
| audience | Select | All Active, Tags |
| tags | Table MultiSelect | Used when audience is Tags |
| status | Select | Draft, Scheduled, Sending, Sent, Failed |
| scheduled_at | Datetime | |
| hourly_limit | Int | Max emails per hour for this issue. Copied from `Mailing Settings` on create. |
| sent_at | Datetime | |
| recipient_count | Int | |
| is_public | Check | Show in the web archive |
| route | Data | Slug for the web archive |

The name `Newsletter Issue` prevents a clash with the separate Frappe `newsletter` app.

**Newsletter Event**: issue, subscriber, type (Open, Click), url, timestamp.

### API

Put the methods in `bwh_os/mailing/api.py`.

`subscribe(form_id, email, first_name=None, source_url=None, utm=None, consent_ip=None)`

- The Netlify function calls this method with the API key of a restricted user. That user has only the role `OS Signup API`.
- There is no Frappe `@rate_limit`. All calls come from Netlify, so a per-IP limit in Frappe would block every reader at once. The Netlify function limits by reader IP.
- `after_migrate` creates the `OS Signup API` role. It has no desk access.
- If the form has double opt-in, the method makes the subscriber Pending and sends the confirm email.
- If the form has single opt-in, the method makes the subscriber Active and sends the welcome email.
- If the email already exists, the method adds the form tags and keeps the first `source_form`. It does not send a second welcome email.
- A signup makes an Unsubscribed person Active again, because the signup is new consent. A Bounced person stays Bounced.
- A closed form raises `FormClosedError`. The site shows "This signup is closed right now."
- The method returns `{"message": <success message>}` for a new and a known email alike.

### Public endpoints

These endpoints allow guests. Each one checks the subscriber token.

| Endpoint | Action |
|---|---|
| Confirm | Makes a Pending subscriber Active, sends the welcome email, and shows a page |
| Unsubscribe (GET) | Shows a page with an unsubscribe button |
| Unsubscribe (POST) | One-click unsubscribe (RFC 8058). The `List-Unsubscribe` header points here. |
| Download | Logs a `Lead Magnet Download` and streams the private file |
| Open pixel | Logs an Open event and returns a 1x1 GIF |
| Click redirect | Logs a Click event and redirects. The target URL is signed, so the endpoint is not an open redirect. |
| `/newsletter` | Lists public sent issues |
| `/newsletter/<route>` | Shows one public issue |

### Sending

- Send each email with `frappe.sendmail`, one recipient per call, with `reference_doctype` and `reference_name`.
- Frappe v16 `sendmail` has the parameters we need:
  - `send_after` paces the send.
  - `unsubscribe_method` and `unsubscribe_params` point the unsubscribe link at our endpoint.
  - `email_headers` adds `List-Unsubscribe` and `List-Unsubscribe-Post`. Frappe does not add these headers itself, and it puts `X-` before custom header names. A `make_email_body_message` hook removes the `X-`.
  - `email_read_tracker_url` can carry the open pixel. Check in slice 10 if it fits, else add our own pixel.
- A background job queues the emails for an issue in hourly batches. Batch N gets `send_after = start + N hours`, and each batch has at most `hourly_limit` emails.
- The Email Queue flush also has a site-wide batch size (`email_queue_batch_size`, default 500 per run).
- Build every public link (confirm, unsubscribe, download, pixel, click, archive) with `frappe.utils.get_url`.
- Every email has an unsubscribe link and a footer with the company name, GSTIN, and postal address from `Mailing Settings`.

### Local development

1. Start Mailpit in Docker (SMTP on port 1025, web UI on port 8025).
2. Make an Email Account on `bwhos.localhost` that sends through `localhost:1025` with no auth and no TLS.
3. Set that Email Account in `Mailing Settings`.
4. Open `http://localhost:8025` to read every email that OS sends.

### Astro site

The branch `feat/newsletter-signup` in `/Users/mdhussain/bwh/bwhtech_blog` already has the parts to reuse:

- `netlify/functions/subscribe.ts` checks the email, the honeypot, and the Turso rate limit.
- `src/components/islands/NewsletterForm.vue` is already on the post layout, the home page, and `train-your-team.astro`.

Changes:

1. Replace `netlify/lib/kit.ts` with `netlify/lib/frappe.ts`. It calls `subscribe` on the OS site.
2. Replace the `KIT_API_KEY` and `KIT_FORM_ID` env vars with `FRAPPE_URL` and `FRAPPE_API_TOKEN`.
3. Give `NewsletterForm.vue` a `formId` prop. Send the page URL and UTM values with each signup.
4. Give `NewsletterForm.vue` a `collectName` prop that shows a first name field. The OS form page shows the snippet with this prop when `collect_name` is on.
5. Show the success message that OS returns.

The Netlify CSP stays strict because the browser only calls the Netlify function.

### OS pages

| Page | frappe-ui parts | Content |
|---|---|---|
| Subscribers | `frappe-ui/list`, `Dialog`, `FormControl` | Filter by status, tag, and form. Add a subscriber. Import a CSV. |
| Forms | `frappe-ui/list`, `FormControl`, `frappe-ui/editor` | Edit a form, see counts, copy the embed snippet |
| Lead Magnets | `frappe-ui/list`, `FileUploader` | Upload the file, see download counts |
| Newsletters | `frappe-ui/list`, `EmailEditor.vue`, `DatePicker`, `TabButtons` | Write, preview, test send, schedule, see stats |
| Dashboard | `frappe-ui/charts` | Subscriber growth, signups per form, last issue stats |

### Editor

Hussain wants an editor like the [React Email editor](https://react.email/docs/editor/overview). That editor uses TipTap and ProseMirror and makes email-safe HTML. Its UI is React. BWH OS is Vue.

1. Make one wrapper, `EmailEditor.vue`. It takes the document JSON and emits the JSON and the email HTML.
2. Spike for half a day. Mount `@react-email/editor` in a shadow root inside the wrapper. Load it only on the newsletter editor route.
3. If the spike works, use it. The shadow root keeps the React Email styles and the frappe-ui styles apart.
4. If the spike fails, use `frappe-ui/editor` (also TipTap). Add email blocks (heading, paragraph, image, button, divider, code) and our own serializer to inline-styled table HTML.

Show the preview in an `iframe` with `srcdoc`, at desktop and mobile widths. Email HTML is a full document, so an iframe shows it the way an email client does.

The editor must accept custom blocks. We add these blocks after v1 (slice 13):

- **Footer**: company name, GSTIN, postal address, and social links from `Mailing Settings`.
- **YouTube video**: paste a YouTube URL. The block shows the video thumbnail (`https://img.youtube.com/vi/<id>/maxresdefault.jpg`) with a play button and the title. The whole block links to the video on YouTube. Email clients do not play embedded video.

The spike passes only if we can add a custom block that serializes to email HTML. Test it with the YouTube block.

Spike result (slice 7): passed. A YouTube `EmailNode` with `renderToReactEmail` serialized to table HTML, and typing and slash commands work in the shadow root. Notes for later slices:

- The serializer (`composeReactEmail`) runs in the browser, so the server cannot make `content_html` from `content_json`.
- `EmailEditor` always adds the default slash commands. Custom blocks (slice 13) need our own `EditorProvider` with `SlashCommand items`.
- The editor puts some styles in `document.head` and its menus in `document.body`. The wrapper copies the node styles into the shadow root and loads the menu theme on the page.
- The code block loads Prism CSS from `/styles/prism/`, which OS does not serve. Code blocks show no syntax colors in the editor.
- The editor chunk is about 720 KB gzip. It loads only on the newsletter page.

## Slices

Each slice goes through all layers. Merge each slice alone.

### 1. Shell and manual subscriber

- Set up the frontend at `/os`. Copy the wiring from `bwh_hive` (see [README](README.md#shell)).
- Add the `Mailing` module, `Subscriber`, `Subscriber Tag`, and `Subscriber Tag Item`.
- Add the sidebar and the Subscribers page with an add dialog.
- Demo: open `/os`, add a subscriber, see the subscriber in the list.

### 2. Signup form from Astro (single opt-in)

- Add `Signup Form` and the Forms page with the embed snippet.
- Add the `subscribe` method and the `OS Signup API` role.
- On the Astro branch, replace `kit.ts` with `frappe.ts` and add the `formId` prop.
- Demo: submit the form on the local Astro site. The subscriber shows in OS with the form and source URL.

### 3. Lead magnet delivery

- Set up Mailpit and the dev Email Account (see [Local development](#local-development)).
- Add `Mailing Settings` with the Email Account and company footer fields.
- Add `Lead Magnet` and `Lead Magnet Download`.
- Send the welcome email with the download link when a subscriber becomes Active.
- Add the download endpoint and the download count on the form and lead magnet pages.
- Demo: sign up, get the email, click the link, get the PDF, see the count go up.

### 4. Double opt-in

- Use the `double_opt_in` checkbox in `subscribe`.
- Add the confirm email and the confirm endpoint and page.
- Send the lead magnet only after confirm.
- Demo: sign up on a double opt-in form. The subscriber is Pending. Click confirm. The subscriber is Active and gets the PDF.

### 5. Unsubscribe

- Add the unsubscribe link to every email and the `List-Unsubscribe` header.
- Add the unsubscribe page and the one-click POST endpoint.
- Demo: click unsubscribe. The status changes to Unsubscribed.

### 6. CSV import

- Add an import dialog: upload a CSV, map the columns, pick tags.
- Import rows as Active. Skip emails that already exist and add the tags to them.
- Add status, tag, and form filters to the Subscribers page.
- Demo: import the LMS user export with the tag `lms-alumni`, then filter by that tag.

### 7. Newsletter draft and test send

- Do the editor spike and build `EmailEditor.vue`.
- Add `Newsletter Issue` and the Newsletters page with the editor and the iframe preview.
- Add a test send to an address. The dialog starts with the current user's address.
- Add a theme picker. The default theme uses frappe-ui tokens.
- Demo: write an issue, preview it at mobile width, send a test, read it in Gmail.

### 8. Send to audience

- Send to all Active subscribers or to subscribers with the chosen tags.
- Add `default_hourly_limit` to `Mailing Settings` and `hourly_limit` to the issue.
- Queue the emails in a background job in hourly batches with `send_after`. Show progress and set the status to Sent.
- Skip Unsubscribed and Bounced subscribers.
- Demo: send an issue to a test tag with three subscribers. All three get it.

### 9. Schedule send

- Add a scheduler job that sends Scheduled issues when `scheduled_at` is due.
- Demo: schedule an issue five minutes ahead. It sends without other action.

### 10. Open and click tracking

- Add the open pixel and rewrite links to the click redirect at send time.
- Show opens, clicks, and top links on the issue page.
- Note: Apple Mail Privacy Protection loads pixels, so the open count is higher than the real count.
- Demo: open a sent issue and click a link. The stats change.

### 11. Web archive

- Add the `/newsletter` index and the `/newsletter/<route>` page for public sent issues.
- Remove the tracking pixel and the unsubscribe link from the web version.
- Demo: mark an issue public and open its URL while logged out.

### 12. Dashboard

- Show subscriber growth over time, signups and confirm rate per form, and stats for the last issue.
- Demo: open the dashboard and see numbers that match the lists.

### 13. Custom editor blocks

- Add the Footer block. It reads `Mailing Settings`.
- Add the YouTube video block: thumbnail, play button, title, and a link to YouTube.
- Demo: paste a video URL, preview the issue, click the thumbnail in Mailpit. YouTube opens.

## Open questions

- Which subdomain and From address send the email? For example `mail.bwh.tech` and `hussain@mail.bwh.tech`.
- What are the GSTIN and registered address of BWH Technologies LLP? These go in `Mailing Settings`. Get them from the GST certificate or the ERP Company record on hq.bwh.tech.
