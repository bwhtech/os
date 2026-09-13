# Copyright (c) 2026, BWH and contributors
# For license information, please see license.txt

from unittest.mock import patch
from urllib.parse import parse_qs, urlparse

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_to_date, set_request

from bwh_os.mailing.api import (
	add_subscriber,
	get_newsletter_engagement,
	send_newsletter,
	track_click,
	track_open,
	unsubscribe,
)
from bwh_os.mailing.doctype.lead_magnet.test_lead_magnet import last_email_to, use_test_email_account
from bwh_os.mailing.doctype.newsletter_issue.test_newsletter_issue import make_issue
from bwh_os.mailing.doctype.subscriber_tag.subscriber_tag import SubscriberTag
from bwh_os.mailing.newsletter_send import run_send_job
from bwh_os.mailing.newsletter_tracking import EmailTracking, sign

CONTENT_HTML = (
	"<!DOCTYPE html><html><head></head><body><table><tr><td>"
	'<p><a href="https://bwh.tech/post?a=1&amp;b=2">Read the post</a></p>'
	'<p><a href="mailto:hello@bwh.tech">Write to us</a></p>'
	"</td></tr></table></body></html>"
)
POST_URL = "https://bwh.tech/post?a=1&b=2"


class IntegrationTestNewsletterTracking(IntegrationTestCase):
	def setUp(self):
		use_test_email_account()
		self.commit = patch.object(frappe.db, "commit")
		self.commit.start()
		self.request = getattr(frappe.local, "request", None)
		frappe.local.response = frappe._dict()

	def tearDown(self):
		frappe.local.request = self.request
		self.commit.stop()
		frappe.set_user("Administrator")

	def test_sent_email_has_tracked_links_and_pixel(self):
		issue, deliveries = self.send(1)
		delivery = deliveries[0]

		html = last_email_to(delivery.email).get_body(("html",)).get_content()

		self.assertNotIn('href="https://bwh.tech/post', html)
		self.assertIn('href="mailto:hello@bwh.tech"', html)
		self.assertIn(f"track_open?delivery={delivery.name}", html)
		self.assertIn(f"delivery={delivery.name}", self.unsubscribe_header(delivery))

		click_url = EmailTracking(delivery.name).click_url(POST_URL)
		query = parse_qs(urlparse(click_url).query)
		self.assertEqual(query["url"], [POST_URL])
		self.assertIn(click_url.replace("&", "&amp;"), html)

	def test_open_counts_each_reader_once_on_the_issue(self):
		issue, deliveries = self.send(2)

		response = track_open(deliveries[0].name)
		track_open(deliveries[0].name)
		track_open(deliveries[1].name)

		self.assertEqual(response.mimetype, "image/gif")
		self.assertEqual(frappe.db.get_value("Newsletter Delivery", deliveries[0].name, "open_count"), 2)
		self.assertEqual(frappe.db.get_value("Newsletter Issue", issue.name, "opened_count"), 2)
		self.assertEqual(frappe.db.count("Newsletter Event", {"issue": issue.name, "type": "Open"}), 3)

	def test_unknown_delivery_still_gets_the_pixel(self):
		self.assertEqual(track_open("not-a-delivery").mimetype, "image/gif")

	def test_click_redirects_and_counts_as_an_open(self):
		issue, deliveries = self.send(1)
		delivery = deliveries[0].name

		response = track_click(delivery, POST_URL, sign(delivery, POST_URL))

		self.assertEqual(response.status_code, 302)
		self.assertEqual(response.location, POST_URL)
		issue.reload()
		self.assertEqual((issue.opened_count, issue.clicked_count), (1, 1))
		event = frappe.get_all("Newsletter Event", filters={"delivery": delivery, "type": "Click"}, pluck="url")
		self.assertEqual(event, [POST_URL])

	def test_click_with_a_bad_signature_does_not_redirect(self):
		issue, deliveries = self.send(1)
		delivery = deliveries[0].name

		response = track_click(delivery, "https://evil.example.com", sign(delivery, POST_URL))

		self.assertIsNone(response)
		self.assertEqual(frappe.local.response.http_status_code, 404)
		self.assertFalse(frappe.db.exists("Newsletter Event", {"delivery": delivery}))

	def test_unsubscribe_from_an_issue_counts_on_the_issue(self):
		issue, deliveries = self.send(1)
		delivery = deliveries[0]
		token = frappe.db.get_value("Subscriber", delivery.email, "token")
		set_request(method="POST", path="/")

		unsubscribe(token, delivery=delivery.name)
		unsubscribe(token, delivery=delivery.name)

		self.assertEqual(frappe.db.get_value("Newsletter Issue", issue.name, "unsubscribed_count"), 1)
		self.assertTrue(frappe.db.get_value("Newsletter Delivery", delivery.name, "unsubscribed_at"))

	def test_engagement_report_compares_with_the_previous_issue(self):
		previous, _ = self.send(2)
		frappe.db.set_value(
			"Newsletter Issue",
			previous.name,
			{"status": "Sent", "sent_count": 2, "opened_count": 1, "sent_at": add_to_date(None, minutes=-1)},
		)
		issue, deliveries = self.send(2)
		frappe.db.set_value("Newsletter Issue", issue.name, "sent_count", 2)
		for delivery in deliveries:
			track_click(delivery.name, POST_URL, sign(delivery.name, POST_URL))

		report = get_newsletter_engagement(issue.name)

		self.assertEqual(report["rates"], {"open_rate": 100.0, "click_rate": 100.0, "unsubscribes": 0})
		self.assertEqual(report["previous"]["name"], previous.name)
		self.assertEqual(report["previous"]["open_rate"], 50.0)
		self.assertEqual([stage["count"] for stage in report["funnel"]], [2, 2, 2, 2])
		self.assertEqual((report["hourly"][0]["Open"], report["hourly"][0]["Click"]), (2, 2))
		self.assertEqual(len(report["hourly"]), 72)
		self.assertEqual(report["top_links"][0]["url"], POST_URL)
		self.assertEqual((report["top_links"][0]["clicks"], report["top_links"][0]["readers"]), (2, 2))

	def send(self, readers: int):
		"""Send a new issue to new readers with a new tag. Returns the issue and its deliveries."""
		tag = SubscriberTag.ensure(f"test-track-{frappe.generate_hash(length=6)}")
		for index in range(readers):
			add_subscriber(f"reader{index}-{tag}@example.com", tags=[tag])
		issue = make_issue(content_html=CONTENT_HTML)
		issue.update({"audience": "Tags", "tags": [{"tag": tag}]}).save()

		with patch("bwh_os.mailing.newsletter_send.frappe.enqueue"):
			send_newsletter(issue.name)
		run_send_job(issue.name)
		issue.reload()
		deliveries = frappe.get_all(
			"Newsletter Delivery", filters={"issue": issue.name}, fields=["name", "email"], order_by="creation"
		)
		return issue, deliveries

	def unsubscribe_header(self, delivery) -> str:
		return last_email_to(delivery.email)["List-Unsubscribe"]
