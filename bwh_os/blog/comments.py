"""Blog comments from Turso, grouped by post for the Comments page."""

from bwh_os.blog.posts import get_post_titles, post_url
from bwh_os.blog.turso import Turso

# The page loads all comments at once. Above this, it shows only the newest.
COMMENT_LIMIT = 2000


class CommentFeed:
	def __init__(self, turso: Turso):
		self.turso = turso

	def load(self) -> dict:
		# One more row than the limit tells us that there are more comments.
		comments, likes = self.turso.pipeline(
			[
				(
					"""SELECT id, post_id, name, email, body, created_at, hidden
					     FROM comments
					 ORDER BY created_at DESC, id DESC
					    LIMIT ?""",
					[COMMENT_LIMIT + 1],
				),
				"SELECT post_id, likes FROM post_likes",
			]
		)
		return {
			"db_host": self.turso.host,
			"truncated": len(comments) > COMMENT_LIMIT,
			"posts": group_by_post(comments[:COMMENT_LIMIT], likes),
		}


def group_by_post(comments: list[dict], likes: list[dict]) -> list[dict]:
	"""One group for each post that has comments. The comments are newest first, so the groups are too."""
	likes_by_post = {row["post_id"]: row["likes"] for row in likes}
	titles = get_post_titles()
	posts: dict[str, dict] = {}
	for comment in comments:
		post_id = comment["post_id"]
		if post_id not in posts:
			posts[post_id] = {
				"post_id": post_id,
				# A draft or a renamed post is not in the feed.
				"title": titles.get(post_id) or post_id,
				"url": post_url(post_id),
				"likes": likes_by_post.get(post_id, 0),
				"comments": [],
			}
		posts[post_id]["comments"].append({**comment, "hidden": bool(comment["hidden"])})
	return list(posts.values())
