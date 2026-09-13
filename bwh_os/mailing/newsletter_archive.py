"""The public web archive of sent newsletters. See slice 11 in specs/01-email-list.md."""

import frappe
from frappe import _
from frappe.utils import get_url
from frappe.website.page_renderers.base_renderer import BaseRenderer
from frappe.website.utils import cleanup_page_name

ROUTE_PREFIX = "newsletter/"


class NewsletterRoute:
	"""Checks that an issue can go public and gives it a unique slug."""

	def __init__(self, issue):
		self.issue = issue

	def validate(self):
		if not self.issue.is_public:
			return
		if self.issue.status != "Sent":
			frappe.throw(_("Only a sent newsletter can show in the web archive"))
		self.issue.route = self.unique(cleanup_page_name(self.issue.route or self.issue.subject))

	def unique(self, slug: str) -> str:
		slug = slug or self.issue.name
		candidate, number = slug, 1
		while frappe.db.exists("Newsletter Issue", {"route": candidate, "name": ("!=", self.issue.name)}):
			number += 1
			candidate = f"{slug}-{number}"
		return candidate


class NewsletterIssuePage(BaseRenderer):
	"""Serves /newsletter/<route> as the web version of a public sent issue."""

	def __init__(self, path=None, http_status_code=None):
		super().__init__(path=path, http_status_code=http_status_code)
		is_archive_path = self.path.startswith(ROUTE_PREFIX)
		self.issue = find_public_issue(self.path.removeprefix(ROUTE_PREFIX)) if is_archive_path else None

	def can_render(self) -> bool:
		return bool(self.issue)

	def render(self):
		return self.build_response(frappe.get_doc("Newsletter Issue", self.issue).get_web_html())


def find_public_issue(route: str) -> str | None:
	if not route:
		return None
	return frappe.db.get_value("Newsletter Issue", {"route": route, "is_public": 1, "status": "Sent"})


def public_issues() -> list[dict]:
	"""Public sent issues, newest first, for the /newsletter index."""
	issues = frappe.get_all(
		"Newsletter Issue",
		filters={"is_public": 1, "status": "Sent"},
		fields=["subject", "preview_text", "route", "sent_at"],
		order_by="sent_at desc",
	)
	for issue in issues:
		issue.url = get_url(f"/{ROUTE_PREFIX}{issue.route}")
	return issues
