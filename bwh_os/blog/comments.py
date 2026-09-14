"""The public thread of a post, in the shape the blog uses. The OS page reads the doctypes directly."""

from zoneinfo import ZoneInfo

import frappe
from frappe.utils import get_datetime, get_system_timezone

# The blog shows at most this many comments on a post.
PUBLIC_LIMIT = 200


def public_comments(post_id: str, comment: int | None = None) -> list[dict]:
	"""Visible comments of a post, oldest first, in the shape the blog uses."""
	filters = {"post": post_id, "hidden": 0}
	if comment:
		filters["name"] = comment
	rows = frappe.get_all(
		"BWH Blog Comment",
		filters=filters,
		fields=["name", "commenter_name", "email", "body", "creation"],
		order_by="creation asc, name asc",
		limit=PUBLIC_LIMIT,
	)
	return [
		{
			"id": row.name,
			"name": row.commenter_name,
			"email": row.email,
			"body": row.body,
			"created_at": unix_time(row.creation),
		}
		for row in rows
	]


def unix_time(value) -> int:
	"""Frappe stores times without a zone, in the system time zone."""
	moment = get_datetime(value).replace(tzinfo=ZoneInfo(get_system_timezone()))
	return int(moment.timestamp())
