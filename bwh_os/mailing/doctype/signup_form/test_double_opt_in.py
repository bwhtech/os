# Copyright (c) 2026, BWH and contributors
# For license information, please see license.txt

from urllib.parse import parse_qs, urlparse

import frappe
from frappe.tests import IntegrationTestCase

from bwh_os.mailing.api import confirm_subscription, subscribe
from bwh_os.mailing.doctype.lead_magnet.test_lead_magnet import (
	download_page,
	last_email_to,
	make_lead_magnet,
	use_test_email_account,
)
from bwh_os.mailing.doctype.signup_form.test_signup_form import email_html, make_form


class IntegrationTestDoubleOptIn(IntegrationTestCase):
	def setUp(self):
		use_test_email_account()
		self.lead_magnet = make_lead_magnet()
		self.lead_magnet.db_set(
			{
				"subject": "Your manual",
				"content_html": email_html('<a href="{{ download_url }}">Download</a>'),
			}
		)
		self.form = make_form("test-double-opt-in")
		self.form.db_set(
			{
				"double_opt_in": 1,
				"confirm_subject": "Confirm, {{ first_name }}",
				"confirm_content_html": email_html(
					'<p>One click left.</p><a href="%7B%7B%20confirm_url%20%7D%7D">Confirm</a>'
				),
				"lead_magnet": self.lead_magnet.name,
			}
		)
		frappe.local.response = frappe._dict()

	def test_signup_is_pending_and_gets_only_the_confirm_email(self):
		subscribe("test-double-opt-in", "pending@example.com", first_name="Ana")

		subscriber = frappe.get_doc("Subscriber", "pending@example.com")
		self.assertEqual(subscriber.status, "Pending")
		self.assertIsNone(subscriber.confirmed_on)
		self.assertEqual(emails_to("pending@example.com"), 1)
		email = last_email_to("pending@example.com")
		self.assertEqual(email["Subject"], "Confirm, Ana")
		confirm_url = self.form.get_confirm_url(subscriber.token).replace("&", "&amp;")
		self.assertIn(confirm_url, email.get_body(("html",)).get_content())

	def test_pending_subscriber_cannot_download(self):
		subscribe("test-double-opt-in", "early@example.com")
		token = frappe.db.get_value("Subscriber", "early@example.com", "token")

		response = download_page(self.lead_magnet.route, token, method="POST")

		self.assertEqual(response.status_code, 404)

	def test_confirm_makes_active_and_sends_the_lead_magnet(self):
		subscribe("test-double-opt-in", "confirmer@example.com")
		token = frappe.db.get_value("Subscriber", "confirmer@example.com", "token")

		confirm_subscription("test-double-opt-in", token)

		subscriber = frappe.get_doc("Subscriber", "confirmer@example.com")
		self.assertEqual(subscriber.status, "Active")
		self.assertIsNotNone(subscriber.confirmed_on)
		self.assertEqual(frappe.local.response.type, "page")
		self.assertEqual(last_email_to("confirmer@example.com")["Subject"], "Your manual")

	def test_confirm_link_from_the_email_works(self):
		subscribe("test-double-opt-in", "link@example.com")
		token = frappe.db.get_value("Subscriber", "link@example.com", "token")
		query = parse_qs(urlparse(self.form.get_confirm_url(token)).query)

		confirm_subscription(query["form_id"][0], query["token"][0])

		self.assertEqual(frappe.db.get_value("Subscriber", "link@example.com", "status"), "Active")

	def test_second_confirm_click_sends_no_second_magnet_email(self):
		subscribe("test-double-opt-in", "double-click@example.com")
		token = frappe.db.get_value("Subscriber", "double-click@example.com", "token")

		confirm_subscription("test-double-opt-in", token)
		confirm_subscription("test-double-opt-in", token)

		self.assertEqual(emails_to("double-click@example.com"), 2)

	def test_active_subscriber_skips_the_confirm_email_and_gets_the_lead_magnet(self):
		"""A confirmed reader has nothing left to confirm, and came for what the form gives away."""
		make_form("test-single")
		subscribe("test-single", "already@example.com")

		subscribe("test-double-opt-in", "already@example.com")

		self.assertEqual(frappe.db.get_value("Subscriber", "already@example.com", "status"), "Active")
		self.assertEqual(emails_to("already@example.com"), 1)
		self.assertEqual(last_email_to("already@example.com")["Subject"], "Your manual")

	def test_unsubscribed_person_must_confirm_again(self):
		subscribe("test-double-opt-in", "back@example.com")
		token = frappe.db.get_value("Subscriber", "back@example.com", "token")
		confirm_subscription("test-double-opt-in", token)
		frappe.db.set_value("Subscriber", "back@example.com", "status", "Unsubscribed")

		# An old confirm link does not undo the unsubscribe.
		confirm_subscription("test-double-opt-in", token)
		self.assertEqual(frappe.db.get_value("Subscriber", "back@example.com", "status"), "Unsubscribed")

		subscribe("test-double-opt-in", "back@example.com")
		self.assertEqual(frappe.db.get_value("Subscriber", "back@example.com", "status"), "Pending")

	def test_wrong_token_changes_nothing(self):
		subscribe("test-double-opt-in", "stays-pending@example.com")

		confirm_subscription("test-double-opt-in", "not-a-token")

		self.assertEqual(frappe.local.response.http_status_code, 404)
		self.assertEqual(frappe.db.get_value("Subscriber", "stays-pending@example.com", "status"), "Pending")

	def test_double_opt_in_needs_a_confirm_subject(self):
		self.form.reload()
		self.form.confirm_subject = ""

		with self.assertRaises(frappe.ValidationError):
			self.form.save()


def emails_to(recipient: str) -> int:
	return frappe.db.count("Email Queue Recipient", {"recipient": recipient})
