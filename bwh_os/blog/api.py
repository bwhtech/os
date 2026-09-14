"""Blog likes and comments. The blog's Netlify functions call the website methods with the API key of
the `OS Signup API` user, and pass the reader's IP for the rate limits. See specs/02-blog.md.
"""

import frappe
from frappe import _
from frappe.rate_limiter import rate_limit

from bwh_os.blog.comments import public_comments
from bwh_os.blog.doctype.bwh_blog_post.bwh_blog_post import get_or_create_post
from bwh_os.mailing.api import SIGNUP_API_ROLE

WEBSITE_ROLES = (SIGNUP_API_ROLE, "System Manager")
MINUTE = 60
HOUR = 60 * MINUTE
DAY = 24 * HOUR
# Well above any real thread. Stops a flood on one post.
MAX_COMMENTS_PER_POST = 500
LIKES_PER_POST_PER_DAY = 3


@frappe.whitelist(methods=["GET"])
def get_engagement(post_id: str) -> dict:
	"""The likes and the visible comments of a post. The email is for the avatar color only."""
	frappe.only_for(WEBSITE_ROLES)
	return {
		"likes": frappe.db.get_value("BWH Blog Post", post_id, "likes") or 0,
		"comments": public_comments(post_id),
	}


@frappe.whitelist(methods=["POST"])
@rate_limit(key="ip", limit=3, seconds=10 * MINUTE)
@rate_limit(key="ip", limit=10, seconds=DAY)
def add_comment(post_id: str, name: str, email: str, body: str, ip: str) -> dict:
	"""Publish a comment at once. Returns its id and time."""
	frappe.only_for(WEBSITE_ROLES)
	post = get_or_create_post(post_id)
	if frappe.db.count("BWH Blog Comment", {"post": post.name, "hidden": 0}) >= MAX_COMMENTS_PER_POST:
		frappe.throw(_("This post has too many comments"), frappe.RateLimitExceededError)
	comment = frappe.get_doc(
		{
			"doctype": "BWH Blog Comment",
			"post": post.name,
			"commenter_name": name,
			"email": email,
			"body": body,
		}
	).insert(ignore_permissions=True)
	return public_comments(post.name, comment.name)[0]


@frappe.whitelist(methods=["POST"])
@rate_limit(key="ip", limit=30, seconds=HOUR)
def like_post(post_id: str, ip: str) -> int:
	"""Add a like. There is no unlike, so nobody can drive a count down. Returns the total."""
	frappe.only_for(WEBSITE_ROLES)
	limit_likes_per_post(ip, post_id)
	return get_or_create_post(post_id).add_like()


@frappe.whitelist(methods=["POST"])
def set_hidden(ids: list[int], hidden: bool) -> int:
	"""Hide or unhide comments on the blog. Returns how many comments changed."""
	frappe.only_for("System Manager")
	names = [int(name) for name in ids]
	for name in names:
		# A save, not db.set_value, so the OS page gets the realtime list update.
		comment = frappe.get_doc("BWH Blog Comment", name)
		comment.hidden = int(bool(hidden))
		comment.save()
	return len(names)


@frappe.whitelist(methods=["POST"])
def delete_comments(ids: list[int]) -> int:
	"""Delete comments for good. Returns how many were deleted."""
	frappe.only_for("System Manager")
	names = [int(name) for name in ids]
	for name in names:
		frappe.delete_doc("BWH Blog Comment", name)
	return len(names)


def limit_likes_per_post(ip: str, post_id: str):
	"""`rate_limit` counts by one parameter. Likes also need a count for each IP and post."""
	key = frappe.cache.make_key(f"rl:bwh_blog_like:{ip}:{post_id}")
	if not frappe.cache.get(key):
		frappe.cache.setex(key, DAY, 0)
	if frappe.cache.incrby(key, 1) > LIKES_PER_POST_PER_DAY:
		frappe.throw(_("You liked this post already"), frappe.RateLimitExceededError)
