"""OS methods for the blog. Each one reads or writes the Turso database live. See specs/02-blog.md."""

import frappe

from bwh_os.blog.comments import CommentFeed
from bwh_os.blog.turso import Turso, TursoNotConfiguredError


@frappe.whitelist(methods=["GET"])
def get_comments() -> dict:
	"""All comments, newest first, grouped by post. Only `configured: false` before setup."""
	frappe.only_for("System Manager")
	try:
		turso = Turso.from_settings()
	except TursoNotConfiguredError:
		return {"configured": False}
	return {"configured": True, **CommentFeed(turso).load()}


@frappe.whitelist(methods=["POST"])
def test_connection() -> str:
	"""Run a query with the saved credentials. Returns the database host."""
	frappe.only_for("System Manager")
	turso = Turso.from_settings()
	turso.query("SELECT 1")
	return turso.host
