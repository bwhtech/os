# Copyright (c) 2026, BWH and contributors
# For license information, please see license.txt

import frappe
from frappe.tests import IntegrationTestCase

from bwh_os.mailing.api import add_subscriber


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
