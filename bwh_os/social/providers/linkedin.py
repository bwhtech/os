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
	Retryable,
	SocialError,
	file_bytes,
	images_of,
	videos_of,
)

# The version of the REST API. LinkedIn wants it on every call to `rest/`, and it retires
# a version a year after releasing it, so this one has a shelf life. Every call uses the
# same version: an endpoint that has not changed in years still stops answering on a
# version that is out of date.
API_VERSION = "202601"
# How long an image needs before a post may name it. Postiz waits the same 20 seconds.
IMAGE_WAIT_SECONDS = 20
# A video is transcoded before it can be posted. Five minutes is the spec's ceiling.
VIDEO_WAIT_SECONDS = 5 * 60
VIDEO_POLL_SECONDS = 5

# `commentary` is little markup, so these characters have to be escaped or the post
# breaks where the reader typed nothing special. The list is postiz's.
ESCAPED = re.compile(r"([\\<>#~_|\[\]*(){}@])")


class LinkedInProvider(Provider):
	key = "LinkedIn"

	max_length = 3000
	# `multiImage` holds 20. A comment on a personal post is text, so media stops at part 1.
	max_images = 20
	# A video under 200 MB, per the spec. The site takes 500 MB, so this is the tighter rule.
	max_video_bytes = 200 * 1024 * 1024
	media_after_part_one = False

	USERINFO_URL = "https://api.linkedin.com/v2/userinfo"
	IMAGES_URL = "https://api.linkedin.com/rest/images?action=initializeUpload"
	VIDEOS_URL = "https://api.linkedin.com/rest/videos?action=initializeUpload"
	FINALIZE_VIDEO_URL = "https://api.linkedin.com/rest/videos?action=finalizeUpload"
	VIDEO_URL = "https://api.linkedin.com/rest/videos/{urn}"
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

			if part_no == 1:
				urn = cls.create_post(
					account, part.get("text") or "", cls.upload_media(account, part.get("media") or [])
				)
				on_release(Release(part_no=1, id=urn, url=cls.FEED_URL.format(urn=urn)))
			else:
				comment_id = cls.create_comment(account, urn, part.get("text") or "")
				on_release(Release(part_no=part_no, id=comment_id))

	@classmethod
	def upload_media(cls, account: Account, media: list[dict]) -> list[str]:
		"""Every file, in the order it was written, as the urns the post refers to.

		A video goes up on its own and says when it is ready. Images cannot: a personal
		token cannot read the status of an image upload, so there is no way to ask whether
		one is ready. LinkedIn drops an image the post names too early, so the post waits
		instead of asking.
		"""
		if videos := videos_of(media):
			return [cls.upload_video(account, videos[0])]

		images = [cls.upload_image(account, item) for item in images_of(media)]
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
			headers=cls.headers(),
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
	def upload_video(cls, account: Account, item: dict) -> str:
		"""A video goes up in the ranges LinkedIn asks for, then it is told they all arrived.

		Each range answers with an ETag, and the finalize call lists them in order: that is
		how LinkedIn puts the file back together. Then the video is transcoded, and a post
		that names it before it is `AVAILABLE` gets no video at all, so this waits for it.
		"""
		content = file_bytes(item["file_url"])
		upload = cls.request(
			"POST",
			cls.VIDEOS_URL,
			account.token_cache,
			post_name=account.post_name,
			headers=cls.headers(),
			json={
				"initializeUploadRequest": {
					"owner": cls.author(account),
					"fileSizeBytes": len(content),
					"uploadCaptions": False,
					"uploadThumbnail": False,
				}
			},
		).json()["value"]

		tags = [
			cls.upload_range(account, instruction, content) for instruction in upload["uploadInstructions"]
		]
		cls.request(
			"POST",
			cls.FINALIZE_VIDEO_URL,
			account.token_cache,
			post_name=account.post_name,
			headers=cls.headers(),
			json={
				"finalizeUploadRequest": {
					"video": upload["video"],
					"uploadToken": upload.get("uploadToken", ""),
					"uploadedPartIds": tags,
				}
			},
		)
		cls.wait_for_video(account, upload["video"])
		return upload["video"]

	@classmethod
	def upload_range(cls, account: Account, instruction: dict, content: bytes) -> str:
		"""One range of the file. The ETag is what names this part in the finalize call."""
		first, last = int(instruction["firstByte"]), int(instruction["lastByte"])
		response = cls.request(
			"PUT",
			instruction["uploadUrl"],
			account.token_cache,
			post_name=account.post_name,
			data=content[first : last + 1],
		)
		tag = response.headers.get("etag") or response.headers.get("ETag")
		if not tag:
			raise BadRequest(_("LinkedIn took a part of the video but named no id"))
		return tag.strip('"')

	@classmethod
	def wait_for_video(cls, account: Account, urn: str) -> None:
		"""Until LinkedIn says the video can be posted, or until waiting is pointless."""
		waited = 0
		while waited < VIDEO_WAIT_SECONDS:
			status = (
				cls.request(
					"GET",
					cls.VIDEO_URL.format(urn=quote(urn, safe="")),
					account.token_cache,
					headers=cls.headers(),
				)
				.json()
				.get("status")
			)
			if status == "AVAILABLE":
				return
			if status == "PROCESSING_FAILED":
				raise BadRequest(_("LinkedIn could not process the video"))
			time.sleep(VIDEO_POLL_SECONDS)
			waited += VIDEO_POLL_SECONDS

		raise Retryable(_("LinkedIn is still processing the video"))

	@classmethod
	def create_post(cls, account: Account, text: str, images: list[str] | None = None) -> str:
		"""Part 1. The id of the post comes back in a header, not in the body."""
		response = cls.request(
			"POST",
			cls.POSTS_URL,
			account.token_cache,
			post_name=account.post_name,
			headers=cls.headers(),
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
			headers=cls.headers(),
			json={"actor": actor, "object": urn, "message": {"text": escape(text)}},
		)
		return response.json().get("object") or ""

	@classmethod
	def error_for(cls, response) -> SocialError:
		"""LinkedIn says 401 to a token that is gone and 403 to a call it will not allow.

		A token that has run out or been taken back is a 401 and names itself, with
		`EXPIRED_ACCESS_TOKEN` or `REVOKED_ACCESS_TOKEN`. A 403 is about the call: the app
		is not cleared for that endpoint. Connecting again through the same app changes
		nothing, so a 403 must not expire the channel and send someone round a loop that
		cannot end. The reader gets what LinkedIn said and decides what to do with it.
		"""
		if response.status_code == 403:
			return BadRequest(
				_("{0} said 403: {1}").format(cls.key, response.text[:500]),
			)
		return super().error_for(response)

	@classmethod
	def headers(cls) -> dict:
		return {"LinkedIn-Version": API_VERSION, "X-Restli-Protocol-Version": "2.0.0"}


def escape(text: str) -> str:
	"""What `commentary` needs, so a post reads the way it was written."""
	return ESCAPED.sub(r"\\\1", text or "")
