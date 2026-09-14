"""Videos and series for the OS. See specs/03-videos.md."""

import frappe
from frappe.query_builder import Case
from frappe.query_builder.functions import Coalesce, Count, Sum

from bwh_os.videos.series_order import SeriesOrder


@frappe.whitelist(methods=["GET"])
def get_series() -> list[dict]:
	"""Every series with its video counts, newest first, for the sidebar and the Series page."""
	frappe.only_for("System Manager")
	series = frappe.qb.DocType("BWH Video Series")
	video = frappe.qb.DocType("BWH Video")
	published = Case().when(video.status == "Published", 1).else_(0)
	return (
		frappe.qb.from_(series)
		.left_join(video)
		.on(video.series == series.name)
		.select(
			series.name,
			series.title,
			series.emoji,
			series.summary,
			Count(video.name).as_("video_count"),
			Coalesce(Sum(published), 0).as_("published_count"),
		)
		.groupby(series.name)
		.orderby(series.creation, order=frappe.qb.desc)
		.run(as_dict=True)
	)


@frappe.whitelist(methods=["GET"])
def get_attachment_counts() -> dict[str, int]:
	"""How many files and links each video has, by video name. Videos with none are left out."""
	frappe.only_for("System Manager")
	rows = frappe.get_all(
		"File",
		filters={"attached_to_doctype": "BWH Video"},
		fields=["attached_to_name", {"COUNT": "*", "as": "count"}],
		group_by="attached_to_name",
	)
	return {row.attached_to_name: row.count for row in rows}


@frappe.whitelist(methods=["POST"])
def move_video(video: int, position: int) -> list[int]:
	"""Move a video to a position in its series. Returns the video names in the new order."""
	frappe.only_for("System Manager")
	series = frappe.db.get_value("BWH Video", video, "series")
	if not series:
		frappe.throw(frappe._("Only a video in a series has a position"))
	return SeriesOrder(series).move(int(video), int(position))
