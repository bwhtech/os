# Copyright (c) 2026, BWH and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class NewsletterDelivery(Document):
	pass


def on_doctype_update():
	# One row per subscriber per issue, so a second run of the send job cannot send twice.
	frappe.db.add_unique(
		"Newsletter Delivery", ("issue", "subscriber"), constraint_name="unique_issue_subscriber"
	)
	frappe.db.add_index("Newsletter Delivery", ("issue", "status"))
