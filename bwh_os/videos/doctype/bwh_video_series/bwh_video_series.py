# Copyright (c) 2026, BWH and contributors
# For license information, please see license.txt

from frappe.model.document import Document


class BWHVideoSeries(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		emoji: DF.Data | None
		name: DF.Int | None
		notes: DF.TextEditor | None
		summary: DF.SmallText | None
		title: DF.Data
	# end: auto-generated types

	pass
