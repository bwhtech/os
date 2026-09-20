# Copyright (c) 2026, BWH and contributors
# For license information, please see license.txt

from urllib.parse import urlencode

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import get_url, now_datetime

from bwh_os.mailing import email_variables
from bwh_os.mailing.emails import ListEmail
from bwh_os.mailing.lead_magnet_page import ROUTE_PREFIX, LeadMagnetRoute


class LeadMagnet(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		blurb: DF.SmallText | None
		content_html: DF.Code | None
		content_json: DF.JSON | None
		description: DF.SmallText | None
		file: DF.Attach
		reply_to: DF.Data | None
		route: DF.Data | None
		subject: DF.Data | None
		theme: DF.Literal["Frappe UI", "Basic", "Minimal"]
		title: DF.Data
	# end: auto-generated types

	def validate(self):
		# A public file would be open to anyone with the URL, with no download logged.
		if not self.file.startswith("/private/files/"):
			frappe.throw(_("Upload the lead magnet as a private file"))
		LeadMagnetRoute(self).validate()
		self.validate_email()

	def validate_email(self):
		if not self.subject:
			return
		if not self.content_html:
			frappe.throw(_("Write the delivery email, or clear its subject to send nothing"))
		email_variables.check(self.subject, email_variables.LEAD_MAGNET, _("The subject"))
		email_variables.check(
			self.content_html,
			email_variables.LEAD_MAGNET,
			_("The delivery email"),
			required=["download_url"],
		)

	def has_email(self) -> bool:
		return bool(self.subject and self.content_html)

	def values_for(self, subscriber) -> dict[str, str]:
		return {"download_url": self.get_download_url(subscriber.token), "lead_magnet": self.title}

	def get_download_url(self, subscriber_token: str) -> str:
		"""The link that goes in an email. The token says who is asking."""
		return get_url(f"/{ROUTE_PREFIX}{self.route}?{urlencode({'token': subscriber_token})}")

	def get_file(self):
		return frappe.get_doc("File", {"file_url": self.file})

	def log_download(self, subscriber: str):
		frappe.get_doc(
			{
				"doctype": "Lead Magnet Download",
				"lead_magnet": self.name,
				"subscriber": subscriber,
				"downloaded_on": now_datetime(),
			}
		).insert(ignore_permissions=True)

	def send_to(self, subscriber, source: str, reference: str | None = None):
		"""The "here is your file" email, with a link only this subscriber can use."""
		if not self.has_email():
			frappe.throw(_("{0} has no delivery email").format(self.title))
		ListEmail(
			subscriber, self.subject, self.content_html, self.values_for(subscriber), reply_to=self.reply_to
		).send()
