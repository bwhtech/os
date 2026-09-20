# Copyright (c) 2026, BWH and contributors
# For license information, please see license.txt

import frappe
from frappe.tests import IntegrationTestCase

from bwh_os.mailing import email_variables
from bwh_os.mailing.api import subscribe
from bwh_os.mailing.doctype.lead_magnet.test_lead_magnet import (
	last_email_to,
	make_lead_magnet,
	use_test_email_account,
)
from bwh_os.mailing.doctype.newsletter_issue.test_newsletter_issue import make_issue
from bwh_os.mailing.doctype.signup_form.test_signup_form import email_html, make_form


class IntegrationTestEmailVariables(IntegrationTestCase):
	def test_fill_escapes_values_and_uses_fallbacks(self):
		values = {"first_name": "", "email": "a&b@example.com"}

		html = email_variables.fill("<p>Hi {{ first_name }}, {{email}}</p>", values)

		self.assertEqual(html, "<p>Hi there, a&amp;b@example.com</p>")

	def test_fill_handles_encoded_links_and_leaves_other_variables(self):
		html = email_variables.fill(
			'<a href="%7B%7B%20confirm_url%20%7D%7D">{{ unknown }}</a>',
			{"confirm_url": "https://x.test/?a=1&b=2"},
		)

		self.assertEqual(html, '<a href="https://x.test/?a=1&amp;b=2">{{ unknown }}</a>')

	def test_check_rejects_unknown_and_old_jinja_variables(self):
		for text in ("{{ confirm_url }}", '{{ first_name or "there" }}'):
			with self.assertRaises(frappe.ValidationError):
				email_variables.check(text, email_variables.NEWSLETTER, "Email")

	def test_check_needs_required_variables(self):
		with self.assertRaises(frappe.ValidationError):
			email_variables.check(
				"<p>{{ first_name }}</p>", email_variables.CONFIRM, "Email", ["confirm_url"]
			)

	def test_double_opt_in_form_needs_the_confirm_link(self):
		form = make_form("test-variables-confirm")
		form.double_opt_in = 1
		form.confirm_subject = "Confirm"
		form.confirm_content_html = email_html("<p>No link</p>")

		with self.assertRaises(frappe.ValidationError):
			form.save()

		form.reload()
		form.update(
			{
				"double_opt_in": 1,
				"confirm_subject": "Confirm",
				"confirm_content_html": email_html('<a href="{{ confirm_url }}">Confirm</a>'),
			}
		).save()

	def test_welcome_email_rejects_the_download_variable(self):
		"""The greeting is a plain welcome now. The file has its own email."""
		with self.assertRaises(frappe.ValidationError):
			email_variables.check("<p>{{ download_url }}</p>", email_variables.WELCOME, "Email")

	def test_welcome_email_cannot_link_the_download_url(self):
		form = make_form("test-variables-welcome")
		form.welcome_subject = "Welcome"
		form.welcome_content_html = email_html('<a href="{{ download_url }}">Get it</a>')

		with self.assertRaises(frappe.ValidationError):
			form.save()

	def test_a_form_needs_its_lead_magnet_to_have_an_email(self):
		form = make_form("test-variables-lead-magnet")
		form.lead_magnet = make_lead_magnet().name

		with self.assertRaises(frappe.ValidationError):
			form.save()

	def test_with_lead_magnet_widens_the_allowed_set(self):
		self.assertEqual(
			email_variables.with_lead_magnet(email_variables.NEWSLETTER, None), email_variables.NEWSLETTER
		)
		self.assertEqual(
			set(email_variables.with_lead_magnet(email_variables.NEWSLETTER, "some-magnet")),
			{*email_variables.NEWSLETTER, *email_variables.MAGNET},
		)

	def test_newsletter_rejects_a_variable_it_cannot_fill(self):
		with self.assertRaises(frappe.ValidationError):
			make_issue(email_html('<a href="{{ download_url }}">Get it</a>'))

	def test_newsletter_web_version_uses_fallbacks(self):
		issue = make_issue(email_html("<p>Hi {{ first_name }}</p>"))

		self.assertIn("<p>Hi there</p>", issue.get_web_html())

	def test_welcome_email_gets_the_subscriber_values(self):
		use_test_email_account()
		form = make_form("test-variables-values")
		form.db_set(
			{
				"welcome_subject": "Hello {{ first_name }}",
				"welcome_content_html": email_html("<p>Hi {{ first_name }}, you are {{ email }}.</p>"),
			}
		)

		subscribe("test-variables-values", "values@example.com")

		email = last_email_to("values@example.com")
		self.assertEqual(email["Subject"], "Hello there")
		self.assertIn("Hi there, you are values@example.com.", email.get_body(("html",)).get_content())
