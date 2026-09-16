# Copyright (c) 2026, BWH and contributors
# For license information, please see license.txt

from frappe.model.document import Document


class SocialPostPart(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		channel: DF.Link | None
		media: DF.JSON | None
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		part_no: DF.Int
		text: DF.LongText | None
	# end: auto-generated types

	pass
