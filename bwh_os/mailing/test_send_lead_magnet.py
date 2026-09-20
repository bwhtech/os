# Copyright (c) 2026, BWH and contributors
# For license information, please see license.txt

import frappe
from frappe.tests import IntegrationTestCase

from bwh_os.mailing.api import add_subscriber, get_lead_magnet_recipients, send_lead_magnet
from bwh_os.mailing.doctype.lead_magnet.lead_magnet import MANUAL_SEND_LIMIT
from bwh_os.mailing.doctype.lead_magnet.test_lead_magnet import (
	emails_to,
	make_lead_magnet,
	new_lead_magnet,
	use_test_email_account,
)
from bwh_os.mailing.doctype.signup_form.test_signup_form import email_html
from bwh_os.mailing.doctype.subscriber_tag.subscriber_tag import SubscriberTag


class IntegrationTestSendLeadMagnet(IntegrationTestCase):
	def setUp(self):
		use_test_email_account()
		self.lead_magnet = make_lead_magnet()
		self.lead_magnet.db_set(
			{
				"subject": "Here is your copy, {{ first_name }}",
				"content_html": email_html('<a href="{{ download_url }}">Download</a>'),
			}
		)
		# Records live for the whole class, so a fixed tag would pick up every other test's
		# subscribers too.
		self.tag = SubscriberTag.ensure(f"test-manual-send-{frappe.generate_hash(length=6)}")

	def test_sends_to_picked_subscribers(self):
		first = add_subscriber("manual-first@example.com", tags=[self.tag])
		second = add_subscriber("manual-second@example.com", tags=[self.tag])

		result = send_lead_magnet(self.lead_magnet.name, subscribers=[first, second])

		self.assertEqual(result, {"sent": 2, "failed": []})
		self.assertEqual(emails_to("manual-first@example.com"), 1)
		self.assertEqual(emails_to("manual-second@example.com"), 1)

	def test_sends_to_everyone_with_a_tag(self):
		add_subscriber("tagged-one@example.com", tags=[self.tag])
		add_subscriber("tagged-two@example.com", tags=[self.tag])
		add_subscriber("untagged@example.com")

		result = send_lead_magnet(self.lead_magnet.name, tags=[self.tag])

		self.assertEqual(result["sent"], 2)
		self.assertEqual(emails_to("untagged@example.com"), 0)

	def test_a_non_active_subscriber_is_left_out(self):
		pending = add_subscriber("still-pending@example.com", tags=[self.tag])
		frappe.db.set_value("Subscriber", pending, "status", "Pending")
		add_subscriber("is-active@example.com", tags=[self.tag])

		result = send_lead_magnet(self.lead_magnet.name, tags=[self.tag])

		self.assertEqual(result["sent"], 1)
		self.assertEqual(emails_to("still-pending@example.com"), 0)
		self.assertEqual(emails_to("is-active@example.com"), 1)

	def test_skip_downloaded_leaves_out_a_prior_reader(self):
		already = add_subscriber("already-has-it@example.com", tags=[self.tag])
		fresh = add_subscriber("wants-it@example.com", tags=[self.tag])
		self.lead_magnet.send_to(frappe.get_doc("Subscriber", already), source="Manual")
		self.lead_magnet.log_download(already)

		counts = get_lead_magnet_recipients(self.lead_magnet.name, tags=[self.tag], skip_downloaded=1)
		result = send_lead_magnet(self.lead_magnet.name, tags=[self.tag], skip_downloaded=1)

		self.assertEqual(counts["recipients"], 1)
		self.assertEqual(counts["already_downloaded"], 1)
		self.assertEqual(result["sent"], 1)
		# One send from setup plus none new: the prior reader is skipped, not re-sent.
		self.assertEqual(emails_to("already-has-it@example.com"), 1)
		self.assertEqual(emails_to(fresh), 1)

	def test_above_the_cap_is_refused(self):
		names = [
			add_subscriber(f"cap-{i}@example.com", tags=[self.tag]) for i in range(MANUAL_SEND_LIMIT + 1)
		]

		with self.assertRaises(frappe.ValidationError):
			send_lead_magnet(self.lead_magnet.name, subscribers=names)

	def test_a_magnet_with_no_email_is_refused(self):
		empty = new_lead_magnet("Manual Send No Email")
		subscriber = add_subscriber("no-email-manual@example.com", tags=[self.tag])

		with self.assertRaises(frappe.ValidationError):
			send_lead_magnet(empty.name, subscribers=[subscriber])

	def test_nobody_picked_is_refused(self):
		with self.assertRaises(frappe.ValidationError):
			send_lead_magnet(self.lead_magnet.name)
