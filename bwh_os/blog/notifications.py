"""The email that tells you about a new blog comment. See slice 5 in specs/02-blog.md."""

from urllib.parse import urlencode

import frappe
from frappe import _
from frappe.utils import get_url

TEMPLATE = "bwh_os/templates/emails/blog_comment.html"
BLOG_URL = "https://bwh.tech/blog"


def notify_new_comment(comment):
	"""Queue the email if notifications are on in Mailing Settings. A failure never blocks the comment."""
	settings = frappe.get_cached_doc("Mailing Settings")
	if not settings.notify_blog_comments or not settings.blog_notification_email:
		return
	try:
		send(comment, settings)
	except Exception:
		frappe.log_error("Could not send the new blog comment email", reference_doctype=comment.doctype)


def send(comment, settings):
	title = frappe.db.get_value("BWH Blog Post", comment.post, "title") or comment.post
	frappe.sendmail(
		recipients=[settings.blog_notification_email],
		sender=settings.get_sender(),
		subject=_("New comment on {0}").format(title),
		message=frappe.render_template(
			TEMPLATE,
			{
				"post_title": title,
				"post_url": f"{BLOG_URL}/{comment.post}/",
				"name": comment.commenter_name,
				"email": comment.email,
				"body": comment.body,
				"moderate_url": get_url(f"/os/blog/comments?{urlencode({'post': comment.post})}"),
			},
		),
		reference_doctype=comment.doctype,
		reference_name=comment.name,
	)
