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
| Audience | The audience is fixed when the send starts. A person who subscribes during a send does not get the issue. |
| Delivery | One `Newsletter Delivery` row for each issue and subscriber. Stats come from these rows, because Frappe deletes old Email Queue records. |
| Issue failure | An issue is Failed only when no email went out. Otherwise it is Sent, and the page shows the failed count. |
| Import | CSV rows import as Active, with tags. |
| LMS sync | Once a day, OS reads new LMS users and batch enrollments with an API key. New users join as Active with no welcome email. Enrollees get the enrollment tags. |
| Editor | An `EmailEditor.vue` wrapper around `@react-email/editor`. The spike in slice 7 passed. See [Editor](#editor). |

### Out of scope for v1

- Drip or automation sequences.
- Bounce and complaint processing. This needs a webhook from the email provider.
- Captcha (for example Cloudflare Turnstile). The Netlify function already has a honeypot and a rate limit.
- Live sync of new LMS users. A daily sync was added later. See `bwh_os/mailing/lms_sync.py`.
- Segments based on opens or clicks.
- Resend to people who did not open. `Newsletter Delivery` makes this possible later.
- More than one list.

## How?

### Data model

All doctypes go in a new module, `Mailing`.

**Mailing Settings** (single doctype)

| Field | Type | Notes |
|---|---|---|
| email_account | Link: Email Account | Sends all list email |
| reply_to | Data (Email) | Where replies to list email go. Empty leaves the header out, so a reply goes to the sending account. An email of its own wins over this one. |
| default_hourly_limit | Int | Default 500. New issues copy this value. |
| company_name | Data | BWH Technologies LLP |
| gstin | Data | |
| postal_address | Small Text | Shown in the email footer |
| youtube_url, x_url, linkedin_url, github_url, discord_url | Data (URL) | Social links in the email footer. Empty links are left out. |

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
| confirm_reply_to, welcome_reply_to | Data (Email) | Where a reply to that email goes. Empty uses `Mailing Settings`. |
| confirm_subject, confirm_theme, confirm_content_json, confirm_content_html | Data, Select, JSON, Code | Used when double opt-in is on. Written in `EmailComposer`. The content must link to `{{ confirm_url }}`. |
| welcome_subject, welcome_theme, welcome_content_json, welcome_content_html | Data, Select, JSON, Code | Sent when the subscriber becomes Active. With a lead magnet, the content must link to `{{ download_url }}`. |

The form page in OS also shows the signup count, the confirm rate, and the embed snippet.

**Lead Magnet**: title, description, file (private Attach).

**Lead Magnet Download**: lead_magnet, subscriber, downloaded_on. The lead magnet page lists the last 100 downloads with the subscriber.

**Newsletter Issue**

| Field | Type | Notes |
|---|---|---|
| subject | Data | |
| preview_text | Data | |
| reply_to | Data (Email) | Where a reply to this issue goes. Empty uses `Mailing Settings`. Locked once the send starts. |
| content_json | JSON | Editor document |
| content_html | Code (HTML) | Email-safe HTML. The editor makes it in the browser and OS saves it with `content_json`. Code, because Frappe sanitizes Long Text and removes `<html>`, `<head>`, and `<body>`. |
| theme | Select | Frappe UI (default), Basic, Minimal. Frappe UI uses the frappe-ui light tokens as hex colors. |
| audience | Select | All Active, Tags |
| tags | Table MultiSelect | Used when audience is Tags. A subscriber with any of the tags gets the issue. |
| status | Select | Draft, Scheduled, Sending, Sent, Failed |
| scheduled_at | Datetime | |
| hourly_limit | Int | Max emails per hour for this issue. Copied from `Mailing Settings` on create. |
| sent_at | Datetime | When the send started |
| completed_at | Datetime | When the last email left the queue |
| recipient_count | Int | Delivery rows made when the send started |
| sent_count, failed_count, skipped_count | Int | Counts of delivery rows. The sync job keeps them current. |
| opened_count, clicked_count, unsubscribed_count | Int | Slice 10. Subscribers who opened, clicked, or unsubscribed from this issue. |
| is_public | Check | Show in the web archive. Slice 11. |
| route | Data | Slug for the web archive |

The name `Newsletter Issue` prevents a clash with the separate Frappe `newsletter` app.

After the send starts, the subject, content, and audience cannot change.

**Newsletter Delivery**: one row for each issue and subscriber. The name is a random hash. Tracking links carry it.

| Field | Type | Notes |
|---|---|---|
| issue | Link: Newsletter Issue | Unique with `subscriber` |
| subscriber | Link: Subscriber | |
| email | Data | The address at send time |
| batch | Int | Hour of the send, from 0. Batch N sends at `sent_at + N hours`. |
| status | Select | Queued, Sent, Failed, Skipped. Skipped means the subscriber was not Active when the email was due to queue. |
| email_queue | Data | Name of the Email Queue record. Data, not Link, because Frappe deletes old queue records. |
| error | Small Text | Why the email failed or was skipped |
| queued_at | Datetime | |
| first_opened_at, open_count | Datetime, Int | Slice 10 |
| first_clicked_at, click_count | Datetime, Int | Slice 10. A click also counts as an open. |
| unsubscribed_at | Datetime | Slice 10. Set when the unsubscribe link in this issue is used. |

**Newsletter Event**: delivery, issue, type (Open, Click, Unsubscribe), url. Slice 10. The raw log for opens and clicks over time and for top links. `creation` is the time of the event.

### API

Put the methods in `bwh_os/mailing/api.py`.

`subscribe(form_id, email, first_name=None, source_url=None, utm=None, consent_ip=None)`

- The Netlify function calls this method with the API key of a restricted user. That user has only the role `OS Signup API`.
- All calls come from Netlify, so a limit on the request IP would block every reader at once. The method uses Frappe `@rate_limit` keyed on `consent_ip`, the reader IP that the function passes: 5 in 10 minutes and 20 in a day.
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
- `email_read_tracker_url` does not fit. Frappe adds its pixel only through its own email wrapper, and issues use `raw_html`. Slice 10 adds our own pixel with the delivery name in the URL.
- Frappe sets the Email Queue status with `frappe.db.set_value`, so no document hook runs when an email goes out. A sync job copies the status to the delivery rows.

Send flow:

1. Before the send, the issue page shows the audience: how many subscribers get the issue, how many have the tags but are not Active, and the hourly batches.
2. Send checks that the issue is a Draft, has content, and has at least one recipient. It sets the status to Sending and `sent_at`, then starts a background job.
3. The job makes one `Newsletter Delivery` row for each subscriber in the audience and sets `recipient_count`. A second run finds the rows and does not make them again.
4. The job queues each Queued row that has no `email_queue`, one `sendmail` call per row. Row N gets `batch = N // hourly_limit` and `send_after = sent_at + batch hours`. It commits every 100 rows.
5. A row whose subscriber is no longer Active becomes Skipped. A row that Frappe does not queue (for example a global `Email Unsubscribe`) becomes Failed.
6. A scheduler job runs every 2 minutes for each Sending issue. It copies the Email Queue status to the rows (Sent to Sent, Error to Failed) and updates the counts on the issue. If rows still wait for a queue record and no send job runs, it starts the job again.
7. When no row is Queued, the issue becomes Sent and gets `completed_at`. It becomes Failed if no row is Sent.
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
| Newsletters | `frappe-ui/list`, `EmailEditor.vue`, `DatePicker`, `TabButtons`, `frappe-ui/charts` | Write, preview, test send, pick the audience, send, schedule, see stats |
| Dashboard | `frappe-ui/charts` | Subscriber growth, signups per form, last issue stats |

### Editor

Hussain wants an editor like the [React Email editor](https://react.email/docs/editor/overview). That editor uses TipTap and ProseMirror and makes email-safe HTML. Its UI is React. BWH OS is Vue.

1. Make one wrapper, `EmailEditor.vue`. It takes the document JSON and emits the JSON and the email HTML.
2. Spike for half a day. Mount `@react-email/editor` in a shadow root inside the wrapper. Load it only on the newsletter editor route.
3. If the spike works, use it. The shadow root keeps the React Email styles and the frappe-ui styles apart.
4. If the spike fails, use `frappe-ui/editor` (also TipTap). Add email blocks (heading, paragraph, image, button, divider, code) and our own serializer to inline-styled table HTML.

Show the preview in an `iframe` with `srcdoc`, at desktop and mobile widths. Email HTML is a full document, so an iframe shows it the way an email client does.

Every email in OS (newsletters, confirm, and welcome) uses `EmailComposer.vue`: the editor, a preview, and the theme picker.

#### Variables

- Type `{{` in the editor to add a variable. It shows as a chip with a tooltip that says what replaces it. Typing or pasting `{{ first_name }}` also makes a chip.
- The chip serializes to `{{ first_name }}`. A link can also use a variable, for example a button to `{{ confirm_url }}`.
- The server fills the variables when it sends (`bwh_os/mailing/email_variables.py`). Values are HTML-escaped. `first_name` falls back to "there".
- Each email has its own variables. Newsletters: `first_name`, `email`. Confirm: also `confirm_url`. Welcome: also `download_url` and `lead_magnet`. A save fails for a variable that the email cannot fill.
- The preview, the test send, and the web archive use sample values or fallbacks.
- Subjects accept the same `{{ key }}` text, with no chips.

The editor must accept custom blocks. We add these blocks after v1 (slice 13):

- **Footer**: company name, GSTIN, postal address, and social links from `Mailing Settings`.
- **YouTube video**: paste a YouTube URL. The block shows the video thumbnail (`https://img.youtube.com/vi/<id>/maxresdefault.jpg`) with a play button and the title. The whole block links to the video on YouTube. Email clients do not play embedded video.

The spike passes only if we can add a custom block that serializes to email HTML. Test it with the YouTube block.

Spike result (slice 7): passed. A YouTube `EmailNode` with `renderToReactEmail` serialized to table HTML, and typing and slash commands work in the shadow root. Notes for later slices:

- The serializer (`composeReactEmail`) runs in the browser, so the server cannot make `content_html` from `content_json`.
- `EmailEditor` always adds its own slash menu, which reads `defaultSlashCommands`. Slice 13 adds the custom blocks to that list.
- The editor puts some styles in `document.head` and its menus in `document.body`. The wrapper copies the node styles into the shadow root and loads the menu theme on the page.
- The code block loads Prism CSS from `/styles/prism/`, which OS does not serve. Code blocks show no syntax colors in the editor.
- The editor chunk is about 720 KB gzip. It loads only on the newsletter page.
- `extendTheme` drops the styles for `blockquote`, `hr`, bold text, and other keys that have no inspector panel. The Frappe UI theme adds them with a small extension after `EmailTheming`, because `composeReactEmail` uses the serializer plugin of the last extension that has one.
- The editor converts px font sizes in theme panels against a 14px base, so the container font size is an extra style.

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
- Add `Newsletter Delivery` with the send fields. See [Sending](#sending) for the flow.
- Queue the emails in a background job in hourly batches with `send_after`. The sync job sets the status to Sent.
- Skip Unsubscribed, Bounced, and Pending subscribers.
- Draft issue page: an Audience section with a live recipient count. The send dialog shows number cards (recipients, not Active with the tags, estimated finish) and a bar chart of emails per hourly batch.
- Sending and Sent issue page: a Report tab with number cards (recipients, sent, failed, skipped), a stacked bar chart of each batch by status, and the recipient list with a status filter. The page refreshes while the issue is Sending.
- Add a Recipients column to the Newsletters list.
- Demo: send an issue to a test tag with three subscribers. All three get it.

### 9. Schedule send

- Add a scheduler job that sends Scheduled issues when `scheduled_at` is due. It runs every minute.
- The send dialog has "Send now" and "Schedule" options. Schedule runs the same checks as a send and needs a time in the future.
- A Scheduled issue cannot change. The issue page shows the send time, the email, and an Unschedule button that makes the issue a Draft again.
- The picker sends the browser time, and the server reads it as system time. They are the same for BWH (Asia/Kolkata).
- If a due issue cannot send (for example, no Active subscriber is left), it becomes Failed and the job logs an Error Log.
- Demo: schedule an issue five minutes ahead. It sends without other action.

### 10. Open and click tracking

- Add the open, click, and unsubscribe fields to `Newsletter Delivery`, and add `Newsletter Event`.
- Add the open pixel and rewrite links to the click redirect at send time. Both carry the delivery name.
- Report tab: number cards for open rate, click rate, and unsubscribes, each against the previous issue. A funnel chart (recipients, sent, opened, clicked), an area chart of opens and clicks per hour for the first 72 hours, and a bar chart of top links.
- Add Open % and Click % columns to the Newsletters list.
- Note: Apple Mail Privacy Protection loads pixels, so the open count is higher than the real count.
- Only `http` and `https` links are rewritten. `mailto:` and `#` links stay as they are. The footer links are not tracked.
- The click URL carries the delivery, the target URL, and an HMAC of both with the site secret. A bad signature shows a "Link not valid" page and does not redirect.
- The unsubscribe link and the `List-Unsubscribe` header carry the delivery, so the issue counts the unsubscribe.
- The issue counts go up with one `UPDATE ... SET count = count + 1` for the first open, click, or unsubscribe of a delivery.
- Test sends have no tracking.
- Demo: open a sent issue and click a link. The stats change.

### 11. Web archive

- Add the `/newsletter` index and the `/newsletter/<route>` page for public sent issues.
- Remove the tracking pixel and the unsubscribe link from the web version.
- Only a Sent issue can be public. The Publish dialog on the issue page sets `is_public` and `route`.
- The route is a unique slug. It comes from the subject when it is empty, and it can change after the send.
- A `page_renderer` hook serves `/newsletter/<route>` as the email document itself, not inside the site template.
- Demo: mark an issue public and open its URL while logged out.

### 12. Dashboard

- Show subscriber growth over time, signups and confirm rate per form, and stats for the last issue.
- After slice 10: a line chart of open rate and click rate for the last 10 issues.
- Demo: open the dashboard and see numbers that match the lists.

### 13. Custom editor blocks

- Add the Footer block. It saves as an empty `data-email-footer` marker. When the email goes out, the server puts the footer from `Mailing Settings` (social links, company details, unsubscribe link) in its place. An email with no Footer block gets the footer at the end, as before.
- Add the YouTube video block: thumbnail, play button, title, and a link to YouTube. Add it from the slash menu, or paste a YouTube link on its own line.
- The server gets the title from YouTube oEmbed and draws the play button into the thumbnail, because many email clients drop overlays. The image is a public file, made once for each video.
- Demo: paste a video URL, preview the issue, click the thumbnail in Mailpit. YouTube opens.

## Open questions

- Which subdomain and From address send the email? For example `mail.bwh.tech` and `hussain@mail.bwh.tech`.
- What are the GSTIN and registered address of BWH Technologies LLP? These go in `Mailing Settings`. Get them from the GST certificate or the ERP Company record on hq.bwh.tech.
