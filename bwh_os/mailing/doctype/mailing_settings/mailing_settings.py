# Copyright (c) 2026, BWH and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import validate_email_address

SOCIAL_LINK_FIELDS = ("youtube_url", "x_url", "linkedin_url", "github_url", "discord_url")


class MailingSettings(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		blog_notification_email: DF.Data | None
		company_name: DF.Data | None
		default_hourly_limit: DF.Int
		discord_url: DF.Data | None
		email_account: DF.Link | None
		github_url: DF.Data | None
		gstin: DF.Data | None
		linkedin_url: DF.Data | None
		notify_blog_comments: DF.Check
		postal_address: DF.SmallText | None
		reply_to: DF.Data | None
		x_url: DF.Data | None
		youtube_url: DF.Data | None
	# end: auto-generated types

	def validate(self):
		if self.reply_to:
			validate_email_address(self.reply_to, throw=True)
		if self.notify_blog_comments and not self.blog_notification_email:
			self.blog_notification_email = frappe.db.get_value("User", frappe.session.user, "email")

	def get_social_links(self) -> list[dict]:
		"""The social links that are set, in the order of the form."""
		return [
			{"label": self.meta.get_label(field), "url": self.get(field)}
			for field in SOCIAL_LINK_FIELDS
			if self.get(field)
		]

	def get_sender(self) -> str | None:
		"""The From address. None lets Frappe use the default outgoing account."""
		if not self.email_account:
			return None
		return frappe.db.get_value("Email Account", self.email_account, "email_id")

	def get_reply_to(self, override: str | None = None) -> str | None:
		"""Where replies go. An email that names its own address wins.

		None leaves the header out, and a reply goes to the From address.
		"""
		return override or self.reply_to or None
