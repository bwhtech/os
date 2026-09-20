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

# A manual send has no hourly batching, unlike a newsletter. Past this, use one instead.
MANUAL_SEND_LIMIT = 50


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

	def matching_query(self, subscribers: list[str] | None, tags: list[str] | None):
		"""Query builder for Active subscribers this send would reach: named, or by tag."""
		table = frappe.qb.DocType("Subscriber")
		query = frappe.qb.from_(table).select(table.name, table.email).where(table.status == "Active")
		if subscribers:
			query = query.where(table.name.isin(subscribers))
		elif tags:
			item = frappe.qb.DocType("Subscriber Tag Item")
			tagged = (
				frappe.qb.from_(item)
				.select(item.parent)
				.where((item.parenttype == "Subscriber") & item.tag.isin(tags))
			)
			query = query.where(table.name.isin(tagged))
		else:
			query = query.where(table.name == "")
		return query, table

	def recipients(
		self,
		subscribers: list[str] | None = None,
		tags: list[str] | None = None,
		skip_downloaded: bool = True,
	) -> list[dict]:
		"""Who a manual send would reach now."""
		query, table = self.matching_query(subscribers, tags)
		if skip_downloaded:
			query = query.where(table.name.notin(downloaders_of(self.name)))
		return query.run(as_dict=True)

	def already_downloaded_count(self, subscribers: list[str] | None, tags: list[str] | None) -> int:
		"""Of the matching subscribers, how many already have this file."""
		query, table = self.matching_query(subscribers, tags)
		return len(query.where(table.name.isin(downloaders_of(self.name))).run())

	def send_many(self, subscribers: list[str], source: str, reference: str | None = None) -> dict:
		"""Send to each by name. A failure on one does not stop the rest."""
		if not self.has_email():
			frappe.throw(_("{0} has no delivery email").format(self.title))
		sent, failed = 0, []
		for name in subscribers:
			try:
				self.send_to(frappe.get_doc("Subscriber", name), source=source, reference=reference)
				sent += 1
			except Exception:
				failed.append(name)
				frappe.log_error(
					f"Manual send of {self.name} to {name} failed",
					reference_doctype="Lead Magnet",
					reference_name=self.name,
				)
		return {"sent": sent, "failed": failed}


def downloaders_of(lead_magnet: str):
	"""Subscribers who already have this file, as a query builder subquery.

	Shared by the manual send above and the newsletter audience filter, so "already has it"
	means one thing everywhere it is asked.
	"""
	download = frappe.qb.DocType("Lead Magnet Download")
	return frappe.qb.from_(download).select(download.subscriber).where(download.lead_magnet == lead_magnet)
