"""LinkedIn, the personal profile. See specs/04-social-posts.md.

The request shapes come from `gitroomhq/postiz-app`, which has posted through this API
for years: the versioned REST host, the `commentary` escaping, the id that arrives in a
response header instead of the body, and the comment endpoint that answers with `object`.
"""

import re
from collections.abc import Callable
from urllib.parse import quote

from frappe import _
from frappe.model.document import Document

from bwh_os.social.providers.base import Account, BadRequest, Provider, Release

# The version of the REST API. LinkedIn wants it on every call to `rest/`.
API_VERSION = "202601"
# The comment endpoint has not moved in years and still answers on this version.
COMMENT_API_VERSION = "202306"

# `commentary` is little markup, so these characters have to be escaped or the post
# breaks where the reader typed nothing special. The list is postiz's.
ESCAPED = re.compile(r"([\\<>#~_|\[\]*(){}@])")


class LinkedInProvider(Provider):
	key = "LinkedIn"

	max_length = 3000
	# `multiImage` holds 20. A comment on a personal post is text, so media stops at part 1.
	max_images = 20
	media_after_part_one = False

	USERINFO_URL = "https://api.linkedin.com/v2/userinfo"
	POSTS_URL = "https://api.linkedin.com/rest/posts"
	COMMENTS_URL = "https://api.linkedin.com/rest/socialActions/{urn}/comments"
	FEED_URL = "https://www.linkedin.com/feed/update/{urn}"

	@classmethod
	def identity(cls, token_cache: Document) -> dict:
		"""The person behind the token. `sub` is the id that goes into `urn:li:person:{sub}`."""
		data = cls.request("GET", cls.USERINFO_URL, token_cache).json()
		return {
			"account_id": data["sub"],
			"display_name": data.get("name"),
			# A personal profile has no handle, and the vanity name needs a scope we do not ask for.
			"handle": None,
			"avatar_url": data.get("picture"),
			"profile_url": None,
		}

	@classmethod
	def post(
		cls,
		account: Account,
		parts: list[dict],
		settings: dict,
		released: list[dict],
		on_release: Callable[[Release], None],
	) -> None:
		"""The post, then one comment per part after it, each written down as it lands."""
		done = {row["part_no"]: row for row in released}
		urn = done.get(1, {}).get("id")

		for part_no, part in enumerate(parts, start=1):
			if part_no in done:
				continue
			if part.get("media"):
				# Media uploads come with slice 2.5. Nothing can attach one before then.
				raise BadRequest(_("LinkedIn media is not ready yet"))

			if part_no == 1:
				urn = cls.create_post(account, part.get("text") or "")
				on_release(Release(part_no=1, id=urn, url=cls.FEED_URL.format(urn=urn)))
			else:
				comment_id = cls.create_comment(account, urn, part.get("text") or "")
				on_release(Release(part_no=part_no, id=comment_id))

	@classmethod
	def create_post(cls, account: Account, text: str) -> str:
		"""Part 1. The id of the post comes back in a header, not in the body."""
		response = cls.request(
			"POST",
			cls.POSTS_URL,
			account.token_cache,
			post_name=account.post_name,
			headers=cls.headers(API_VERSION),
			json={
				"author": f"urn:li:person:{account.account_id}",
				"commentary": escape(text),
				"visibility": "PUBLIC",
				"distribution": {
					"feedDistribution": "MAIN_FEED",
					"targetEntities": [],
					"thirdPartyDistributionChannels": [],
				},
				"lifecycleState": "PUBLISHED",
				"isReshareDisabledByAuthor": False,
			},
		)
		urn = response.headers.get("x-restli-id")
		if not urn:
			raise BadRequest(_("LinkedIn took the post but named no id"))
		return urn

	@classmethod
	def create_comment(cls, account: Account, urn: str, text: str) -> str:
		"""A part after the first becomes a comment on the post."""
		actor = f"urn:li:person:{account.account_id}"
		response = cls.request(
			"POST",
			cls.COMMENTS_URL.format(urn=quote(urn, safe="")),
			account.token_cache,
			post_name=account.post_name,
			headers=cls.headers(COMMENT_API_VERSION),
			json={"actor": actor, "object": urn, "message": {"text": escape(text)}},
		)
		return response.json().get("object") or ""

	@classmethod
	def headers(cls, version: str) -> dict:
		return {"LinkedIn-Version": version, "X-Restli-Protocol-Version": "2.0.0"}


def escape(text: str) -> str:
	"""What `commentary` needs, so a post reads the way it was written."""
	return ESCAPED.sub(r"\\\1", text or "")
