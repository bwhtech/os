# Copyright (c) 2026, BWH and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import get_url, now_datetime, validate_email_address

from bwh_os.mailing.doctype.subscriber_tag.subscriber_tag import SubscriberTag


class Subscriber(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from bwh_os.mailing.doctype.subscriber_tag_item.subscriber_tag_item import SubscriberTagItem

		confirmed_on: DF.Datetime | None
		consent_ip: DF.Data | None
		email: DF.Data
		first_name: DF.Data | None
		source_form: DF.Link | None
		source_url: DF.SmallText | None
		status: DF.Literal["Pending", "Active", "Unsubscribed", "Bounced"]
		subscribed_on: DF.Datetime | None
		tags: DF.TableMultiSelect[SubscriberTagItem]
		token: DF.Data | None
		unsubscribed_on: DF.Datetime | None
		utm: DF.JSON | None
	# end: auto-generated types

	# Runs before naming, so the document name is the normalized email.
	def before_insert(self):
		self.email = normalize_email(self.email)
		self.ensure_not_on_list()
		self.token = frappe.generate_hash(length=32)
		self.subscribed_on = self.subscribed_on or now_datetime()

	def validate(self):
		self.email = normalize_email(self.email)
		validate_email_address(self.email, throw=True)

	def activate(self):
		"""Make the subscriber Active. The confirm date is the first one, not the latest."""
		self.status = "Active"
		self.confirmed_on = self.confirmed_on or now_datetime()

	def unsubscribe(self):
		"""Remove the subscriber from all sends. A Bounced subscriber stays Bounced."""
		if self.status in ("Pending", "Active"):
			self.status = "Unsubscribed"
			self.unsubscribed_on = now_datetime()

	def set_status(self, status: str):
		"""Change the status by hand. The dates follow it, but no email is sent."""
		if status == "Active":
			self.activate()
		elif status == "Unsubscribed":
			self.status = status
			self.unsubscribed_on = self.unsubscribed_on or now_datetime()
		else:
			self.status = status

	def get_unsubscribe_url(self) -> str:
		return get_url(f"/api/method/bwh_os.mailing.api.unsubscribe?token={self.token}")

	def add_tags(self, tag_names: list[str]):
		"""Append tags the subscriber does not have yet, creating missing ones.

		Frappe checks links before any save hook runs, so tags must exist before the save.
		"""
		existing = {row.tag for row in self.tags}
		for tag_name in clean_tag_names(tag_names):
			if tag_name in existing:
				continue
			self.append("tags", {"tag": SubscriberTag.ensure(tag_name)})
			existing.add(tag_name)

	def ensure_not_on_list(self):
		if frappe.db.exists("Subscriber", self.email):
			frappe.throw(_("{0} is already on the list").format(self.email), frappe.DuplicateEntryError)


def normalize_email(email: str | None) -> str:
	return (email or "").strip().lower()


def clean_tag_names(tag_names: list[str]) -> list[str]:
	return [name.strip() for name in tag_names if name and name.strip()]
