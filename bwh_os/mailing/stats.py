"""Counts for the email list dashboard and the number cards on detail pages."""

from datetime import date, timedelta

import frappe
from frappe.query_builder.functions import Count, Date
from frappe.utils import getdate, nowdate

WEEKS = 12
PERIOD_DAYS = 30


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
	}


def signups_by_form() -> list[dict]:
	"""Subscriber count per signup form, biggest first. Subscribers with no form are added by hand or imported."""
	titles = dict(frappe.get_all("Signup Form", fields=["name", "title"], as_list=True))
	rows = [
		{
			"form": titles.get(row["value"], row["value"]) if row["value"] else "Added or imported",
			"count": row["count"],
		}
		for row in count_grouped("Subscriber", "source_form")
	]
	return sorted(rows, key=lambda row: row["count"], reverse=True)


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
