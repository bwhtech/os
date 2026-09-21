# Copyright (c) 2026, BWH and contributors
# For license information, please see license.txt

import frappe
from frappe.tests import IntegrationTestCase

from bwh_os.mailing.api import send_test_newsletter
from bwh_os.mailing.doctype.lead_magnet.test_lead_magnet import (
	last_email_to,
	make_lead_magnet,
	use_test_email_account,
)
from bwh_os.mailing.doctype.signup_form.test_signup_form import email_html

CONTENT_HTML = (
	'<!DOCTYPE html><html><head></head><body style="background-color:#f3f3f3">'
	"<table><tr><td><p>Hello readers</p></td></tr></table>"
	"</body></html>"
)


class IntegrationTestNewsletterIssue(IntegrationTestCase):
	def setUp(self):
		use_test_email_account()
		frappe.get_doc("Mailing Settings").update({"company_name": "Test Company LLP"}).save()

	def tearDown(self):
		frappe.set_user("Administrator")

	def test_new_issue_is_a_draft(self):
		self.assertEqual(make_issue().status, "Draft")

	def test_test_send_goes_to_given_address_with_footer(self):
		issue = make_issue()

		recipient = send_test_newsletter(issue.name, " reader-test@example.com ")

		self.assertEqual(recipient, "reader-test@example.com")
		email = last_email_to(recipient)
		self.assertEqual(email["Subject"], "[Test] Issue #1")
		html = email.get_body(("html",)).get_content()
		self.assertIn("Hello readers", html)
		self.assertIn("Test Company LLP", html)
		self.assertIn("bwh_os.mailing.api.unsubscribe", html)
		# The footer goes in the outer cell of the email, and Frappe does not wrap it in a second document.
		self.assertLess(html.index("Hello readers"), html.index("Test Company LLP"))
		self.assertLess(html.index("Test Company LLP"), html.lower().rindex("</td>"))
		self.assertEqual(html.lower().count("<body"), 1)

	def test_saved_html_keeps_the_full_document(self):
		issue = make_issue()

		self.assertEqual(frappe.db.get_value("Newsletter Issue", issue.name, "content_html"), CONTENT_HTML)

	def test_footer_is_added_when_html_has_no_body_tag(self):
		issue = make_issue(content_html="<p>Just a fragment</p>")

		html = issue.get_email_html("https://example.com/unsubscribe")

		self.assertTrue(html.startswith("<p>Just a fragment</p>"))
		self.assertIn("https://example.com/unsubscribe", html)

	def test_empty_issue_cannot_be_tested(self):
		issue = make_issue(content_html="")

		with self.assertRaises(frappe.ValidationError):
			send_test_newsletter(issue.name, "reader-test@example.com")

	def test_invalid_address_is_rejected(self):
		with self.assertRaises(frappe.ValidationError):
			send_test_newsletter(make_issue().name, "not-an-email")

	def test_unsubscribed_address_gets_an_error_instead_of_nothing(self):
		issue = make_issue()
		frappe.get_doc(
			{"doctype": "Email Unsubscribe", "email": "gone-test@example.com", "global_unsubscribe": 1}
		).insert(ignore_permissions=True)

		with self.assertRaises(frappe.ValidationError):
			send_test_newsletter(issue.name, "gone-test@example.com")

	def test_only_system_manager_can_send_test(self):
		issue = make_issue()
		frappe.set_user("Guest")

		with self.assertRaises(frappe.PermissionError):
			send_test_newsletter(issue.name, "reader-test@example.com")

	def test_issue_with_a_lead_magnet_needs_the_download_link(self):
		with self.assertRaises(frappe.ValidationError):
			make_issue(lead_magnet=make_lead_magnet().name)

	def test_issue_with_a_lead_magnet_and_the_link_saves(self):
		magnet = make_lead_magnet()

		issue = make_issue(
			content_html=email_html('<a href="{{ download_url }}">Download</a>'), lead_magnet=magnet.name
		)

		self.assertEqual(issue.lead_magnet, magnet.name)

	def test_a_newsletter_without_a_lead_magnet_cannot_use_the_download_link(self):
		with self.assertRaises(frappe.ValidationError):
			make_issue(content_html=email_html('<a href="{{ download_url }}">Download</a>'))

	def test_send_test_uses_a_real_download_link(self):
		magnet = make_lead_magnet()
		issue = make_issue(
			content_html=email_html('<a href="{{ download_url }}">Download</a>'), lead_magnet=magnet.name
		)

		send_test_newsletter(issue.name, "magnet-test@example.com")

		email = last_email_to("magnet-test@example.com")
		download_url = magnet.get_download_url("test").replace("&", "&amp;")
		self.assertIn(download_url, email.get_body(("html",)).get_content())


def make_issue(content_html: str = CONTENT_HTML, lead_magnet: str | None = None):
	return frappe.get_doc(
		{
			"doctype": "Newsletter Issue",
			"subject": "Issue #1",
			"content_json": {"type": "doc", "content": []},
			"content_html": content_html,
			"lead_magnet": lead_magnet,
		}
	).insert()
