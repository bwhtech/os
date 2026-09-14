"""Numbers for the Blog overview page."""

import frappe
from frappe.query_builder.functions import Count, Sum

from bwh_os.mailing.stats import activity

TOP_POSTS = 10


def blog_overview() -> dict:
	return {
		"comments": activity("BWH Blog Comment", "creation"),
		"hidden": frappe.db.count("BWH Blog Comment", {"hidden": 1}),
		"likes": total_likes(),
		"top_by_comments": top_posts_by_comments(),
		"top_by_likes": top_posts_by_likes(),
	}


def total_likes() -> int:
	post = frappe.qb.DocType("BWH Blog Post")
	return frappe.qb.from_(post).select(Sum(post.likes)).run()[0][0] or 0


def top_posts_by_comments() -> list[dict]:
	"""Posts with the most comments, hidden ones included."""
	comment = frappe.qb.DocType("BWH Blog Comment")
	post = frappe.qb.DocType("BWH Blog Post")
	count = Count(comment.name)
	return (
		frappe.qb.from_(comment)
		.join(post)
		.on(post.name == comment.post)
		.select(post.name.as_("post_id"), post.title, count.as_("count"))
		.groupby(post.name, post.title)
		.orderby(count, order=frappe.qb.desc)
		.limit(TOP_POSTS)
		.run(as_dict=True)
	)


def top_posts_by_likes() -> list[dict]:
	return frappe.get_all(
		"BWH Blog Post",
		filters={"likes": (">", 0)},
		fields=["name as post_id", "title", "likes as count"],
		order_by="likes desc",
		limit=TOP_POSTS,
	)
