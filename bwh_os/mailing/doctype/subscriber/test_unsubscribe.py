# Copyright (c) 2026, BWH and contributors
# For license information, please see license.txt

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import set_request

from bwh_os.mailing.api import add_subscriber, subscribe, unsubscribe
from bwh_os.mailing.doctype.lead_magnet.test_lead_magnet import last_email_to, use_test_email_account
from bwh_os.mailing.doctype.signup_form.test_signup_form import email_html, make_form


class IntegrationTestUnsubscribe(IntegrationTestCase):
	def setUp(self):
		use_test_email_account()
		self.request = getattr(frappe.local, "request", None)
		frappe.local.response = frappe._dict()

	def tearDown(self):
		frappe.local.request = self.request

	def test_list_email_has_unsubscribe_link_and_headers(self):
		form = make_form("test-unsubscribe-email")
		form.db_set({"welcome_subject": "Welcome", "welcome_content_html": email_html("<p>Hi</p>")})
		subscribe("test-unsubscribe-email", "headers@example.com")

		email = last_email_to("headers@example.com")
		url = frappe.get_doc("Subscriber", "headers@example.com").get_unsubscribe_url()
		self.assertEqual(email["List-Unsubscribe"], f"<{url}>")
		self.assertEqual(email["List-Unsubscribe-Post"], "List-Unsubscribe=One-Click")
		self.assertIsNone(email["X-List-Unsubscribe"])
		self.assertIn(url, email.get_body(("html",)).get_content())

	def test_get_shows_a_page_and_changes_nothing(self):
		token = make_subscriber("look@example.com")
		set_request(method="GET", path="/")

		unsubscribe(token)

		self.assertEqual(frappe.local.response.type, "page")
		self.assertIn("<form", frappe.local.message)
		self.assertEqual(frappe.db.get_value("Subscriber", "look@example.com", "status"), "Active")

	def test_post_unsubscribes(self):
		token = make_subscriber("leave@example.com")
		set_request(method="POST", path="/")

		unsubscribe(token)

		subscriber = frappe.get_doc("Subscriber", "leave@example.com")
		self.assertEqual(subscriber.status, "Unsubscribed")
		self.assertIsNotNone(subscriber.unsubscribed_on)

	def test_pending_subscriber_can_unsubscribe(self):
		token = make_subscriber("pending-leave@example.com")
		frappe.db.set_value("Subscriber", "pending-leave@example.com", "status", "Pending")
		set_request(method="POST", path="/")

		unsubscribe(token)

		self.assertEqual(
			frappe.db.get_value("Subscriber", "pending-leave@example.com", "status"), "Unsubscribed"
		)

	def test_bounced_subscriber_stays_bounced(self):
		token = make_subscriber("bounced@example.com")
		frappe.db.set_value("Subscriber", "bounced@example.com", "status", "Bounced")
		set_request(method="POST", path="/")

		unsubscribe(token)

		self.assertEqual(frappe.db.get_value("Subscriber", "bounced@example.com", "status"), "Bounced")

	def test_wrong_token_shows_not_found(self):
		set_request(method="POST", path="/")

		unsubscribe("not-a-token")

		self.assertEqual(frappe.local.response.http_status_code, 404)


def make_subscriber(email: str) -> str:
	name = add_subscriber(email)
	return frappe.db.get_value("Subscriber", name, "token")
