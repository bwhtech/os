# Copyright (c) 2026, BWH and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import now_datetime


class NewsletterDelivery(Document):
	"""One issue to one subscriber. The tracking links carry its name."""

	def record_open(self):
		first = not self.first_opened_at
		self.db_set(
			{"open_count": self.open_count + 1, "first_opened_at": self.first_opened_at or now_datetime()},
			update_modified=False,
		)
		self.log_event("Open")
		if first:
			self.count_on_issue("opened_count")

	def record_click(self, url: str):
		"""A click also counts as an open, because some mail apps block the pixel."""
		if not self.first_opened_at:
			self.record_open()
		first = not self.first_clicked_at
		self.db_set(
			{"click_count": self.click_count + 1, "first_clicked_at": self.first_clicked_at or now_datetime()},
			update_modified=False,
		)
		self.log_event("Click", url)
		if first:
			self.count_on_issue("clicked_count")

	def record_unsubscribe(self):
		if self.unsubscribed_at:
			return
		self.db_set("unsubscribed_at", now_datetime(), update_modified=False)
		self.log_event("Unsubscribe")
		self.count_on_issue("unsubscribed_count")

	def log_event(self, event_type: str, url: str | None = None):
		frappe.get_doc(
			{
				"doctype": "Newsletter Event",
				"delivery": self.name,
				"issue": self.issue,
				"type": event_type,
				"url": url,
			}
		).insert(ignore_permissions=True)

	def count_on_issue(self, field: str):
		# One UPDATE, so opens from many readers at once do not lose counts.
		table = frappe.qb.DocType("Newsletter Issue")
		frappe.qb.update(table).set(table[field], table[field] + 1).where(table.name == self.issue).run()


def on_doctype_update():
	# One row per subscriber per issue, so a second run of the send job cannot send twice.
	frappe.db.add_unique(
		"Newsletter Delivery", ("issue", "subscriber"), constraint_name="unique_issue_subscriber"
	)
	frappe.db.add_index("Newsletter Delivery", ("issue", "status"))
