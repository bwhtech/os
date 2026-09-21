# Copyright (c) 2026, BWH and contributors
# For license information, please see license.txt

"""Where a reader's reply goes: the address on the email, or the one in Mailing Settings."""

from unittest.mock import patch

import frappe
from frappe.tests import IntegrationTestCase

from bwh_os.mailing.api import add_subscriber, send_newsletter, subscribe
from bwh_os.mailing.doctype.lead_magnet.test_lead_magnet import last_email_to, use_test_email_account
from bwh_os.mailing.doctype.newsletter_issue.test_newsletter_issue import make_issue
from bwh_os.mailing.doctype.signup_form.test_signup_form import email_html, make_form
from bwh_os.mailing.doctype.subscriber_tag.subscriber_tag import SubscriberTag
from bwh_os.mailing.newsletter_send import run_send_job

SETTINGS_REPLY_TO = "hello@example.com"
OWN_REPLY_TO = "editor@example.com"


class IntegrationTestReplyTo(IntegrationTestCase):
	def setUp(self):
		use_test_email_account()
		frappe.get_doc("Mailing Settings").update({"reply_to": SETTINGS_REPLY_TO}).save()
		self.form = make_form("test-reply-to")
		self.form.db_set(
			{
				"double_opt_in": 1,
				"confirm_subject": "Confirm",
				"confirm_content_html": email_html('<a href="{{ confirm_url }}">Confirm</a>'),
				"send_welcome_email": 1,
				"welcome_subject": "Welcome",
				"welcome_content_html": email_html("<p>Glad you are here.</p>"),
				"welcome_reply_to": OWN_REPLY_TO,
				"confirm_reply_to": None,
			}
		)
		frappe.local.response = frappe._dict()

	def test_welcome_email_replies_to_the_address_on_the_form(self):
		email = "welcome-reply@example.com"
		subscribe("test-reply-to", email)
		self.form.confirm(frappe.get_doc("Subscriber", email))

		self.assertEqual(last_email_to(email)["Reply-To"], OWN_REPLY_TO)

	def test_an_email_with_no_address_of_its_own_replies_to_the_settings_address(self):
		email = "confirm-reply@example.com"
		subscribe("test-reply-to", email)

		self.assertEqual(last_email_to(email)["Reply-To"], SETTINGS_REPLY_TO)

	def test_newsletter_replies_to_the_address_on_the_issue(self):
		tag = SubscriberTag.ensure(f"test-reply-to-{frappe.generate_hash(length=6)}")
		reader = "reader-reply@example.com"
		add_subscriber(reader, tags=[tag])
		issue = make_issue()
		issue.update({"audience": "Tags", "tags": [{"tag": tag}], "reply_to": OWN_REPLY_TO}).save()

		with patch.object(frappe.db, "commit"), patch("bwh_os.mailing.newsletter_send.frappe.enqueue"):
			send_newsletter(issue.name)
			run_send_job(issue.name)

		self.assertEqual(last_email_to(reader)["Reply-To"], OWN_REPLY_TO)

	def test_an_address_that_is_not_an_email_is_refused(self):
		self.form.welcome_reply_to = "not an address"

		self.assertRaises(frappe.ValidationError, self.form.save)
