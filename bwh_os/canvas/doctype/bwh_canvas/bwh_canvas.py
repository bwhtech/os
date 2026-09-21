# Copyright (c) 2026, BWH and contributors
# For license information, please see license.txt

from frappe.model.document import Document


class BWHCanvas(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		name: DF.Int | None
		scene: DF.LongText | None
		title: DF.Data
		video: DF.Link | None
	# end: auto-generated types

	pass
