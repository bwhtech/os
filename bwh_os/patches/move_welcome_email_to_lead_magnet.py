"""Move the "here is your file" email from the signup form onto the lead magnet it links.

The magnet now delivers itself (see Lead Magnet.subject/content_html). The form's own
welcome email becomes a plain greeting, sent before the file, and no longer needs — or is
allowed — a download link of its own.

Runs on `frappe.db.set_value`, never `.save()`: the new validations on both doctypes would
throw partway through a migration over data that is, by definition, not valid under them yet.
"""

import frappe

DOWNLOAD_MARKER = "download_url"


def execute():
	filled, cleared, kept = [], [], []

	# Oldest first, so when two forms share a magnet, the one that has been linked the
	# longest is the one whose email the magnet keeps.
	for name in frappe.get_all(
		"Signup Form", filters={"lead_magnet": ("is", "set")}, order_by="creation asc", pluck="name"
	):
		form = frappe.db.get_value(
			"Signup Form",
			name,
			[
				"lead_magnet",
				"welcome_subject",
				"welcome_theme",
				"welcome_content_json",
				"welcome_content_html",
				"welcome_reply_to",
			],
			as_dict=True,
		)
		magnet_subject = frappe.db.get_value("Lead Magnet", form.lead_magnet, "subject")

		if form.welcome_subject and not magnet_subject:
			frappe.db.set_value(
				"Lead Magnet",
				form.lead_magnet,
				{
					"subject": form.welcome_subject,
					"theme": form.welcome_theme,
					"content_json": form.welcome_content_json,
					"content_html": form.welcome_content_html,
					"reply_to": form.welcome_reply_to,
				},
			)
			filled.append(form.lead_magnet)
		elif form.welcome_subject and magnet_subject:
			# A second form on the same magnet. Its content would double the send and fail
			# the new welcome-email check either way, so it is logged, not silently dropped.
			frappe.log_error(
				title=f"{name}: welcome email dropped, {form.lead_magnet} already has one",
				message=form.welcome_content_html or "",
			)

		if form.welcome_content_html and DOWNLOAD_MARKER in form.welcome_content_html:
			# The email moved to the magnet, or was a dead link to begin with either way, a
			# form cannot keep text that the new WELCOME variables no longer allow.
			frappe.db.set_value(
				"Signup Form",
				name,
				{
					"welcome_subject": "",
					# A JSON column rejects an empty string; NULL is the "nothing here" value.
					"welcome_content_json": None,
					"welcome_content_html": "",
					"welcome_reply_to": "",
				},
			)
			cleared.append(name)
		elif form.welcome_subject:
			# Already a plain greeting. set_send_welcome_email keeps it going out before the file.
			kept.append(name)

	# A form with no magnet can still carry a dead download link from before this change: the
	# old WELCOME variables allowed it and only required it when a magnet was set.
	for name in frappe.get_all(
		"Signup Form",
		filters={"lead_magnet": ("is", "not set"), "welcome_content_html": ("like", f"%{DOWNLOAD_MARKER}%")},
		pluck="name",
	):
		frappe.log_error(
			title=f"{name}: welcome email dropped, its download link was already dead",
			message=frappe.db.get_value("Signup Form", name, "welcome_content_html") or "",
		)
		frappe.db.set_value(
			"Signup Form",
			name,
			{"welcome_subject": "", "welcome_content_json": None, "welcome_content_html": ""},
		)
		cleared.append(name)

	still_empty = sorted(
		{*frappe.get_all("Lead Magnet", filters={"subject": ("is", "not set")}, pluck="name")}
		| {*frappe.get_all("Lead Magnet", filters={"subject": ""}, pluck="name")}
	)

	print(
		f"Lead magnet emails — filled from a form: {len(filled)}, "
		f"forms cleared: {len(cleared)}, forms kept as a greeting: {len(kept)}, "
		f"still without an email: {still_empty or 'none'}"
	)
