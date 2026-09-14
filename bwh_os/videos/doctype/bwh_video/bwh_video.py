# Copyright (c) 2026, BWH and contributors
# For license information, please see license.txt

from frappe.model.document import Document
from frappe.utils import cstr

from bwh_os.videos.series_order import SeriesOrder


class BWHVideo(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		description: DF.TextEditor | None
		name: DF.Int | None
		position: DF.Int
		publish_on: DF.Date | None
		research: DF.TextEditor | None
		script: DF.TextEditor | None
		series: DF.Link | None
		status: DF.Literal["Idea", "Researching", "Scripting", "Recording", "Editing", "Thumbnail Pending", "Published"]
		title: DF.Data
		youtube_url: DF.Data | None
	# end: auto-generated types

	def validate(self):
		self.set_position()

	def on_update(self):
		before = self.get_doc_before_save()
		if before and before.series and self.series_changed():
			SeriesOrder(before.series).close_gap()

	def on_trash(self):
		if self.series:
			SeriesOrder(self.series).close_gap(leaving=self.name)

	def set_position(self):
		"""The server owns the position. A video that joins a series goes to the end."""
		if not self.series:
			self.position = 0
		elif self.series_changed():
			self.position = SeriesOrder(self.series).next_position()
		else:
			self.position = self.get_doc_before_save().position

	def series_changed(self) -> bool:
		before = self.get_doc_before_save()
		# A save turns the Link to the autoincrement series into an int, and the copy from the
		# database holds a str, so compare them as text.
		return not before or cstr(before.series) != cstr(self.series)
