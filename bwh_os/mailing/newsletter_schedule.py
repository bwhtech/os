"""Send a newsletter issue at a set time. See slice 9 in specs/01-email-list.md."""

import frappe
from frappe import _
from frappe.utils import get_datetime, now_datetime

from bwh_os.mailing.newsletter_send import NewsletterSend

SAVEPOINT = "newsletter_schedule"


class NewsletterSchedule:
	"""A Scheduled issue is locked like a sent one. Cancel the schedule to edit it again."""

	def __init__(self, issue):
		self.issue = issue

	def schedule(self, at: str):
		if self.issue.status != "Draft":
			frappe.throw(_("Only a draft can be scheduled"))
		at = get_datetime(at)
		if at <= now_datetime():
			frappe.throw(_("Pick a time in the future"))
		NewsletterSend(self.issue).check()

		self.issue.status = "Scheduled"
		self.issue.scheduled_at = at
		self.issue.save()

	def cancel(self):
		if self.issue.status != "Scheduled":
			frappe.throw(_("This newsletter is not scheduled"))
		self.issue.status = "Draft"
		self.issue.scheduled_at = None
		self.issue.save()

	def send(self):
		"""Start the send. If the issue cannot go out any more, it becomes Failed, so the job does not retry it."""
		frappe.db.savepoint(SAVEPOINT)
		try:
			NewsletterSend(self.issue).start()
		except frappe.ValidationError:
			frappe.db.rollback(save_point=SAVEPOINT)
			frappe.log_error(
				title=_("Scheduled newsletter did not send"),
				reference_doctype=self.issue.doctype,
				reference_name=self.issue.name,
			)
			self.issue.db_set({"status": "Failed", "completed_at": now_datetime()})


def send_due_issues():
	"""Scheduler job. Starts every Scheduled issue whose time has come."""
	due = frappe.get_all(
		"Newsletter Issue",
		filters={"status": "Scheduled", "scheduled_at": ("<=", now_datetime())},
		order_by="scheduled_at asc",
		pluck="name",
	)
	for name in due:
		NewsletterSchedule(frappe.get_doc("Newsletter Issue", name)).send()
		frappe.db.commit()
