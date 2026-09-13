"""Send a newsletter issue to its audience. See "Sending" in specs/01-email-list.md."""

from datetime import timedelta
from math import ceil

import frappe
from frappe import _
from frappe.query_builder.functions import Count
from frappe.utils import add_to_date, get_datetime, now_datetime
from frappe.utils.background_jobs import is_job_enqueued

from bwh_os.mailing.emails import list_headers

# Rows between commits in the send job
COMMIT_EVERY = 100
# Email Queue records per query in the sync job
SYNC_CHUNK = 1000
DEFAULT_HOURLY_LIMIT = 500
DELIVERY_STATUSES = ("Queued", "Sent", "Failed", "Skipped")


class Audience:
	"""The subscribers an issue goes to: all Active ones, or Active ones with any of the tags."""

	def __init__(self, audience: str, tags: list[str], hourly_limit: int):
		self.audience = audience
		self.tags = tags
		self.hourly_limit = hourly_limit or DEFAULT_HOURLY_LIMIT

	@classmethod
	def of(cls, issue) -> "Audience":
		return cls(issue.audience, [row.tag for row in issue.tags], issue.hourly_limit)

	def preview(self) -> dict:
		"""What a send would do now: recipient count, people with the tags who are not Active, and the batches."""
		recipients = len(self.subscribers())
		return {
			"recipients": recipients,
			"left_out": self.left_out(),
			"hourly_limit": self.hourly_limit,
			"batches": [
				min(self.hourly_limit, recipients - batch * self.hourly_limit)
				for batch in range(ceil(recipients / self.hourly_limit))
			],
		}

	def subscribers(self) -> list[dict]:
		"""Active subscribers, oldest first, so batch 0 goes to the longest-standing readers."""
		table = frappe.qb.DocType("Subscriber")
		query = self.filter(
			frappe.qb.from_(table).select(table.name, table.email).where(table.status == "Active"), table
		)
		return query.orderby(table.creation).orderby(table.name).run(as_dict=True)

	def left_out(self) -> dict[str, int]:
		"""Subscribers who match the audience but are not Active, by status."""
		table = frappe.qb.DocType("Subscriber")
		query = self.filter(
			frappe.qb.from_(table)
			.select(table.status, Count("*").as_("count"))
			.where(table.status != "Active")
			.groupby(table.status),
			table,
		)
		return {row.status: row.count for row in query.run(as_dict=True)}

	def filter(self, query, table):
		if self.audience != "Tags":
			return query
		item = frappe.qb.DocType("Subscriber Tag Item")
		tagged = (
			frappe.qb.from_(item)
			.select(item.parent)
			.where((item.parenttype == "Subscriber") & item.tag.isin(self.tags or [""]))
		)
		return query.where(table.name.isin(tagged))


