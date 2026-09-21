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
from bwh_os.mailing.lead_magnet_page import content_disposition

FILE_BYTES = b"test manual"


class IntegrationTestLeadMagnet(IntegrationTestCase):
	def setUp(self):
		use_test_email_account()
		self.lead_magnet = make_lead_magnet()
		self.lead_magnet.db_set(
			{
				"subject": "Here is your copy, {{ first_name }}",
				"content_html": email_html(
					'<p>Hi {{ first_name }}, here is {{ lead_magnet }}.</p><a href="{{ download_url }}">Download</a>'
				),
			}
		)
		self.form = make_form("test-manual")
		self.form.db_set(
			{
				"lead_magnet": self.lead_magnet.name,
				"welcome_subject": "Welcome, {{ first_name }}",
				"welcome_content_html": email_html("<p>Hi {{ first_name }}, thanks for joining.</p>"),
			}
		)
		frappe.local.response = frappe._dict()

	def test_public_file_is_rejected(self):
		with self.assertRaises(frappe.ValidationError):
			frappe.get_doc({"doctype": "Lead Magnet", "title": "Open", "file": "/files/open.pdf"}).insert()

	def test_new_signup_gets_the_greeting_then_the_magnet_email(self):
		subscribe("test-manual", "magnet@example.com", first_name="Ana")

		self.assertEqual(emails_to("magnet@example.com"), 2)
		greeting, magnet_email = ordered_emails_to("magnet@example.com")
		self.assertEqual(greeting["Subject"], "Welcome, Ana")
		self.assertEqual(magnet_email["Subject"], "Here is your copy, Ana")
		token = frappe.db.get_value("Subscriber", "magnet@example.com", "token")
		download_url = self.lead_magnet.get_download_url(token).replace("&", "&amp;")
		self.assertIn(download_url, magnet_email.get_body(("html",)).get_content())

	def test_known_email_asking_again_gets_the_file_but_not_the_greeting(self):
		"""Someone already on the list still came for the manual, but has already been welcomed."""
		subscribe("test-manual", "twice-magnet@example.com")
		subscribe("test-manual", "twice-magnet@example.com")

		self.assertEqual(emails_to("twice-magnet@example.com"), 3)
		subjects = [
			frappe.db.get_value("Email Queue", name, "message")
			for name in frappe.db.get_all(
				"Email Queue Recipient",
				filters={"recipient": "twice-magnet@example.com"},
				pluck="parent",
			)
		]
		self.assertEqual(sum("Welcome" in s for s in subjects), 1)
		self.assertEqual(sum("Here is your copy" in s for s in subjects), 2)

	def test_turning_off_the_switch_sends_only_the_file(self):
		self.form.db_set("send_welcome_with_lead_magnet", 0)

		subscribe("test-manual", "file-only@example.com")

		self.assertEqual(emails_to("file-only@example.com"), 1)
		self.assertEqual(last_email_to("file-only@example.com")["Subject"], "Here is your copy, there")

	def test_a_form_with_no_welcome_subject_still_sends_the_file(self):
		self.form.db_set({"welcome_subject": "", "welcome_content_html": ""})

		subscribe("test-manual", "no-welcome@example.com")

		self.assertEqual(emails_to("no-welcome@example.com"), 1)
		self.assertEqual(last_email_to("no-welcome@example.com")["Subject"], "Here is your copy, there")

	def test_delivery_email_needs_the_download_link(self):
		magnet = new_lead_magnet("No Link Yet")
		magnet.subject = "Here it is"
		magnet.content_html = email_html("<p>No link in here.</p>")

		with self.assertRaises(frappe.ValidationError):
			magnet.save()

	def test_subject_without_content_is_refused(self):
		magnet = new_lead_magnet("No Content Yet")
		magnet.subject = "Here it is"

		with self.assertRaises(frappe.ValidationError):
			magnet.save()

	def test_a_magnet_with_no_email_has_nothing_to_send(self):
		magnet = new_lead_magnet("No Email At All")
		subscriber = frappe.get_doc("Subscriber", add_subscriber("no-email-magnet@example.com"))

		self.assertFalse(magnet.has_email())
		with self.assertRaises(frappe.ValidationError):
			magnet.send_to(subscriber, source="Manual")

	def test_send_to_gives_each_subscriber_their_own_link(self):
		first = frappe.get_doc("Subscriber", add_subscriber("first-send@example.com"))
		second = frappe.get_doc("Subscriber", add_subscriber("second-send@example.com"))

		self.lead_magnet.send_to(first, source="Manual")
		self.lead_magnet.send_to(second, source="Manual")

		first_email = last_email_to("first-send@example.com")
		second_email = last_email_to("second-send@example.com")
		self.assertIn(first.token, first_email.get_body(("html",)).get_content())
		self.assertIn(second.token, second_email.get_body(("html",)).get_content())
		self.assertNotIn(second.token, first_email.get_body(("html",)).get_content())

	def test_a_form_needs_its_lead_magnet_to_have_an_email(self):
		empty_magnet = new_lead_magnet("Nothing To Give")
		self.form.reload()
		self.form.lead_magnet = empty_magnet.name

		with self.assertRaises(frappe.ValidationError):
			self.form.save()

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

	def test_a_non_ascii_file_name_survives_the_header(self):
		self.assertEqual(
			content_disposition('Guía "2026".pdf'),
			"attachment; filename=\"Gu_a _2026_.pdf\"; filename*=UTF-8''Gu%C3%ADa%20%222026%22.pdf",
		)

	def test_missing_token_matches_no_subscriber(self):
		name = add_subscriber("no-token@example.com")
		# A token-less row would match `token IS NULL` if the page looked up a missing token.
		frappe.db.set_value("Subscriber", name, "token", None)

		response = download_page(self.lead_magnet.route, None, method="POST")

		self.assertEqual(response.status_code, 404)
		self.assertFalse(frappe.db.exists("Lead Magnet Download", {"subscriber": name}))

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


def download_page(route: str, token: str | None, method: str = "GET"):
	"""Ask for /download/<route> the way a browser does, through the real page renderer.

	The request goes back as it was afterwards. A leftover one from `set_request` has no
	`request_ip`, and the next test to call a rate-limited endpoint dies on it.
	"""
	request = getattr(frappe.local, "request", None)
	form_dict = frappe.local.form_dict
	try:
		query_string = f"token={token}" if token else ""
		set_request(method=method, path=f"/download/{route}", query_string=query_string)
		frappe.local.form_dict = frappe._dict(token=token) if token else frappe._dict()
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
		{
			"doctype": "File",
			"file_name": f"{frappe.generate_hash(length=8)}.txt",
			"is_private": 1,
			"content": FILE_BYTES,
		}
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


def emails_to(recipient: str) -> int:
	return frappe.db.count("Email Queue Recipient", {"recipient": recipient})


def ordered_emails_to(recipient: str):
	"""Every email to this recipient, oldest first, as parsed messages."""
	names = frappe.db.get_all(
		"Email Queue Recipient",
		filters={"recipient": recipient},
		pluck="parent",
		order_by="creation asc, name asc",
	)
	return [
		message_from_string(frappe.db.get_value("Email Queue", name, "message"), policy=policy.default)
		for name in names
	]
