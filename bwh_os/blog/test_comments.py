from unittest.mock import patch

import frappe
from frappe.tests import IntegrationTestCase

from bwh_os.blog.api import add_comment, get_comments, get_engagement, like_post, set_hidden


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

	def test_feed_groups_comments_by_post(self, _titles):
		comment = add_comment("stories/one-year", "Ada", "ada@example.com", "Grouped", random_ip())
		frappe.db.set_value("BWH Blog Comment", comment["id"], "hidden", 1)

		feed = get_comments()

		post = next(post for post in feed["posts"] if post["post_id"] == "stories/one-year")
		self.assertEqual(post["title"], "One Year")
		self.assertEqual(post["url"], "https://bwh.tech/blog/stories/one-year/")
		row = next(row for row in post["comments"] if row["id"] == comment["id"])
		self.assertIs(row["hidden"], True)

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

	def test_website_methods_need_the_api_role(self, _titles):
		frappe.set_user("Guest")

		with self.assertRaises(frappe.PermissionError):
			get_engagement("stories/one-year")
		with self.assertRaises(frappe.PermissionError):
			get_comments()
		with self.assertRaises(frappe.PermissionError):
			set_hidden([1], True)
