# Copyright (c) 2026, BWH and contributors
# For license information, please see license.txt

import re

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import get_url

FOOTER_TEMPLATE = "bwh_os/templates/emails/newsletter_footer.html"
BODY_END = re.compile(r"</body\s*>", re.IGNORECASE)
CELL_END = re.compile(r"</td\s*>", re.IGNORECASE)


class NewsletterIssue(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		content_html: DF.Code | None
		content_json: DF.JSON | None
		preview_text: DF.Data | None
		status: DF.Literal["Draft", "Scheduled", "Sending", "Sent", "Failed"]
		subject: DF.Data
		theme: DF.Literal["Frappe UI", "Basic", "Minimal"]
	# end: auto-generated types

	def send_test(self, recipient: str):
		"""Send the saved content to one address, with "[Test]" before the subject."""
		if not self.content_html:
			frappe.throw(_("Write the newsletter before you send a test"))

		settings = frappe.get_cached_doc("Mailing Settings")
		# A test goes to a user, not a subscriber, so the link has no real token.
		unsubscribe_url = get_url("/api/method/bwh_os.mailing.api.unsubscribe?token=test")
		queued = frappe.sendmail(
			recipients=[recipient],
			sender=settings.get_sender(),
			subject=_("[Test] {0}").format(self.subject),
			message=self.get_email_html(unsubscribe_url),
			# The editor makes a full HTML document. Frappe's wrapper would nest it.
			raw_html=True,
			reference_doctype=self.doctype,
			reference_name=self.name,
			add_unsubscribe_link=0,
		)
		# Frappe drops an address with a global Email Unsubscribe record and raises nothing.
		if not queued:
			frappe.throw(
				_("{0} is unsubscribed from all email in Frappe. Remove its Email Unsubscribe record.").format(
					recipient
				)
			)

	def get_email_html(self, unsubscribe_url: str) -> str:
		"""The content with the company footer and the unsubscribe link at the end of the email."""
		footer = frappe.render_template(
			FOOTER_TEMPLATE,
			{"settings": frappe.get_cached_doc("Mailing Settings"), "unsubscribe_url": unsubscribe_url},
		)
		html = self.content_html
		body_ends = list(BODY_END.finditer(html))
		if not body_ends:
			return html + footer

		# The editor puts the email in one outer table cell that has the theme background.
		# Its closing tag is the last </td>, so the footer goes before it.
		body_end = body_ends[-1].start()
		cell_ends = list(CELL_END.finditer(html, 0, body_end))
		at = cell_ends[-1].start() if cell_ends else body_end
		return html[:at] + footer + html[at:]
