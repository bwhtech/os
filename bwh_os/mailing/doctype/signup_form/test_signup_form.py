# Copyright (c) 2026, BWH and contributors
# For license information, please see license.txt

import frappe
from frappe.tests import IntegrationTestCase

from bwh_os.mailing.api import SIGNUP_API_ROLE, subscribe
from bwh_os.mailing.doctype.signup_form.signup_form import FormClosedError
from bwh_os.mailing.doctype.subscriber_tag.subscriber_tag import SubscriberTag


class IntegrationTestSignupForm(IntegrationTestCase):
	def setUp(self):
		# Records live for the whole class, so reset what a test may have changed.
		self.form = make_form("test-blog-post", tags=["test-blog"])
		self.form.db_set("is_active", 1)

	def tearDown(self):
		frappe.set_user("Administrator")

	def test_new_signup_records_source_and_tags(self):
		reply = subscribe(
			"test-blog-post",
			"New.Reader@example.com",
			first_name="Ana",
			source_url="https://bwh.tech/blog/x",
			utm={"utm_source": "youtube"},
			consent_ip="203.0.113.7",
		)

		self.assertEqual(reply, {"message": self.form.success_message})
		subscriber = frappe.get_doc("Subscriber", "new.reader@example.com")
		self.assertEqual(subscriber.status, "Active")
		self.assertEqual(subscriber.source_form, "test-blog-post")
		self.assertEqual(subscriber.first_name, "Ana")
		self.assertEqual(subscriber.consent_ip, "203.0.113.7")
		self.assertEqual(frappe.parse_json(subscriber.utm), {"utm_source": "youtube"})
		self.assertEqual([row.tag for row in subscriber.tags], ["test-blog"])

	def test_known_email_gets_tags_and_keeps_its_source(self):
		make_form("test-home", tags=["test-home"])
		subscribe("test-home", "known@example.com")

		subscribe("test-blog-post", "known@example.com")

		subscriber = frappe.get_doc("Subscriber", "known@example.com")
		self.assertEqual(subscriber.source_form, "test-home")
		self.assertEqual(sorted(row.tag for row in subscriber.tags), ["test-blog", "test-home"])

	def test_unsubscribed_email_is_active_again_after_signup(self):
		subscribe("test-blog-post", "returning@example.com")
		frappe.db.set_value("Subscriber", "returning@example.com", "status", "Unsubscribed")

		subscribe("test-blog-post", "returning@example.com")

		self.assertEqual(frappe.db.get_value("Subscriber", "returning@example.com", "status"), "Active")

	def test_closed_form_rejects_signups(self):
		self.form.db_set("is_active", 0)

		with self.assertRaises(FormClosedError):
			subscribe("test-blog-post", "late@example.com")

	def test_form_id_must_be_a_slug(self):
		with self.assertRaises(frappe.ValidationError):
			make_form("Bad Form_ID")

	def test_signup_api_user_can_subscribe_but_not_read_forms(self):
		api_user = make_api_user()
		frappe.set_user(api_user)

		subscribe("test-blog-post", "via-api@example.com")

		self.assertTrue(frappe.db.exists("Subscriber", "via-api@example.com"))
		self.assertFalse(frappe.has_permission("Signup Form", "read"))

	def test_user_without_role_cannot_subscribe(self):
		frappe.set_user("Guest")

		with self.assertRaises(frappe.PermissionError):
			subscribe("test-blog-post", "guest@example.com")


def make_form(form_id: str, tags: list[str] | None = None):
	if frappe.db.exists("Signup Form", form_id):
		return frappe.get_doc("Signup Form", form_id)
	for tag in tags or []:
		SubscriberTag.ensure(tag)
	return frappe.get_doc(
		{
			"doctype": "Signup Form",
			"title": form_id,
			"form_id": form_id,
			"tags": [{"tag": tag} for tag in tags or []],
		}
	).insert()


def make_api_user() -> str:
	email = "test-signup-api@example.com"
	if not frappe.db.exists("User", email):
		user = frappe.get_doc({"doctype": "User", "email": email, "first_name": "Signup API", "send_welcome_email": 0})
		user.append("roles", {"role": SIGNUP_API_ROLE})
		user.insert(ignore_permissions=True)
	return email
