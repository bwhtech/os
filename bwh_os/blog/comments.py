"""Reads of blog comments: the public thread of a post, and the feed for the OS Comments page."""

from zoneinfo import ZoneInfo

import frappe
from frappe.utils import get_datetime, get_system_timezone

from bwh_os.blog.posts import post_url

# The blog shows at most this many comments on a post.
PUBLIC_LIMIT = 200
# The OS page loads all comments at once. Above this, it shows only the newest.
FEED_LIMIT = 2000


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


def get_comment_feed() -> dict:
	# One more row than the limit tells us that there are more comments.
	comments = frappe.get_all(
		"BWH Blog Comment",
		fields=["name", "post", "commenter_name", "email", "body", "creation", "hidden"],
		order_by="creation desc, name desc",
		limit=FEED_LIMIT + 1,
	)
	posts = frappe.get_all("BWH Blog Post", fields=["name", "title", "likes"])
	return {
		"truncated": len(comments) > FEED_LIMIT,
		"posts": group_by_post(comments[:FEED_LIMIT], posts),
	}


def group_by_post(comments: list[dict], posts: list[dict]) -> list[dict]:
	"""One group for each post that has comments. The comments are newest first, so the groups are too."""
	posts_by_id = {post.name: post for post in posts}
	groups: dict[str, dict] = {}
	for comment in comments:
		post_id = comment.post
		if post_id not in groups:
			post = posts_by_id.get(post_id, {})
			groups[post_id] = {
				"post_id": post_id,
				# The feed had no title when the post was made, for example for a draft.
				"title": post.get("title") or post_id,
				"url": post_url(post_id),
				"likes": post.get("likes", 0),
				"comments": [],
			}
		groups[post_id]["comments"].append(
			{
				"id": comment.name,
				"name": comment.commenter_name,
				"email": comment.email,
				"body": comment.body,
				"created_at": unix_time(comment.creation),
				"hidden": bool(comment.hidden),
			}
		)
	return list(groups.values())


def unix_time(value) -> int:
	"""Frappe stores times without a zone, in the system time zone."""
	moment = get_datetime(value).replace(tzinfo=ZoneInfo(get_system_timezone()))
	return int(moment.timestamp())
