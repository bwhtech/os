from unittest.mock import MagicMock, patch

import frappe
from frappe.tests import IntegrationTestCase

from bwh_os.blog.api import get_comments
from bwh_os.blog.comments import COMMENT_LIMIT, CommentFeed, group_by_post


def comment(id: int, post_id: str, hidden: int = 0) -> dict:
	return {
		"id": id,
		"post_id": post_id,
		"name": "Ada",
		"email": "ada@example.com",
		"body": "Nice post",
		"created_at": 1_789_000_000 - id,
		"hidden": hidden,
	}


@patch("bwh_os.blog.comments.get_post_titles", return_value={"stories/one-year": "One Year"})
class IntegrationTestComments(IntegrationTestCase):
	def tearDown(self):
		frappe.set_user("Administrator")

	def test_groups_keep_the_order_of_the_newest_comment(self, _titles):
		comments = [
			comment(1, "stories/one-year"),
			comment(2, "tutorial/draft", hidden=1),
			comment(3, "stories/one-year"),
		]

		posts = group_by_post(comments, [{"post_id": "stories/one-year", "likes": 12}])

		self.assertEqual([post["post_id"] for post in posts], ["stories/one-year", "tutorial/draft"])
		self.assertEqual([c["id"] for c in posts[0]["comments"]], [1, 3])
		self.assertEqual(posts[0]["title"], "One Year")
		self.assertEqual(posts[0]["url"], "https://bwh.tech/blog/stories/one-year/")
		self.assertEqual(posts[0]["likes"], 12)
		# A post that is not in the feed shows its id and has no likes row.
		self.assertEqual(posts[1]["title"], "tutorial/draft")
		self.assertEqual(posts[1]["likes"], 0)
		self.assertIs(posts[1]["comments"][0]["hidden"], True)

	def test_feed_is_truncated_above_the_limit(self, _titles):
		turso = MagicMock(host="db.turso.io")
		turso.pipeline.return_value = [[comment(i, "stories/one-year") for i in range(COMMENT_LIMIT + 1)], []]

		feed = CommentFeed(turso).load()

		self.assertTrue(feed["truncated"])
		self.assertEqual(len(feed["posts"][0]["comments"]), COMMENT_LIMIT)
		self.assertEqual(feed["db_host"], "db.turso.io")

	def test_get_comments_before_setup(self, _titles):
		settings = frappe.get_single("Blog Settings")
		settings.turso_url = ""
		settings.save()

		self.assertEqual(get_comments(), {"configured": False})

	def test_get_comments_needs_system_manager(self, _titles):
		frappe.set_user("Guest")

		with self.assertRaises(frappe.PermissionError):
			get_comments()
