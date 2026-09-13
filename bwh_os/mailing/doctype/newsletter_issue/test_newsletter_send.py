# Copyright (c) 2026, BWH and contributors
# For license information, please see license.txt

from unittest.mock import patch

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_to_date, get_datetime

from bwh_os.mailing.api import (
	add_subscriber,
	get_newsletter_audience,
	get_newsletter_progress,
	send_newsletter,
)
from bwh_os.mailing.doctype.lead_magnet.test_lead_magnet import last_email_to, use_test_email_account
from bwh_os.mailing.doctype.newsletter_issue.test_newsletter_issue import make_issue
from bwh_os.mailing.doctype.subscriber_tag.subscriber_tag import SubscriberTag
from bwh_os.mailing.newsletter_send import NewsletterSend, run_send_job, sync_sending_issues


class IntegrationTestNewsletterSend(IntegrationTestCase):
	def setUp(self):
		use_test_email_account()
		# The send job commits in batches. Keep each test's rows out of the other tests.
		self.commit = patch.object(frappe.db, "commit")
		self.commit.start()
		self.tag = SubscriberTag.ensure(f"test-send-{frappe.generate_hash(length=6)}")

	def tearDown(self):
		self.commit.stop()
		frappe.set_user("Administrator")

	def test_new_issue_copies_hourly_limit_from_settings(self):
		frappe.get_doc("Mailing Settings").update({"default_hourly_limit": 250}).save()

		self.assertEqual(make_issue().hourly_limit, 250)

	def test_audience_counts_active_subscribers_with_the_tags(self):
		self.add_readers(3)
		unsubscribed = self.add_readers(1, prefix="gone")[0]
		frappe.db.set_value("Subscriber", unsubscribed, "status", "Unsubscribed")
		add_subscriber(f"untagged-{self.tag}@example.com")

		preview = get_newsletter_audience("Tags", [self.tag], hourly_limit=2)

		self.assertEqual(preview["recipients"], 3)
		self.assertEqual(preview["left_out"], {"Unsubscribed": 1})
		self.assertEqual(preview["batches"], [2, 1])

	def test_send_makes_a_delivery_per_reader_in_hourly_batches(self):
		readers = self.add_readers(3)
		issue = self.issue_for_tag(hourly_limit=2)

		with patch("bwh_os.mailing.newsletter_send.frappe.enqueue") as enqueue:
			self.assertEqual(send_newsletter(issue.name), "Sending")
		self.assertEqual(enqueue.call_args.kwargs["job_id"], f"newsletter_send::{issue.name}")

		run_send_job(issue.name)

		issue.reload()
		self.assertEqual(issue.recipient_count, 3)
		deliveries = self.deliveries(issue)
		self.assertEqual(sorted(row.email for row in deliveries), sorted(readers))
		self.assertEqual([row.batch for row in deliveries], [0, 0, 1])
		self.assertTrue(all(row.email_queue for row in deliveries))

		send_after = [frappe.db.get_value("Email Queue", row.email_queue, "send_after") for row in deliveries]
		self.assertIsNone(send_after[0])
		self.assertEqual(get_datetime(send_after[2]), add_to_date(get_datetime(issue.sent_at), hours=1))

		email = last_email_to(deliveries[0].email)
		self.assertEqual(email["Subject"], "Issue #1")
		self.assertIn("List-Unsubscribe", email)
		token = frappe.db.get_value("Subscriber", deliveries[0].email, "token")
		self.assertIn(token, email.get_body(("html",)).get_content())

	def test_each_reader_gets_their_own_first_name(self):
		reader = add_subscriber(f"named-{self.tag}@example.com", first_name="Ana", tags=[self.tag])
		issue = self.issue_for_tag()
		issue.update({"subject": "For {{ first_name }}", "content_html": "<p>Hi {{ first_name }}</p>"}).save()

		run_send_job(self.start(issue).name)

		email = last_email_to(reader)
		self.assertEqual(email["Subject"], "For Ana")
		self.assertIn("Hi Ana</p>", email.get_body(("html",)).get_content())

	def test_running_the_job_again_sends_nothing_twice(self):
		self.add_readers(2)
		issue = self.start(self.issue_for_tag())

		run_send_job(issue.name)
		run_send_job(issue.name)

		self.assertEqual(len(self.deliveries(issue)), 2)
		queues = {row.email_queue for row in self.deliveries(issue)}
		self.assertEqual(len(queues), 2)

	def test_reader_who_unsubscribes_before_queueing_is_skipped(self):
		readers = self.add_readers(2)
		issue = self.start(self.issue_for_tag())
		send = NewsletterSend(issue)
		send.make_deliveries()
		frappe.db.set_value("Subscriber", readers[1], "status", "Unsubscribed")

		send.queue_deliveries()

		statuses = {row.email: row.status for row in self.deliveries(issue)}
		self.assertEqual(statuses, {readers[0]: "Queued", readers[1]: "Skipped"})

	def test_sync_marks_issue_sent_when_queue_is_done(self):
		self.add_readers(2)
		issue = self.start(self.issue_for_tag())
		run_send_job(issue.name)
		first, second = self.deliveries(issue)

		frappe.db.set_value("Email Queue", first.email_queue, "status", "Sent")
		sync_sending_issues()
		self.assertEqual(frappe.db.get_value("Newsletter Issue", issue.name, "status"), "Sending")

		frappe.db.set_value(
			"Email Queue", second.email_queue, {"status": "Error", "error": "<b>SMTP down</b>"}
		)
		sync_sending_issues()

		issue.reload()
		self.assertEqual(issue.status, "Sent")
		self.assertEqual((issue.sent_count, issue.failed_count), (1, 1))
		self.assertTrue(issue.completed_at)
		self.assertEqual(frappe.db.get_value("Newsletter Delivery", second.name, "error"), "SMTP down")

		progress = get_newsletter_progress(issue.name)
		self.assertEqual(progress["counts"], {"Queued": 0, "Sent": 1, "Failed": 1, "Skipped": 0})
		self.assertEqual(progress["batches"][0]["Sent"], 1)

	def test_issue_fails_when_no_email_goes_out(self):
		self.add_readers(1)
		issue = self.start(self.issue_for_tag())
		run_send_job(issue.name)
		frappe.db.set_value("Email Queue", self.deliveries(issue)[0].email_queue, "status", "Error")

		sync_sending_issues()

		self.assertEqual(frappe.db.get_value("Newsletter Issue", issue.name, "status"), "Failed")

	def test_issue_cannot_be_sent_twice_or_changed_after_send(self):
		self.add_readers(1)
		issue = self.start(self.issue_for_tag())

		with self.assertRaises(frappe.ValidationError):
			send_newsletter(issue.name)
		issue.reload()
		issue.subject = "Changed"
		with self.assertRaises(frappe.ValidationError):
			issue.save()

	def test_send_needs_content_and_an_audience(self):
		with self.assertRaises(frappe.ValidationError):
			send_newsletter(self.issue_for_tag().name)

		self.add_readers(1)
		issue = make_issue(content_html="")
		issue.update({"audience": "Tags", "tags": [{"tag": self.tag}]}).save()
		with self.assertRaises(frappe.ValidationError):
			send_newsletter(issue.name)

	def test_only_system_manager_can_send(self):
		issue = self.issue_for_tag()
		frappe.set_user("Guest")

		with self.assertRaises(frappe.PermissionError):
			send_newsletter(issue.name)

	def add_readers(self, count: int, prefix: str = "reader") -> list[str]:
		return [
			add_subscriber(f"{prefix}{index}-{self.tag}@example.com", tags=[self.tag])
			for index in range(count)
		]

	def issue_for_tag(self, hourly_limit: int = 500):
		issue = make_issue()
		issue.update({"audience": "Tags", "tags": [{"tag": self.tag}], "hourly_limit": hourly_limit})
		return issue.save()

	def start(self, issue):
		with patch("bwh_os.mailing.newsletter_send.frappe.enqueue"):
			send_newsletter(issue.name)
		issue.reload()
		return issue

	def deliveries(self, issue):
		return frappe.get_all(
			"Newsletter Delivery",
			filters={"issue": issue.name},
			fields=["name", "email", "batch", "status", "email_queue"],
			order_by="batch asc, creation asc",
		)
