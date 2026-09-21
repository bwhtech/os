"""Canvases for the OS."""

import frappe


@frappe.whitelist(methods=["POST"])
def get_video_canvas(video: str) -> str:
	"""The name of the canvas of a video. The first call makes it, named after the video."""
	frappe.only_for("System Manager")
	if name := frappe.db.get_value("BWH Canvas", {"video": video}):
		return name
	title = frappe.db.get_value("BWH Video", video, "title")
	if title is None:
		frappe.throw(frappe._("Video {0} not found").format(video), frappe.DoesNotExistError)
	return frappe.get_doc({"doctype": "BWH Canvas", "title": title, "video": video}).insert().name
