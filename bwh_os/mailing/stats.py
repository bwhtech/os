"""Counts for the email list dashboard and the number cards on detail pages."""

from datetime import date, timedelta

import frappe
from frappe.query_builder.functions import Count, Date
from frappe.utils import getdate, nowdate

from bwh_os.mailing.newsletter_engagement import COUNT_FIELDS, NewsletterEngagement, percent, rates

WEEKS = 12
PERIOD_DAYS = 30
ISSUES = 10


def activity(doctype: str, date_field: str, filters: dict | None = None) -> dict:
	"""All-time total, the last 30 days against the 30 before, and a count per week.

	`weekly` holds one row per week for the last 12 weeks, oldest first. `week` is the Monday.
	"""
	today = getdate(nowdate())
	period_start = today - timedelta(days=PERIOD_DAYS - 1)
	previous_start = period_start - timedelta(days=PERIOD_DAYS)
	first_week = week_start(today) - timedelta(weeks=WEEKS - 1)
	per_day = count_per_day(doctype, date_field, filters, min(first_week, previous_start))

	return {
		"total": frappe.db.count(doctype, filters),
		"last_period": sum_between(per_day, period_start, today),
		"previous_period": sum_between(per_day, previous_start, period_start - timedelta(days=1)),
		"weekly": count_per_week(per_day, first_week),
	}


def list_overview() -> dict:
	"""The numbers behind the dashboard page."""
	return {
		"subscribers": activity("Subscriber", "subscribed_on"),
		"unsubscribes": activity("Subscriber", "unsubscribed_on", {"status": "Unsubscribed"}),
		"downloads": activity("Lead Magnet Download", "downloaded_on"),
		"by_status": count_grouped("Subscriber", "status"),
		"by_form": signups_by_form(),
		"last_issue": last_issue(),
		"issue_rates": issue_rates(),
	}


def signups_by_form() -> list[dict]:
	"""Signups and confirmed signups per signup form, biggest first.

	A single opt-in form confirms on signup, so only a double opt-in form has a confirm rate.
	Subscribers with no form are added by hand or imported.
	"""
	subscriber = frappe.qb.DocType("Subscriber")
	form = frappe.qb.DocType("Signup Form")
	signups = Count("*")
	rows = (
		frappe.qb.from_(subscriber)
		.left_join(form)
		.on(form.name == subscriber.source_form)
		.select(
			subscriber.source_form,
			form.title,
			form.double_opt_in,
			signups.as_("signups"),
			Count(subscriber.confirmed_on).as_("confirmed"),
		)
		.groupby(subscriber.source_form, form.title, form.double_opt_in)
		.orderby(signups, order=frappe.qb.desc)
		.run(as_dict=True)
	)
	return [
		{
			"form": (row.title or row.source_form) if row.source_form else "Added or imported",
			"signups": row.signups,
			"confirmed": row.confirmed,
			"confirm_rate": percent(row.confirmed, row.signups) if row.double_opt_in else None,
		}
		for row in rows
	]


def last_issue() -> dict | None:
	"""The rates of the last sent issue, against the issue before it."""
	name = frappe.db.get_value("Newsletter Issue", {"status": "Sent"}, "name", order_by="sent_at desc")
	if not name:
		return None
	issue = frappe.get_doc("Newsletter Issue", name)
	return {
		"name": issue.name,
		"subject": issue.subject,
		"sent_at": issue.sent_at,
		"recipient_count": issue.recipient_count,
		**NewsletterEngagement(issue).comparison(),
	}


def issue_rates() -> list[dict]:
	"""Open and click rates of the last 10 sent issues, oldest first."""
	issues = frappe.get_all(
		"Newsletter Issue",
		filters={"status": "Sent"},
		fields=["name", "subject", "sent_at", *COUNT_FIELDS],
		order_by="sent_at desc",
		limit=ISSUES,
	)
	return [
		{"name": issue.name, "subject": issue.subject, "sent_at": issue.sent_at, **rates(issue)}
		for issue in reversed(issues)
	]


def count_grouped(doctype: str, field: str) -> list[dict]:
	table = frappe.qb.DocType(doctype)
	return (
		frappe.qb.from_(table)
		.select(table[field].as_("value"), Count("*").as_("count"))
		.groupby(table[field])
		.run(as_dict=True)
	)


def count_per_day(doctype: str, date_field: str, filters: dict | None, since: date) -> dict[date, int]:
	table = frappe.qb.DocType(doctype)
	day = Date(table[date_field])
	query = (
		frappe.qb.from_(table)
		.select(day.as_("day"), Count("*").as_("count"))
		.where(table[date_field] >= since)
		.groupby(day)
	)
	for field, value in (filters or {}).items():
		query = query.where(table[field] == value)
	return {getdate(row.day): row.count for row in query.run(as_dict=True)}


def count_per_week(per_day: dict[date, int], first_week: date) -> list[dict]:
	weeks = [first_week + timedelta(weeks=index) for index in range(WEEKS)]
	counts = dict.fromkeys(weeks, 0)
	for day, count in per_day.items():
		week = week_start(day)
		if week in counts:
			counts[week] += count
	return [{"week": str(week), "count": counts[week]} for week in weeks]


def sum_between(per_day: dict[date, int], start: date, end: date) -> int:
	return sum(count for day, count in per_day.items() if start <= day <= end)


def week_start(day: date) -> date:
	return day - timedelta(days=day.weekday())
