# Copyright (c) 2026, BWH and contributors
# For license information, please see license.txt

import frappe
from frappe.tests import IntegrationTestCase

from bwh_os.mailing.api import send_test_newsletter
from bwh_os.mailing.doctype.lead_magnet.test_lead_magnet import last_email_to, use_test_email_account

EDITOR_EMAIL = "test-newsletter-editor@example.com"
CONTENT_HTML = (
	"<!DOCTYPE html><html><head></head><body>"
	'<table><tr><td><p>Hello readers</p></td></tr></table>'
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

	def test_test_send_goes_to_current_user_with_footer(self):
		issue = make_issue()
		frappe.set_user(make_editor())

		recipient = send_test_newsletter(issue.name)

		self.assertEqual(recipient, EDITOR_EMAIL)
		email = last_email_to(recipient)
		self.assertEqual(email["Subject"], "[Test] Issue #1")
		html = email.get_body(("html",)).get_content()
		self.assertIn("Hello readers", html)
		self.assertIn("Test Company LLP", html)
		self.assertIn("bwh_os.mailing.api.unsubscribe", html)
		# The footer goes inside the document, and Frappe does not wrap it in a second one.
		self.assertLess(html.index("Test Company LLP"), html.lower().index("</body>"))
		self.assertEqual(html.lower().count("<body"), 1)

	def test_footer_is_added_when_html_has_no_body_tag(self):
		issue = make_issue(content_html="<p>Just a fragment</p>")

		html = issue.get_email_html("https://example.com/unsubscribe")

		self.assertTrue(html.startswith("<p>Just a fragment</p>"))
		self.assertIn("https://example.com/unsubscribe", html)

	def test_empty_issue_cannot_be_tested(self):
		issue = make_issue(content_html="")

		with self.assertRaises(frappe.ValidationError):
			send_test_newsletter(issue.name)

	def test_unsubscribed_user_gets_an_error_instead_of_nothing(self):
		issue = make_issue()
		frappe.set_user(make_editor())
		frappe.get_doc({"doctype": "Email Unsubscribe", "email": EDITOR_EMAIL, "global_unsubscribe": 1}).insert(
			ignore_permissions=True
		)

		with self.assertRaises(frappe.ValidationError):
			send_test_newsletter(issue.name)

	def test_only_system_manager_can_send_test(self):
		issue = make_issue()
		frappe.set_user("Guest")

		with self.assertRaises(frappe.PermissionError):
			send_test_newsletter(issue.name)


def make_editor() -> str:
	if not frappe.db.exists("User", EDITOR_EMAIL):
		user = frappe.get_doc(
			{"doctype": "User", "email": EDITOR_EMAIL, "first_name": "Editor", "send_welcome_email": 0}
		)
		user.append("roles", {"role": "System Manager"})
		user.insert(ignore_permissions=True)
	return EDITOR_EMAIL


def make_issue(content_html: str = CONTENT_HTML):
	return frappe.get_doc(
		{
			"doctype": "Newsletter Issue",
			"subject": "Issue #1",
			"content_json": {"type": "doc", "content": []},
			"content_html": content_html,
		}
	).insert()
