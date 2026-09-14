"""The order of the videos in a series. Positions run 1, 2, 3 with no gaps."""

import frappe
from frappe import _

VIDEO = "BWH Video"


class SeriesOrder:
	def __init__(self, series: int | str):
		self.series = series

	def next_position(self) -> int:
		"""The position for a video that joins the series at the end."""
		return len(self.names()) + 1

	def move(self, video: int, position: int) -> list[int]:
		"""Put the video at `position` and shift the others. Returns the new order."""
		names = self.names()
		if video not in names:
			frappe.throw(_("Video {0} is not in this series").format(video))
		names.remove(video)
		names.insert(max(position, 1) - 1, video)
		self.save(names)
		return names

	def close_gap(self, leaving: int | None = None):
		"""Renumber after a video leaves the series. `leaving` is still in the database on delete."""
		self.save([name for name in self.names() if name != leaving])

	def names(self) -> list[int]:
		return frappe.get_all(
			VIDEO,
			filters={"series": self.series},
			order_by="position asc, creation asc",
			pluck="name",
		)

	def save(self, names: list[int]):
		# A direct write, so moving one video does not run validate on all of them.
		for position, name in enumerate(names, start=1):
			frappe.db.set_value(VIDEO, name, "position", position, update_modified=False)
		# Open pages reload on this event. A direct write does not send it.
		frappe.publish_realtime(
			"list_update", {"doctype": VIDEO, "user": frappe.session.user}, after_commit=True
		)
