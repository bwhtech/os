from unittest.mock import patch

import frappe
from frappe.tests import IntegrationTestCase

from bwh_os.blog.api import add_comment
from bwh_os.mailing.doctype.lead_magnet.test_lead_magnet import last_email_to, use_test_email_account

RECIPIENT = "blog-owner@example.com"


def random_ip() -> str:
	return f"test-{frappe.generate_hash(length=8)}"


@patch(
	"bwh_os.blog.doctype.bwh_blog_post.bwh_blog_post.get_post_titles",
	return_value={"stories/one-year": "One Year"},
)
class IntegrationTestBlogNotifications(IntegrationTestCase):
	def setUp(self):
		use_test_email_account()

	def turn_on(self, email: str | None = RECIPIENT):
		settings = frappe.get_doc("Mailing Settings")
		settings.update({"notify_blog_comments": 1, "blog_notification_email": email}).save()

	def test_new_comment_sends_an_escaped_email_with_the_moderate_link(self, _titles):
		self.turn_on()

		add_comment(
			"stories/one-year",
			"Ada <b>",
			"ada@example.com",
			"Nice <script>x</script>\nSecond line",
			random_ip(),
		)

		email = last_email_to(RECIPIENT)
		html = email.get_body(("html",)).get_content()
		self.assertIn("New comment on One Year", email["Subject"])
		self.assertIn("<strong>Ada &lt;b&gt;</strong>", html)
		self.assertIn("Nice &lt;script&gt;x&lt;/script&gt;", html)
		self.assertNotIn("<script>", html)
		self.assertIn("/os/blog/comments?post=stories%2Fone-year", html)

	def test_no_email_when_notifications_are_off(self, _titles):
		self.turn_on()
		frappe.get_doc("Mailing Settings").update({"notify_blog_comments": 0}).save()
		before = frappe.db.count("Email Queue", {"reference_doctype": "BWH Blog Comment"})

		add_comment("stories/one-year", "Ada", "ada@example.com", "Quiet", random_ip())

		self.assertEqual(frappe.db.count("Email Queue", {"reference_doctype": "BWH Blog Comment"}), before)

	def test_recipient_defaults_to_the_user_who_turns_it_on(self, _titles):
		self.turn_on(email=None)

		self.assertEqual(
			frappe.db.get_single_value("Mailing Settings", "blog_notification_email"),
			frappe.db.get_value("User", frappe.session.user, "email"),
		)
