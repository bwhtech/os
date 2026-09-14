from unittest.mock import patch

import frappe
from frappe.tests import IntegrationTestCase

from bwh_os.blog.api import (
	add_comment,
	delete_comments,
	get_engagement,
	get_overview,
	like_post,
	set_hidden,
)


def random_ip() -> str:
	return f"test-{frappe.generate_hash(length=8)}"


@patch(
	"bwh_os.blog.doctype.bwh_blog_post.bwh_blog_post.get_post_titles",
	return_value={"stories/one-year": "One Year"},
)
class IntegrationTestBlogApi(IntegrationTestCase):
	def tearDown(self):
		frappe.set_user("Administrator")

	def test_first_comment_makes_the_post_with_its_feed_title(self, _titles):
		comment = add_comment("stories/one-year", "Ada", " Ada@Example.com ", "Nice post", random_ip())

		self.assertEqual(frappe.db.get_value("BWH Blog Post", "stories/one-year", "title"), "One Year")
		self.assertEqual(comment["name"], "Ada")
		self.assertEqual(comment["email"], "ada@example.com")
		self.assertIsInstance(comment["created_at"], int)

	def test_comment_is_stored_as_typed(self, _titles):
		# The blog shows plain text, so code like <template> must not be stripped as HTML.
		comment = add_comment(
			"stories/one-year", "Ada <dev>", "ada@example.com", "Wrap it in <template>", random_ip()
		)

		self.assertEqual(comment["name"], "Ada <dev>")
		self.assertEqual(comment["body"], "Wrap it in <template>")

	def test_engagement_leaves_out_hidden_comments(self, _titles):
		visible = add_comment("stories/one-year", "Ada", "ada@example.com", "Visible", random_ip())
		hidden = add_comment("stories/one-year", "Bot", "bot@example.com", "Spam", random_ip())
		frappe.db.set_value("BWH Blog Comment", hidden["id"], "hidden", 1)

		ids = [comment["id"] for comment in get_engagement("stories/one-year")["comments"]]

		self.assertIn(visible["id"], ids)
		self.assertNotIn(hidden["id"], ids)

	def test_likes_add_up_and_stop_after_three_from_one_ip(self, _titles):
		ip = random_ip()
		before = get_engagement("tutorial/likes-test")["likes"]

		totals = [like_post("tutorial/likes-test", ip) for _ in range(3)]

		self.assertEqual(totals, [before + 1, before + 2, before + 3])
		with self.assertRaises(frappe.RateLimitExceededError):
			like_post("tutorial/likes-test", ip)
		self.assertEqual(like_post("tutorial/likes-test", random_ip()), before + 4)

	def test_post_id_must_be_category_and_slug(self, _titles):
		with self.assertRaises(frappe.ValidationError):
			like_post("../etc/passwd", random_ip())

	def test_hide_and_unhide_many_comments(self, _titles):
		ids = [
			add_comment("stories/one-year", "Ada", "ada@example.com", f"Bulk {i}", random_ip())["id"]
			for i in range(2)
		]

		self.assertEqual(set_hidden(ids, True), 2)
		shown = [comment["id"] for comment in get_engagement("stories/one-year")["comments"]]
		self.assertFalse(set(ids) & set(shown))

		set_hidden([str(ids[0])], False)
		shown = [comment["id"] for comment in get_engagement("stories/one-year")["comments"]]
		self.assertIn(ids[0], shown)
		self.assertNotIn(ids[1], shown)

	def test_delete_many_comments(self, _titles):
		ids = [
			add_comment("stories/one-year", "Ada", "ada@example.com", f"Delete {i}", random_ip())["id"]
			for i in range(2)
		]

		self.assertEqual(delete_comments(ids), 2)

		self.assertFalse(frappe.db.exists("BWH Blog Comment", {"name": ("in", ids)}))

	def test_overview_counts_comments_likes_and_top_posts(self, _titles):
		for body in ("One", "Two"):
			add_comment("stories/overview-test", "Ada", "ada@example.com", body, random_ip())
		hidden = add_comment("stories/overview-test", "Bot", "bot@example.com", "Spam", random_ip())
		set_hidden([hidden["id"]], True)
		like_post("stories/overview-test", random_ip())
		before = get_overview()
		like_post("stories/overview-test", random_ip())

		overview = get_overview()

		self.assertGreaterEqual(overview["comments"]["total"], 3)
		self.assertGreaterEqual(overview["comments"]["last_period"], 3)
		self.assertGreaterEqual(overview["hidden"], 1)
		self.assertEqual(overview["likes"], before["likes"] + 1)
		top = next(post for post in overview["top_by_comments"] if post.post_id == "stories/overview-test")
		self.assertEqual(top["count"], 3)

	def test_website_methods_need_the_api_role(self, _titles):
		frappe.set_user("Guest")

		with self.assertRaises(frappe.PermissionError):
			get_engagement("stories/one-year")
		with self.assertRaises(frappe.PermissionError):
			set_hidden([1], True)
		with self.assertRaises(frappe.PermissionError):
			delete_comments([1])
		with self.assertRaises(frappe.PermissionError):
			get_overview()