class NewsletterSend:
	"""Makes one delivery row per recipient, queues the emails in hourly batches, and follows the queue."""

	def __init__(self, issue):
		self.issue = issue

	@property
	def job_id(self) -> str:
		return f"newsletter_send::{self.issue.name}"

	def start(self):
		"""Check the issue, mark it Sending, and queue the emails in a worker."""
		if self.issue.status != "Draft":
			frappe.throw(_("This newsletter is already {0}").format(_(self.issue.status).lower()))
		if not self.issue.content_html:
			frappe.throw(_("Write the newsletter before you send it"))
		if self.issue.audience == "Tags" and not self.issue.tags:
			frappe.throw(_("Pick at least one tag, or send to all Active subscribers"))
		if not Audience.of(self.issue).subscribers():
			frappe.throw(_("No Active subscriber is in the audience"))

		self.issue.status = "Sending"
		self.issue.sent_at = now_datetime()
		self.issue.save()
		self.enqueue()

	def enqueue(self):
		frappe.enqueue(
			run_send_job,
			queue="long",
			timeout=60 * 60,
			enqueue_after_commit=True,
			job_id=self.job_id,
			deduplicate=True,
			issue=self.issue.name,
		)

	def run(self):
		"""Safe to run again: rows that exist are not made again, and queued rows are not queued again."""
		self.make_deliveries()
		self.queue_deliveries()
		self.sync()

	def make_deliveries(self):
		if frappe.db.exists("Newsletter Delivery", {"issue": self.issue.name}):
			return

		limit = self.issue.hourly_limit or DEFAULT_HOURLY_LIMIT
		now = now_datetime()
		user = frappe.session.user
		fields = [
			"name",
			"issue",
			"subscriber",
			"email",
			"batch",
			"status",
			"creation",
			"modified",
			"owner",
			"modified_by",
		]
		values = [
			(
				frappe.generate_hash(),
				self.issue.name,
				row.name,
				row.email,
				index // limit,
				"Queued",
				now,
				now,
				user,
				user,
			)
			for index, row in enumerate(Audience.of(self.issue).subscribers())
		]
		frappe.db.bulk_insert("Newsletter Delivery", fields, values, ignore_duplicates=True)
		self.issue.db_set("recipient_count", len(values))
		frappe.db.commit()

	def queue_deliveries(self):
		for index, row in enumerate(self.unqueued_rows(), start=1):
			self.queue(row)
			if index % COMMIT_EVERY == 0:
				frappe.db.commit()
		frappe.db.commit()

	def queue(self, row: dict):
		if row.subscriber_status != "Active":
			set_delivery(
				row.name, status="Skipped", error=_("Subscriber is {0}").format(row.subscriber_status)
			)
			return

		unsubscribe_url = frappe.get_doc("Subscriber", row.subscriber).get_unsubscribe_url()
		queue = frappe.sendmail(
			recipients=[row.email],
			sender=frappe.get_cached_doc("Mailing Settings").get_sender(),
			subject=self.issue.subject,
			message=self.issue.get_email_html(unsubscribe_url),
			# The editor makes a full HTML document. Frappe's wrapper would nest it.
			raw_html=True,
			reference_doctype=self.issue.doctype,
			reference_name=self.issue.name,
			add_unsubscribe_link=0,
			email_headers=list_headers(unsubscribe_url),
			send_after=self.send_after(row.batch),
		)
		if not queue:
			# Frappe drops an address with a global Email Unsubscribe record and raises nothing.
			set_delivery(
				row.name, status="Failed", error=_("Frappe did not queue the email. Check Email Unsubscribe.")
			)
			return
		set_delivery(row.name, email_queue=queue.name, queued_at=now_datetime())

	def send_after(self, batch: int):
		if not batch:
			return None
		return add_to_date(get_datetime(self.issue.sent_at), hours=batch)

	def unqueued_rows(self) -> list[dict]:
		delivery = frappe.qb.DocType("Newsletter Delivery")
		subscriber = frappe.qb.DocType("Subscriber")
		return (
			frappe.qb.from_(delivery)
			.join(subscriber)
			.on(subscriber.name == delivery.subscriber)
			.select(
				delivery.name,
				delivery.subscriber,
				delivery.email,
				delivery.batch,
				subscriber.status.as_("subscriber_status"),
			)
			.where(
				(delivery.issue == self.issue.name)
				& (delivery.status == "Queued")
				& (delivery.email_queue.isnull() | (delivery.email_queue == ""))
			)
			.orderby(delivery.batch)
			.orderby(delivery.creation)
			.run(as_dict=True)
		)

	def sync(self):
		"""Copy the Email Queue status to the rows, update the counts, and finish the issue when no row waits."""
		self.copy_queue_status()
		counts = self.status_counts()
		self.issue.db_set(
			{
				"sent_count": counts.get("Sent", 0),
				"failed_count": counts.get("Failed", 0),
				"skipped_count": counts.get("Skipped", 0),
			}
		)

		made = sum(counts.values())
		if made and not counts.get("Queued"):
			self.issue.db_set(
				{"status": "Sent" if counts.get("Sent") else "Failed", "completed_at": now_datetime()}
			)
		elif (not made or self.unqueued_rows()) and not is_job_enqueued(self.job_id):
			# The worker stopped before it queued every row.
			self.enqueue()

	def copy_queue_status(self):
		rows = frappe.get_all(
			"Newsletter Delivery",
			filters={"issue": self.issue.name, "status": "Queued", "email_queue": ("is", "set")},
			fields=["name", "email_queue"],
		)
		for start in range(0, len(rows), SYNC_CHUNK):
			chunk = rows[start : start + SYNC_CHUNK]
			queues = {
				queue.name: queue
				for queue in frappe.get_all(
					"Email Queue",
					filters={
						"name": ("in", [row.email_queue for row in chunk]),
						"status": ("in", ("Sent", "Error")),
					},
					fields=["name", "status", "error"],
				)
			}
			for row in chunk:
				if queue := queues.get(row.email_queue):
					if queue.status == "Sent":
						set_delivery(row.name, status="Sent")
					else:
						set_delivery(
							row.name, status="Failed", error=frappe.utils.strip_html(queue.error or "")[:1000]
						)

	def status_counts(self) -> dict[str, int]:
		rows = frappe.get_all(
			"Newsletter Delivery",
			filters={"issue": self.issue.name},
			fields=["status", {"COUNT": "*", "as": "count"}],
			group_by="status",
		)
		return {row.status: row["count"] for row in rows}

	def progress(self) -> dict:
		"""Delivery counts in total and per batch, for the report tab."""
		table = frappe.qb.DocType("Newsletter Delivery")
		rows = (
			frappe.qb.from_(table)
			.select(table.batch, table.status, Count("*").as_("count"))
			.where(table.issue == self.issue.name)
			.groupby(table.batch, table.status)
			.run(as_dict=True)
		)
		sent_at = get_datetime(self.issue.sent_at) if self.issue.sent_at else None
		batches: dict[int, dict] = {}
		for row in rows:
			batch = batches.setdefault(row.batch, {"batch": row.batch, **dict.fromkeys(DELIVERY_STATUSES, 0)})
			batch["sends_at"] = str(sent_at + timedelta(hours=row.batch)) if sent_at else None
			batch[row.status] = row["count"]
		return {
			"counts": {
				status: sum(batch[status] for batch in batches.values()) for status in DELIVERY_STATUSES
			},
			"batches": [batches[key] for key in sorted(batches)],
		}


def set_delivery(name: str, **values):
	frappe.db.set_value("Newsletter Delivery", name, values, update_modified=False)


def run_send_job(issue: str):
	NewsletterSend(frappe.get_doc("Newsletter Issue", issue)).run()


def sync_sending_issues():
	"""Scheduler job. Follows every issue that is Sending."""
	for name in frappe.get_all("Newsletter Issue", filters={"status": "Sending"}, pluck="name"):
		NewsletterSend(frappe.get_doc("Newsletter Issue", name)).sync()
		frappe.db.commit()
