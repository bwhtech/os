# Copyright (c) 2026, BWH and contributors
# For license information, please see license.txt

from email import message_from_string, policy

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import set_request
from frappe.website.serve import get_response

from bwh_os.mailing.api import (
	add_subscriber,
	download_lead_magnet,
	get_download_counts,
	get_lead_magnet_activity,
	subscribe,
)
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

	def test_known_email_asking_again_gets_the_file_again(self):
		"""Someone already on the list still came for the manual."""
		subscribe("test-manual", "twice-magnet@example.com")
		subscribe("test-manual", "twice-magnet@example.com")

		self.assertEqual(
			frappe.db.count("Email Queue", {"reference_name": "twice-magnet@example.com"}),
			2,
		)

	def test_route_comes_from_the_title(self):
		self.assertEqual(new_lead_magnet("A Field Guide to Bench").route, "a-field-guide-to-bench")

	def test_a_second_magnet_with_the_same_title_gets_a_suffix(self):
		title = "Two of These"
		first = new_lead_magnet(title)

		self.assertEqual(new_lead_magnet(title).route, f"{first.route}-2")

	def test_the_landing_page_shows_the_title_and_logs_nothing(self):
		"""A mail scanner follows the link. It must not count as a download."""
		name = add_subscriber("browser@example.com")
		token = frappe.db.get_value("Subscriber", name, "token")
		downloads = frappe.db.count("Lead Magnet Download")

		response = download_page(self.lead_magnet.route, token)

		self.assertEqual(response.status_code, 200)
		self.assertIn(self.lead_magnet.title, frappe.safe_decode(response.get_data()))
		self.assertEqual(frappe.db.count("Lead Magnet Download"), downloads)

	def test_the_button_logs_and_sends_the_file(self):
		name = add_subscriber("downloader@example.com")
		token = frappe.db.get_value("Subscriber", name, "token")

		response = download_page(self.lead_magnet.route, token, method="POST")

		self.assertEqual(response.get_data(), FILE_BYTES)
		self.assertIn("attachment", response.headers["Content-Disposition"])
		self.assertTrue(
			frappe.db.exists(
				"Lead Magnet Download", {"lead_magnet": self.lead_magnet.name, "subscriber": name}
			)
		)

	def test_the_same_reader_downloading_again_counts_once(self):
		"""The log keeps every download. The summaries count people."""
		name = add_subscriber("repeat-downloader@example.com")
		token = frappe.db.get_value("Subscriber", name, "token")
		before = get_download_counts().get(self.lead_magnet.name, 0)
		before_activity = get_lead_magnet_activity(self.lead_magnet.name)

		for _ in range(3):
			download_page(self.lead_magnet.route, token, method="POST")

		self.assertEqual(
			frappe.db.count(
				"Lead Magnet Download", {"lead_magnet": self.lead_magnet.name, "subscriber": name}
			),
			3,
		)
		self.assertEqual(get_download_counts()[self.lead_magnet.name], before + 1)
		activity = get_lead_magnet_activity(self.lead_magnet.name)
		self.assertEqual(activity["total"], before_activity["total"] + 1)
		self.assertEqual(activity["last_period"], before_activity["last_period"] + 1)

	def test_wrong_token_logs_nothing(self):
		downloads = frappe.db.count("Lead Magnet Download")

		response = download_page(self.lead_magnet.route, "not-a-token", method="POST")

		self.assertEqual(response.status_code, 404)
		self.assertEqual(frappe.db.count("Lead Magnet Download"), downloads)

	def test_the_old_download_url_still_works(self):
		"""Those links are in inboxes forever."""
		name = add_subscriber("old-link@example.com")
		token = frappe.db.get_value("Subscriber", name, "token")

		response = download_lead_magnet(self.lead_magnet.name, token)

		self.assertEqual(response.status_code, 302)
		self.assertIn(f"/download/{self.lead_magnet.route}", response.headers["Location"])


def download_page(route: str, token: str, method: str = "GET"):
	"""Ask for /download/<route> the way a browser does, through the real page renderer.

	The request goes back as it was afterwards. A leftover one from `set_request` has no
	`request_ip`, and the next test to call a rate-limited endpoint dies on it.
	"""
	request = getattr(frappe.local, "request", None)
	form_dict = frappe.local.form_dict
	try:
		set_request(method=method, path=f"/download/{route}", query_string=f"token={token}")
		frappe.local.form_dict = frappe._dict(token=token)
		return get_response()
	finally:
		frappe.local.request = request
		frappe.local.form_dict = form_dict


def make_lead_magnet():
	title = "Test Missing Frappe Manual"
	if name := frappe.db.exists("Lead Magnet", {"title": title}):
		return frappe.get_doc("Lead Magnet", name)
	return new_lead_magnet(title)


def new_lead_magnet(title: str):
	file = frappe.get_doc(
		{"doctype": "File", "file_name": f"{frappe.generate_hash(length=8)}.txt", "is_private": 1, "content": FILE_BYTES}
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
