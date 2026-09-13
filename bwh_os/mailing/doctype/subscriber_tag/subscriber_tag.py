# Copyright (c) 2026, BWH and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class SubscriberTag(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		tag_name: DF.Data
	# end: auto-generated types

	@staticmethod
	def ensure(tag_name: str) -> str:
		"""Return the tag name, creating the tag first if it does not exist."""
		if not frappe.db.exists("Subscriber Tag", tag_name):
			frappe.get_doc({"doctype": "Subscriber Tag", "tag_name": tag_name}).insert()
		return tag_name
