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


@frappe.whitelist()
def get_library() -> str | None:
	"""The shapes saved to the Excalidraw library, as JSON. Every canvas shares them."""
	frappe.only_for("System Manager")
	return frappe.db.get_single_value("BWH Canvas Library", "items")


@frappe.whitelist(methods=["POST"])
def save_library(items: str):
	frappe.only_for("System Manager")
	library = frappe.get_single("BWH Canvas Library")
	library.items = items
	library.save()
