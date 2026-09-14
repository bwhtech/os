# Copyright (c) 2026, BWH and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import validate_email_address

BODY_MAX = 2000


class BWHBlogComment(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		body: DF.Text
		commenter_name: DF.Data
		email: DF.Data
		hidden: DF.Check
		name: DF.Int | None
		post: DF.Link
	# end: auto-generated types

	def validate(self):
		self.email = self.email.strip().lower()
		validate_email_address(self.email, throw=True)
		if len(self.body) > BODY_MAX:
			frappe.throw(_("Keep the comment under {0} characters").format(BODY_MAX))
