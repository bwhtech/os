# Copyright (c) 2026, BWH and contributors
# For license information, please see license.txt

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import now_datetime

from bwh_os.mailing.api import add_subscriber, delete_subscribers, set_subscriber_status
from bwh_os.mailing.doctype.lead_magnet.test_lead_magnet import make_lead_magnet


class IntegrationTestSubscriber(IntegrationTestCase):
	def test_email_is_normalized_and_used_as_name(self):
		name = add_subscriber("  Reader@Example.COM ")

		self.assertEqual(name, "reader@example.com")
		subscriber = frappe.get_doc("Subscriber", name)
		self.assertEqual(subscriber.status, "Active")
		self.assertEqual(len(subscriber.token), 32)
		self.assertIsNotNone(subscriber.subscribed_on)

	def test_missing_tags_are_created_once(self):
		name = add_subscriber("tagged@example.com", tags=["test-lms-alumni", "test-lms-alumni", " "])

		subscriber = frappe.get_doc("Subscriber", name)
		self.assertEqual([row.tag for row in subscriber.tags], ["test-lms-alumni"])
		self.assertTrue(frappe.db.exists("Subscriber Tag", "test-lms-alumni"))

	def test_duplicate_email_is_rejected(self):
		add_subscriber("twice@example.com")

		with self.assertRaises(frappe.DuplicateEntryError):
			add_subscriber("TWICE@example.com")

	def test_invalid_email_is_rejected(self):
		with self.assertRaises(frappe.InvalidEmailAddressError):
			add_subscriber("not-an-email")

	def test_bulk_status_change_sets_the_dates(self):
		names = [add_subscriber("bulk-one@example.com"), add_subscriber("bulk-two@example.com")]

		self.assertEqual(set_subscriber_status(names, "Unsubscribed"), 2)
		self.assertEqual(set_subscriber_status(names, "Unsubscribed"), 0)
		for name in names:
			subscriber = frappe.get_doc("Subscriber", name)
			self.assertEqual(subscriber.status, "Unsubscribed")
			self.assertIsNotNone(subscriber.unsubscribed_on)

	def test_bulk_delete_keeps_subscribers_with_history(self):
		plain = add_subscriber("bulk-plain@example.com")
		downloader = add_subscriber("bulk-downloader@example.com")
		frappe.get_doc(
			{
				"doctype": "Lead Magnet Download",
				"lead_magnet": make_lead_magnet().name,
				"subscriber": downloader,
				"downloaded_on": now_datetime(),
			}
		).insert()

		result = delete_subscribers([plain, downloader])

		self.assertEqual(result, {"deleted": [plain], "kept": [downloader]})
		self.assertFalse(frappe.db.exists("Subscriber", plain))
		self.assertTrue(frappe.db.exists("Subscriber", downloader))
