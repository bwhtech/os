# BWH OS

BWH OS is the control panel for BWH Media & Products. It is a [Frappe](https://frappe.io/framework) app with a [frappe-ui](https://ui.frappe.io) frontend at `/os`.

BWH runs a YouTube channel, cohorts, open-source products, and client work. The data for this work is in many tools. BWH OS puts the work in one place, and BWH owns the data.

The first module is the email list. See [specs/README.md](specs/README.md) for the full plan.

## Features

### Dashboard

The dashboard shows the growth of the list, subscribers by status, and the stats of the last newsletter. It also shows open and click rates for the last 10 newsletters, and signups and the confirm rate for each signup form.

![Dashboard](.github/images/dashboard.png)

### Subscribers

- One list with tags. One unsubscribe removes a person from all sends.
- Filter by status, tag, and signup form. Search by email.
- Add a subscriber by hand.
- Import a CSV file. Map the columns, pick tags, and see what the import does before it starts. The import runs in a background job.

![Subscribers](.github/images/subscribers.png)

### Signup forms

- Each form has an ID. A website sends signups to the `subscribe` API with this ID.
- Single or double opt-in, set on each form.
- Tags to add on signup, a success message, and an optional lead magnet.
- A confirm email and a welcome email for each form, written in the email editor.
- The form page shows signup counts and the embed snippet.

![Signup form](.github/images/signup-form.png)

### Lead magnets

A lead magnet is a private file, for example a PDF. The welcome email has a download link with a token. Each download is logged.

![Lead magnet](.github/images/lead-magnet.png)

### Newsletters

![Newsletters](.github/images/newsletters.png)

#### Email editor

Every email in OS uses the same editor. The editor is [React Email editor](https://react.email/docs/editor/overview) in a shadow root inside the Vue app.

- Type `/` for blocks: headings, lists, buttons, columns, code, and more.
- Type `{{` to add a variable, for example the first name of the subscriber.
- **YouTube video block.** Paste a YouTube link on its own line. The block shows the thumbnail with a play button and the title, and links to the video.
- **Footer block.** The block shows the social links, the company details, and the unsubscribe link from Settings. An email without the block gets the footer at the end.
- Three themes: Frappe UI, Basic, and Minimal.
- Press Cmd+S or Ctrl+S to save a draft.

![Newsletter editor](.github/images/newsletter-editor.png)

#### Preview and send

- Preview the email at desktop and mobile width, with sample values.
- Send a test to any address.
- Send to all Active subscribers, or to subscribers with some tags. The page shows the recipient count before the send.
- Emails go out in hourly batches. Each newsletter has an hourly limit.
- Send now, or schedule the send for later.

![Newsletter preview](.github/images/newsletter-preview.png)

#### Report

- Counts for recipients, sent, failed, and skipped emails.
- Open rate, click rate, and unsubscribes, each against the previous newsletter.
- A funnel from recipients to clicks, opens and clicks per hour, and the top links.
- Publish a sent newsletter to the web archive at `/newsletter/<route>`.

![Newsletter report](.github/images/newsletter-report.png)

### Settings

The Settings dialog sets the email account that sends list email, the default hourly limit, and the footer: the company name, GSTIN, postal address, and social links.

![Settings](.github/images/settings.png)

## Upcoming

### Email list

- Show the confirm rate on the signup form page.
- Connect the signup form on bwh.tech to the `subscribe` API through the Netlify function.
- Set the sending subdomain and From address, for example `mail.bwh.tech`.
- Add the GSTIN and the registered address of BWH Technologies LLP to Settings.

These items are out of scope for v1. They can come later:

- Drip and automation sequences.
- Bounce and complaint processing, with a webhook from the email provider.
- Captcha on signup forms.
- Live sync of new LMS users.
- Segments from opens and clicks.
- Resend to people who did not open.
- More than one list.

### New modules

| # | Module | Plan |
|---|---|---|
| 02 | Content Pipeline | Track each video from idea to publish, on a Kanban board and a calendar. |
| 03 | Social Posts | Plan posts for X, LinkedIn, the YouTube community tab, and Discord. Show them on the same calendar. |
| 04 | YouTube Integration | Sync the channel videos. Find and replace text in descriptions, update calls to action on many videos, and find videos with no chapters or playlists. |
| 05 | LMS Integration | Show live cohorts, seats sold, and revenue for each batch from school.bwh.tech. |
| 06 | GitHub Integration | Show stars, open issues, open pull requests, and releases for the core products. |

## Installation

Install this app with the [bench](https://github.com/frappe/bench) CLI:

```bash
cd $PATH_TO_YOUR_BENCH
bench get-app $URL_OF_THIS_REPO --branch develop
bench install-app bwh_os
```

Only users with the System Manager role can open `/os`.

## Development

### Frontend

The frontend is in the `frontend` folder. The Vite dev server sends API calls to port 8000.

```bash
cd frontend
yarn install
yarn dev
```

`yarn build` builds the app into `bwh_os/public/frontend` and `bwh_os/www/os.html`.

### Local email

1. Start [Mailpit](https://mailpit.axllent.org) in Docker, with SMTP on port 1025 and the web UI on port 8025.
2. Make an Email Account that sends through `localhost:1025` with no auth and no TLS.
3. Select that Email Account in Settings.
4. Open `http://localhost:8025` to read the emails that OS sends.

### Tests

```bash
bench --site $SITE run-tests --app bwh_os
```

## Contributing

This app uses `pre-commit` for code formatting and linting. [Install pre-commit](https://pre-commit.com/#installation) and enable it for this repository:

```bash
cd apps/bwh_os
pre-commit install
```

Pre-commit uses these tools to check and format the code:

- ruff
- eslint
- prettier
- pyupgrade

## CI

This app uses GitHub Actions for CI:

- CI: installs this app and runs the unit tests on every push to the `develop` branch.
- Linters: runs [Frappe Semgrep Rules](https://github.com/frappe/semgrep-rules) and [pip-audit](https://pypi.org/project/pip-audit/) on every pull request.

## License

MIT
