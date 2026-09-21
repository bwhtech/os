# Copyright (c) 2026, BWH and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class BWHCanvas(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		name: DF.Int | None
		scene: DF.LongText | None
		thumbnail: DF.LongText | None
		title: DF.Data
		video: DF.Link | None
	# end: auto-generated types

	def validate(self):
		self.validate_one_canvas_per_video()

	def validate_one_canvas_per_video(self):
		"""The video page opens the canvas of the video, so a second one could never be seen there."""
		if not self.video:
			return
		other = frappe.db.get_value("BWH Canvas", {"video": self.video, "name": ("!=", self.name or 0)})
		if other:
			frappe.throw(_("Video {0} already has a canvas").format(self.video))
