"""Opens, clicks, and unsubscribes of a sent issue, for the Report tab. See slice 10 in specs/01-email-list.md."""

import frappe
from frappe.query_builder.functions import Count
from frappe.utils import add_to_date, get_datetime

HOURS = 72
TOP_LINKS = 10
COUNT_FIELDS = ("sent_count", "opened_count", "clicked_count", "unsubscribed_count")


class NewsletterEngagement:
	def __init__(self, issue):
		self.issue = issue

	def report(self) -> dict:
		return {
			**self.comparison(),
			"funnel": [
				{"stage": "Recipients", "count": self.issue.recipient_count},
				{"stage": "Sent", "count": self.issue.sent_count},
				{"stage": "Opened", "count": self.issue.opened_count},
				{"stage": "Clicked", "count": self.issue.clicked_count},
			],
			"hourly": self.hourly(),
			"top_links": self.top_links(),
		}

	def comparison(self) -> dict:
		"""The rates of this issue and of the issue before it."""
		previous = self.previous_issue()
		return {
			"rates": rates(self.issue),
			"previous": {"name": previous.name, "subject": previous.subject, **rates(previous)}
			if previous
			else None,
		}

	def previous_issue(self):
		"""The last issue that went out before this one."""
		if not self.issue.sent_at:
			return None
		rows = frappe.get_all(
			"Newsletter Issue",
			filters={"status": "Sent", "sent_at": ("<", self.issue.sent_at), "name": ("!=", self.issue.name)},
			fields=["name", "subject", *COUNT_FIELDS],
			order_by="sent_at desc",
			limit=1,
		)
		return rows[0] if rows else None

	def hourly(self) -> list[dict]:
		"""Open and click events in each hour of the first 72 hours, from the start of the send."""
		if not self.issue.sent_at:
			return []
		start = get_datetime(self.issue.sent_at)
		hours = [{"hour": hour, "Open": 0, "Click": 0} for hour in range(HOURS)]
		events = frappe.get_all(
			"Newsletter Event",
			filters={
				"issue": self.issue.name,
				"type": ("in", ("Open", "Click")),
				"creation": ("between", (start, add_to_date(start, hours=HOURS))),
			},
			fields=["type", "creation"],
		)
		for event in events:
			hour = int((get_datetime(event.creation) - start).total_seconds() // 3600)
			if 0 <= hour < HOURS:
				hours[hour][event.type] += 1
		return hours

	def top_links(self) -> list[dict]:
		event = frappe.qb.DocType("Newsletter Event")
		return (
			frappe.qb.from_(event)
			.select(
				event.url,
				Count("*").as_("clicks"),
				Count(event.delivery).distinct().as_("readers"),
			)
			.where((event.issue == self.issue.name) & (event.type == "Click"))
			.groupby(event.url)
			.orderby(Count("*"), order=frappe.qb.desc)
			.limit(TOP_LINKS)
			.run(as_dict=True)
		)


def rates(issue) -> dict:
	"""Open and click rates are shares of the emails sent, from 0 to 100."""
	sent = issue.sent_count or 0
	return {
		"open_rate": percent(issue.opened_count, sent),
		"click_rate": percent(issue.clicked_count, sent),
		"unsubscribes": issue.unsubscribed_count or 0,
	}


def percent(count: int | None, total: int) -> float | None:
	if not total:
		return None
	return round((count or 0) * 100 / total, 1)
