# Copyright (c) 2026, BWH and contributors
# For license information, please see license.txt

from unittest.mock import patch

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_to_date, now_datetime

from bwh_os.mailing.api import add_subscriber, schedule_newsletter, unschedule_newsletter
from bwh_os.mailing.doctype.lead_magnet.test_lead_magnet import use_test_email_account
from bwh_os.mailing.doctype.newsletter_issue.test_newsletter_issue import make_issue
from bwh_os.mailing.doctype.subscriber_tag.subscriber_tag import SubscriberTag
from bwh_os.mailing.newsletter_schedule import send_due_issues


class IntegrationTestNewsletterSchedule(IntegrationTestCase):
	def setUp(self):
		use_test_email_account()
		self.commit = patch.object(frappe.db, "commit")
		self.commit.start()
		self.enqueue = patch("bwh_os.mailing.newsletter_send.frappe.enqueue")
		self.enqueue.start()
		self.tag = SubscriberTag.ensure(f"test-schedule-{frappe.generate_hash(length=6)}")

	def tearDown(self):
		self.enqueue.stop()
		self.commit.stop()
		frappe.set_user("Administrator")

	def test_scheduled_issue_sends_when_due(self):
		self.add_reader()
		issue = self.issue_for_tag()

		self.assertEqual(schedule_newsletter(issue.name, str(in_minutes(5))), "Scheduled")
		send_due_issues()
		self.assertEqual(self.status(issue), "Scheduled")

		frappe.db.set_value("Newsletter Issue", issue.name, "scheduled_at", in_minutes(-1))
		send_due_issues()

		issue.reload()
		self.assertEqual(issue.status, "Sending")
		self.assertTrue(issue.sent_at)

	def test_schedule_needs_a_future_time_and_a_sendable_issue(self):
		issue = self.issue_for_tag()
		with self.assertRaises(frappe.ValidationError):
			schedule_newsletter(issue.name, str(in_minutes(5)))

		self.add_reader()
		with self.assertRaises(frappe.ValidationError):
			schedule_newsletter(issue.name, str(in_minutes(-5)))
		self.assertEqual(self.status(issue), "Draft")

	def test_scheduled_issue_is_locked_until_unscheduled(self):
		self.add_reader()
		issue = self.issue_for_tag()
		schedule_newsletter(issue.name, str(in_minutes(5)))

		issue.reload()
		issue.subject = "Changed"
		with self.assertRaises(frappe.ValidationError):
			issue.save()

		self.assertEqual(unschedule_newsletter(issue.name), "Draft")
		issue.reload()
		self.assertIsNone(issue.scheduled_at)
		issue.subject = "Changed"
		issue.save()

	def test_due_issue_with_no_audience_left_fails_once(self):
		reader = self.add_reader()
		issue = self.issue_for_tag()
		schedule_newsletter(issue.name, str(in_minutes(5)))
		frappe.db.set_value("Subscriber", reader, "status", "Unsubscribed")
		frappe.db.set_value("Newsletter Issue", issue.name, "scheduled_at", in_minutes(-1))

		send_due_issues()

		issue.reload()
		self.assertEqual(issue.status, "Failed")
		self.assertIsNone(issue.sent_at)
		self.assertTrue(
			frappe.db.exists("Error Log", {"reference_doctype": "Newsletter Issue", "reference_name": issue.name})
		)

	def test_only_system_manager_can_schedule(self):
		issue = self.issue_for_tag()
		frappe.set_user("Guest")

		with self.assertRaises(frappe.PermissionError):
			schedule_newsletter(issue.name, str(in_minutes(5)))

	def add_reader(self) -> str:
		return add_subscriber(f"reader-{self.tag}@example.com", tags=[self.tag])

	def issue_for_tag(self):
		issue = make_issue()
		return issue.update({"audience": "Tags", "tags": [{"tag": self.tag}]}).save()

	def status(self, issue) -> str:
		return frappe.db.get_value("Newsletter Issue", issue.name, "status")


def in_minutes(minutes: int):
	return add_to_date(now_datetime(), minutes=minutes)
