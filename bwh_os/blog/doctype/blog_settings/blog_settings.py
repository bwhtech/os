# Copyright (c) 2026, BWH and contributors
# For license information, please see license.txt

from frappe.model.document import Document


class BlogSettings(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		turso_token: DF.Password | None
		turso_url: DF.Data | None
	# end: auto-generated types

	def validate(self):
		self.turso_url = (self.turso_url or "").strip()
