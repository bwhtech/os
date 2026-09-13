# Copyright (c) 2026, BWH and contributors
# For license information, please see license.txt

from email import message_from_string, policy

import frappe
from frappe.tests import IntegrationTestCase

from bwh_os.mailing.api import add_subscriber, download_lead_magnet, subscribe
from bwh_os.mailing.doctype.signup_form.test_signup_form import email_html, make_form

FILE_BYTES = b"test manual"


class IntegrationTestLeadMagnet(IntegrationTestCase):
	def setUp(self):
		use_test_email_account()
		self.lead_magnet = make_lead_magnet()
		self.form = make_form("test-manual")
		self.form.db_set(
			{
				"lead_magnet": self.lead_magnet.name,
				"welcome_subject": "Your manual, {{ first_name }}",
				"welcome_content_html": email_html(
					'<p>Hi {{ first_name }}, here is {{ lead_magnet }}.</p><a href="{{ download_url }}">Download</a>'
				),
			}
		)
		frappe.local.response = frappe._dict()

	def test_public_file_is_rejected(self):
		with self.assertRaises(frappe.ValidationError):
			frappe.get_doc({"doctype": "Lead Magnet", "title": "Open", "file": "/files/open.pdf"}).insert()

	def test_new_signup_gets_welcome_email_with_download_link(self):
		subscribe("test-manual", "magnet@example.com", first_name="Ana")

		email = last_email_to("magnet@example.com")
		self.assertEqual(email["Subject"], "Your manual, Ana")
		token = frappe.db.get_value("Subscriber", "magnet@example.com", "token")
		download_url = self.lead_magnet.get_download_url(token).replace("&", "&amp;")
		self.assertIn(download_url, email.get_body(("html",)).get_content())

	def test_known_email_gets_no_second_welcome_email(self):
		subscribe("test-manual", "twice-magnet@example.com")
		subscribe("test-manual", "twice-magnet@example.com")

		self.assertEqual(
			frappe.db.count("Email Queue", {"reference_name": "twice-magnet@example.com"}),
			1,
		)

	def test_download_logs_and_sends_the_file(self):
		name = add_subscriber("downloader@example.com")
		token = frappe.db.get_value("Subscriber", name, "token")

		download_lead_magnet(self.lead_magnet.name, token)

		self.assertEqual(frappe.local.response.type, "download")
		self.assertEqual(frappe.safe_encode(frappe.local.response.filecontent), FILE_BYTES)
		self.assertTrue(
			frappe.db.exists(
				"Lead Magnet Download", {"lead_magnet": self.lead_magnet.name, "subscriber": name}
			)
		)

	def test_wrong_token_logs_nothing(self):
		downloads = frappe.db.count("Lead Magnet Download")

		download_lead_magnet(self.lead_magnet.name, "not-a-token")

		self.assertEqual(frappe.local.response.type, "page")
		self.assertEqual(frappe.local.response.http_status_code, 404)
		self.assertEqual(frappe.db.count("Lead Magnet Download"), downloads)


def make_lead_magnet():
	title = "Test Missing Frappe Manual"
	if name := frappe.db.exists("Lead Magnet", {"title": title}):
		return frappe.get_doc("Lead Magnet", name)
	file = frappe.get_doc(
		{"doctype": "File", "file_name": "test-manual.txt", "is_private": 1, "content": FILE_BYTES}
	).insert()
	return frappe.get_doc({"doctype": "Lead Magnet", "title": title, "file": file.file_url}).insert()


def use_test_email_account():
	name = "_Test Mailing"
	if not frappe.db.exists("Email Account", name):
		frappe.get_doc(
			{
				"doctype": "Email Account",
				"email_account_name": name,
				"email_id": "test-mailing@example.com",
				"enable_outgoing": 1,
				"smtp_server": "localhost",
				"no_smtp_authentication": 1,
			}
		).insert()
	frappe.get_doc("Mailing Settings").update({"email_account": name}).save()


def last_email_to(recipient: str):
	name = frappe.db.get_value(
		"Email Queue Recipient", {"recipient": recipient}, "parent", order_by="creation desc"
	)
	message = frappe.db.get_value("Email Queue", name, "message")
	return message_from_string(message, policy=policy.default)
