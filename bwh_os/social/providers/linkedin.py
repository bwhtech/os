"""LinkedIn, the personal profile. See specs/04-social-posts.md.

The request shapes come from `gitroomhq/postiz-app`, which has posted through this API
for years: the versioned REST host, the `commentary` escaping, the id that arrives in a
response header instead of the body, and the comment endpoint that answers with `object`.
"""

import re
import time
from collections.abc import Callable
from urllib.parse import quote

from frappe import _
from frappe.model.document import Document

from bwh_os.social.providers.base import (
	Account,
	BadRequest,
	Provider,
	Release,
	file_bytes,
	images_of,
	videos_of,
)

# The version of the REST API. LinkedIn wants it on every call to `rest/`.
API_VERSION = "202601"
# The comment endpoint has not moved in years and still answers on this version.
COMMENT_API_VERSION = "202306"
# How long an image needs before a post may name it. Postiz waits the same 20 seconds.
IMAGE_WAIT_SECONDS = 20

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
	IMAGES_URL = "https://api.linkedin.com/rest/images?action=initializeUpload"
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
			if videos_of(part):
				# Video uploads come with slice 3.1. Nothing can attach one before then.
				raise BadRequest(_("LinkedIn video is not ready yet"))

			if part_no == 1:
				urn = cls.create_post(
					account, part.get("text") or "", cls.upload_media(account, images_of(part))
				)
				on_release(Release(part_no=1, id=urn, url=cls.FEED_URL.format(urn=urn)))
			else:
				comment_id = cls.create_comment(account, urn, part.get("text") or "")
				on_release(Release(part_no=part_no, id=comment_id))

	@classmethod
	def upload_media(cls, account: Account, media: list[dict]) -> list[str]:
		"""Every image, in the order it was written, as the urns the post refers to.

		A personal token cannot read the status of an upload, so there is no way to ask
		whether an image is ready. LinkedIn drops an image the post names too early, so
		the post waits instead of asking.
		"""
		images = [cls.upload_image(account, item) for item in media]
		if images:
			time.sleep(IMAGE_WAIT_SECONDS)
		return images

	@classmethod
	def upload_image(cls, account: Account, item: dict) -> str:
		"""LinkedIn hands out a URL to put the file at, and the urn it will be known by."""
		# The file is read first: an upload slot for a file that is gone helps nobody.
		content = file_bytes(item["file_url"])
		upload = cls.request(
			"POST",
			cls.IMAGES_URL,
			account.token_cache,
			post_name=account.post_name,
			headers=cls.headers(API_VERSION),
			json={"initializeUploadRequest": {"owner": cls.author(account)}},
		).json()["value"]
		cls.request(
			"PUT",
			upload["uploadUrl"],
			account.token_cache,
			post_name=account.post_name,
			data=content,
		)
		return upload["image"]

	@classmethod
	def create_post(cls, account: Account, text: str, images: list[str] | None = None) -> str:
		"""Part 1. The id of the post comes back in a header, not in the body."""
		response = cls.request(
			"POST",
			cls.POSTS_URL,
			account.token_cache,
			post_name=account.post_name,
			headers=cls.headers(API_VERSION),
			json={
				"author": cls.author(account),
				"commentary": escape(text),
				"visibility": "PUBLIC",
				"distribution": {
					"feedDistribution": "MAIN_FEED",
					"targetEntities": [],
					"thirdPartyDistributionChannels": [],
				},
				"lifecycleState": "PUBLISHED",
				"isReshareDisabledByAuthor": False,
				**cls.content(images or []),
			},
		)
		urn = response.headers.get("x-restli-id")
		if not urn:
			raise BadRequest(_("LinkedIn took the post but named no id"))
		return urn

	@classmethod
	def content(cls, images: list[str]) -> dict:
		"""How a post carries its images. One is `media`; more than one is `multiImage`."""
		if not images:
			return {}
		if len(images) == 1:
			return {"content": {"media": {"id": images[0], "altText": ""}}}
		return {"content": {"multiImage": {"images": [{"id": urn, "altText": ""} for urn in images]}}}

	@classmethod
	def author(cls, account: Account) -> str:
		return f"urn:li:person:{account.account_id}"

	@classmethod
	def create_comment(cls, account: Account, urn: str, text: str) -> str:
		"""A part after the first becomes a comment on the post."""
		actor = cls.author(account)
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
