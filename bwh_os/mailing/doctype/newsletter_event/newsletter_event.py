# Copyright (c) 2026, BWH and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class NewsletterEvent(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		delivery: DF.Link
		issue: DF.Link
		type: DF.Literal["Open", "Click", "Unsubscribe"]
		url: DF.SmallText | None
	# end: auto-generated types

	pass


def on_doctype_update():
	# The report groups events of one issue by type, hour, and link.
	frappe.db.add_index("Newsletter Event", ("issue", "type", "creation"))
