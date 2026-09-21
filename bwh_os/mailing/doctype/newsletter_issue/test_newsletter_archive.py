# Copyright (c) 2026, BWH and contributors
# For license information, please see license.txt

import frappe
from frappe.tests import IntegrationTestCase
from frappe.website.serve import get_response

from bwh_os.mailing.doctype.lead_magnet.test_lead_magnet import make_lead_magnet
from bwh_os.mailing.doctype.newsletter_issue.test_newsletter_issue import make_issue
from bwh_os.mailing.doctype.signup_form.test_signup_form import email_html
from bwh_os.mailing.newsletter_archive import public_issues


class IntegrationTestNewsletterArchive(IntegrationTestCase):
	def setUp(self):
		frappe.get_doc("Mailing Settings").update({"company_name": "Archive Company LLP"}).save()

	def tearDown(self):
		frappe.set_user("Administrator")

	def test_draft_cannot_be_public(self):
		issue = make_issue()
		issue.is_public = 1

		with self.assertRaises(frappe.ValidationError):
			issue.save()

	def test_a_lead_magnet_issue_cannot_be_public(self):
		magnet = make_lead_magnet()
		issue = make_issue(
			content_html=email_html('<a href="{{ download_url }}">Download</a>'), lead_magnet=magnet.name
		)
		# db_set, not save: is_public is the only field this test changes, and the status jump
		# alone would trip ensure_unchanged_after_send if it went through validate().
		issue.db_set({"status": "Sent", "sent_at": frappe.utils.now_datetime()})
		issue.reload()

		issue.is_public = 1
		with self.assertRaises(frappe.ValidationError):
			issue.save()

	def test_route_is_made_from_the_subject_and_kept_unique(self):
		first = publish(make_sent_issue("Three Videos: and a Cohort!"))
		second = publish(make_sent_issue("Three Videos: and a Cohort!"))

		self.assertEqual(first.route, "three-videos-and-a-cohort")
		self.assertEqual(second.route, "three-videos-and-a-cohort-2")

	def test_route_can_change_after_the_send(self):
		issue = publish(make_sent_issue())
		issue.route = "My New Route"
		issue.save()

		self.assertEqual(issue.route, "my-new-route")

	def test_public_issue_page_has_no_pixel_and_no_unsubscribe_link(self):
		issue = publish(make_sent_issue())
		frappe.set_user("Guest")

		response = get_response(f"newsletter/{issue.route}")

		html = response.get_data(as_text=True)
		self.assertEqual(response.status_code, 200)
		self.assertIn("Hello readers", html)
		self.assertIn("Archive Company LLP", html)
		self.assertNotIn("track_open", html)
		self.assertNotIn("unsubscribe", html.lower())

	def test_private_issue_page_is_not_found(self):
		issue = publish(make_sent_issue())
		issue.db_set("is_public", 0)
		frappe.set_user("Guest")

		self.assertEqual(get_response(f"newsletter/{issue.route}").status_code, 404)

	def test_index_lists_only_public_sent_issues(self):
		public = publish(make_sent_issue())
		make_sent_issue()

		routes = [row.route for row in public_issues()]

		self.assertIn(public.route, routes)
		self.assertEqual(len(routes), len(set(routes)))
		self.assertTrue(all(routes))

	def test_index_page_renders_for_guests(self):
		issue = publish(make_sent_issue("Archive index issue"))
		frappe.set_user("Guest")

		response = get_response("newsletter")

		self.assertEqual(response.status_code, 200)
		self.assertIn("Archive index issue", response.get_data(as_text=True))
		self.assertIn(f"/newsletter/{issue.route}", response.get_data(as_text=True))


def make_sent_issue(subject: str = "Archive issue"):
	issue = make_issue()
	issue.db_set({"subject": subject, "status": "Sent", "sent_at": frappe.utils.now_datetime()})
	issue.reload()
	return issue


def publish(issue):
	issue.is_public = 1
	issue.save()
	return issue
