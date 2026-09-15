from collections.abc import Iterator
from dataclasses import asdict, dataclass

import frappe
import requests
from frappe import _
from frappe.utils import validate_email_address

from bwh_os.mailing.doctype.subscriber.subscriber import normalize_email

PAGE_SIZE = 500
TIMEOUT_SECONDS = 30
# Frappe makes these users on every site. They are never real people.
BUILT_IN_USERS = ("Administrator", "Guest")


@dataclass
class SyncResult:
	added: int = 0
	# Already on the list, whatever their status. An unsubscribed person stays unsubscribed.
	skipped: int = 0
	failed: int = 0
	tagged: int = 0

	def summary(self) -> str:
		parts = []
		if self.added:
			parts.append(_("Added {0}").format(plural(self.added, "user")))
		if self.tagged:
			parts.append(_("tagged {0}").format(plural(self.tagged, "enrollee")))
		if self.failed:
			parts.append(_("{0} failed").format(self.failed))
		return ", ".join(parts).capitalize() if parts else _("No new users")

	def as_dict(self) -> dict:
		return asdict(self)


class LMSSync:
	"""Add new LMS users to the list, and tag subscribers who enroll in a batch.

	Each part reads only the records created after its cursor, so a subscriber you delete
	does not come back. A cursor moves to the newest record read, not to the current time,
	so records created during a sync are read by the next one.
	"""

	def __init__(self, settings):
		self.settings = settings
		self.client = LMSClient(settings.site_url, settings.api_key, settings.get_password("api_secret"))
		self.result = SyncResult()

	def run(self) -> SyncResult:
		# Users first, so a person who signs up and enrolls on the same day gets both tags.
		self.sync_users()
		self.sync_enrollments()
		return self.result

	def sync_users(self):
		user_tags = [row.tag for row in self.settings.user_tags]
		filters = [
			["user_type", "=", "Website User"],
			["enabled", "=", 1],
			["name", "not in", BUILT_IN_USERS],
		]
		for user in self.client.get_all(
			"User", ["name", "first_name", "creation"], filters, self.settings.users_synced_until
		):
			self.add_user(user, user_tags)
			self.settings.users_synced_until = user["creation"]

	def sync_enrollments(self):
		enrollment_tags = [row.tag for row in self.settings.enrollment_tags]
		for enrollment in self.client.get_all(
			"LMS Batch Enrollment", ["member", "creation"], [], self.settings.enrollments_synced_until
		):
			if enrollment_tags:
				self.tag_enrollee(normalize_email(enrollment["member"]), enrollment_tags)
			self.settings.enrollments_synced_until = enrollment["creation"]

	def add_user(self, user: dict, tags: list[str]):
		email = normalize_email(user["name"])
		if not validate_email_address(email):
			self.result.skipped += 1
		elif frappe.db.exists("Subscriber", email):
			self.result.skipped += 1
		else:
			self.insert_subscriber(email, user.get("first_name"), tags)

	def insert_subscriber(self, email: str, first_name: str | None, tags: list[str]):
		# One bad user must not undo the users before it.
		frappe.db.savepoint("lms_user")
		try:
			subscriber = frappe.new_doc("Subscriber")
			subscriber.email = email
			subscriber.first_name = first_name
			subscriber.status = "Active"
			subscriber.add_tags(tags)
			subscriber.insert(ignore_permissions=True)
		except Exception:
			frappe.db.rollback(save_point="lms_user")
			frappe.log_error(f"LMS sync could not add {email}")
			self.result.failed += 1
		else:
			frappe.db.release_savepoint("lms_user")
			self.result.added += 1

	def tag_enrollee(self, email: str, tags: list[str]):
		# People not on the list are left out on purpose, for example test accounts you deleted.
		if not frappe.db.exists("Subscriber", email):
			return
		subscriber = frappe.get_doc("Subscriber", email)
		before = len(subscriber.tags)
		subscriber.add_tags(tags)
		if len(subscriber.tags) != before:
			subscriber.save(ignore_permissions=True)
			self.result.tagged += 1


class LMSClient:
	"""Reads documents from a Frappe site with an API key."""

	def __init__(self, site_url: str, api_key: str, api_secret: str):
		self.site_url = site_url.rstrip("/")
		self.session = requests.Session()
		self.session.headers["Authorization"] = f"token {api_key}:{api_secret}"

	def get_all(
		self, doctype: str, fields: list[str], filters: list, created_after: str | None
	) -> Iterator[dict]:
		"""Records created after `created_after`, oldest first, one page at a time."""
		if created_after:
			filters = [*filters, ["creation", ">", str(created_after)]]
		start = 0
		while True:
			page = self.get_page(doctype, fields, filters, start)
			yield from page
			if len(page) < PAGE_SIZE:
				return
			start += PAGE_SIZE

	def get_page(self, doctype: str, fields: list[str], filters: list, start: int) -> list[dict]:
		response = self.session.get(
			f"{self.site_url}/api/resource/{doctype}",
			params={
				"fields": frappe.as_json(fields),
				"filters": frappe.as_json(filters),
				"order_by": "creation asc",
				"limit_start": start,
				"limit_page_length": PAGE_SIZE,
			},
			timeout=TIMEOUT_SECONDS,
		)
		if response.status_code in (401, 403):
			frappe.throw(_("LMS rejected the API key. It needs read access to {0}.").format(doctype))
		response.raise_for_status()
		return response.json()["data"]


def sync_daily():
	settings = frappe.get_single("LMS Sync Settings")
	if settings.enabled:
		settings.sync()


def plural(count: int, noun: str) -> str:
	return f"{count} {noun}" if count == 1 else f"{count} {noun}s"
