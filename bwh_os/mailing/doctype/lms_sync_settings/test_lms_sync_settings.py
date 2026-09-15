# Copyright (c) 2026, BWH and contributors
# For license information, please see license.txt

from unittest.mock import patch

import frappe
from frappe.tests import IntegrationTestCase

from bwh_os.mailing.api import add_subscriber
from bwh_os.mailing.doctype.subscriber_tag.subscriber_tag import SubscriberTag
from bwh_os.mailing.lms_sync import LMSClient


class IntegrationTestLMSSyncSettings(IntegrationTestCase):
	def setUp(self):
		self.settings = frappe.get_single("LMS Sync Settings")
		self.settings.update(
			{
				"enabled": 1,
				"site_url": "https://lms.example.com/",
				"api_key": "key",
				"api_secret": "secret",
				"users_synced_until": None,
				"enrollments_synced_until": None,
				"user_tags": [{"tag": SubscriberTag.ensure("test-lms-user")}],
				"enrollment_tags": [{"tag": SubscriberTag.ensure("test-lms-paid")}],
			}
		)
		self.settings.save()
		self.lms = {"User": [], "LMS Batch Enrollment": []}

	def sync(self) -> dict:
		def get_page(client, doctype, fields, filters, start):
			self.requests.append({"doctype": doctype, "filters": filters})
			return self.lms[doctype][start:]

		self.requests = []
		with patch.object(LMSClient, "get_page", get_page):
			return self.settings.sync()

	def test_new_users_join_as_active_with_the_user_tags(self):
		self.lms["User"] = [user("New.Learner@example.com", "Asha", "2026-09-15 10:00:00")]

		result = self.sync()

		subscriber = frappe.get_doc("Subscriber", "new.learner@example.com")
		self.assertEqual(subscriber.status, "Active")
		self.assertEqual(subscriber.first_name, "Asha")
		self.assertEqual([row.tag for row in subscriber.tags], ["test-lms-user"])
		self.assertEqual(result["added"], 1)
		self.assertEqual(self.settings.last_sync_status, "Success")

	def test_known_emails_are_skipped_and_stay_unsubscribed(self):
		name = add_subscriber("gone@example.com")
		frappe.db.set_value("Subscriber", name, "status", "Unsubscribed")
		self.lms["User"] = [
			user("gone@example.com", "Gone", "2026-09-15 10:00:00"),
			user("not-an-email", "X", "2026-09-15 10:01:00"),
		]

		result = self.sync()

		self.assertEqual(result["skipped"], 2)
		self.assertEqual(frappe.db.get_value("Subscriber", name, "status"), "Unsubscribed")
		self.assertEqual(frappe.get_doc("Subscriber", name).tags, [])

	def test_cursor_moves_to_the_newest_user_and_filters_the_next_sync(self):
		self.lms["User"] = [
			user("first@example.com", "A", "2026-09-15 09:00:00"),
			user("second@example.com", "B", "2026-09-15 11:30:00"),
		]
		self.sync()
		self.assertEqual(
			str(frappe.db.get_single_value("LMS Sync Settings", "users_synced_until")), "2026-09-15 11:30:00"
		)

		self.lms["User"] = []
		self.sync()

		self.assertIn(["creation", ">", "2026-09-15 11:30:00"], self.requests[0]["filters"])

	def test_enrollees_on_the_list_get_the_enrollment_tags(self):
		add_subscriber("enrolled@example.com", tags=["test-lms-user"])
		self.lms["LMS Batch Enrollment"] = [
			{"member": "enrolled@example.com", "creation": "2026-09-15 12:00:00"},
			{"member": "not-on-list@example.com", "creation": "2026-09-15 12:05:00"},
		]

		result = self.sync()

		subscriber = frappe.get_doc("Subscriber", "enrolled@example.com")
		self.assertEqual([row.tag for row in subscriber.tags], ["test-lms-user", "test-lms-paid"])
		self.assertFalse(frappe.db.exists("Subscriber", "not-on-list@example.com"))
		self.assertEqual(result["tagged"], 1)

	def test_failed_sync_keeps_the_cursor_and_records_the_error(self):
		self.settings.db_set("users_synced_until", "2026-09-01 00:00:00")
		self.lms["User"] = [user("partial@example.com", "P", "2026-09-15 10:00:00")]

		def fail(*args):
			raise frappe.ValidationError("LMS is down")

		with patch("bwh_os.mailing.lms_sync.LMSSync.sync_enrollments", fail):
			result = self.sync()

		self.assertEqual(result["status"], "Failed")
		self.assertFalse(frappe.db.exists("Subscriber", "partial@example.com"))
		saved = frappe.get_single("LMS Sync Settings")
		self.assertEqual(str(saved.users_synced_until), "2026-09-01 00:00:00")
		self.assertEqual(saved.last_sync_status, "Failed")
		self.assertIn("LMS is down", saved.last_sync_message)


def user(email: str, first_name: str, creation: str) -> dict:
	return {"name": email, "first_name": first_name, "creation": creation}
