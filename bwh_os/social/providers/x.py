"""X, the personal account. See specs/04-social-posts.md.

The token endpoint of X lives here rather than in the framework. `Connected App` signs
its calls the way `requests_oauthlib` does, with the client id in the body and no PKCE,
and X answers that with a refusal. Both legs of the connect come through this class: the
browser leg in `bwh_os/social/x_oauth.py`, and every later refresh from
`bwh_os.social.tokens`.

A post goes out as a thread: part 1 is a tweet, and each part after it replies to the one
before, which is how X itself makes one.
"""

import mimetypes
import time
from collections.abc import Callable

import frappe
import requests
from frappe import _
from frappe.model.document import Document
from frappe.utils.synchronization import filelock

from bwh_os.social.providers.base import (
	Account,
	BadRequest,
	Provider,
	ReconnectRequired,
	Release,
	Retryable,
	SocialError,
	file_bytes,
)
from bwh_os.social.x_text import weighted_length

# An X access token lives two hours. Refresh it before the last minutes, so a long upload
# that started on a healthy token does not end on a dead one. This sits above the margin
# `bwh_os.social.tokens` calls expired, or a token would be refused before it is renewed.
REFRESH_MARGIN_SECONDS = 300

# Who may reply to the thread. Everyone is the absence of the field rather than a value
# of it, so it never rides in the body, and a post that says nothing about it gets it.
REPLY_SETTINGS = ("everyone", "following", "mentionedUsers", "subscribers")
EVERYONE = "everyone"

# X takes the file in pieces of this size. Its own guide uses 1 MB.
MEDIA_CHUNK_BYTES = 1024 * 1024
# A video is transcoded before it can be tweeted. Five minutes is the spec's ceiling.
MEDIA_WAIT_SECONDS = 5 * 60
MEDIA_POLL_SECONDS = 5


class XProvider(Provider):
	key = "X"

	max_length = 280
	max_images = 4
	# X takes 5 MB of image. A GIF may be 15 MB, but the OS has one kind of image, so the
	# tighter number is the one it holds everything to.
	max_image_bytes = 5 * 1024 * 1024

	USERS_ME_URL = "https://api.x.com/2/users/me?user.fields=profile_image_url,username,name"
	PROFILE_URL = "https://x.com/{handle}"
	TWEETS_URL = "https://api.x.com/2/tweets"
	# The handle is not on the account the publisher carries, and X redirects `i` to it.
	TWEET_URL = "https://x.com/i/status/{id}"
	MEDIA_URL = "https://api.x.com/2/media/upload"
	MEDIA_INITIALIZE_URL = "https://api.x.com/2/media/upload/initialize"
	MEDIA_APPEND_URL = "https://api.x.com/2/media/upload/{id}/append"
	MEDIA_FINALIZE_URL = "https://api.x.com/2/media/upload/{id}/finalize"

	# X hands out a refresh token that rotates instead of running out, so the connection
	# has no day to count down to and the channel keeps no expiry.
	connection_expires = False

	@classmethod
	def identity(cls, token_cache: Document) -> dict:
		"""The account behind the token. `id` is the number that survives a rename."""
		data = cls.request("GET", cls.USERS_ME_URL, token_cache).json()["data"]
		handle = data.get("username")
		return {
			"account_id": data["id"],
			"display_name": data.get("name"),
			"handle": handle,
			"avatar_url": data.get("profile_image_url"),
			"profile_url": cls.PROFILE_URL.format(handle=handle) if handle else None,
		}

	@classmethod
	def count(cls, text: str) -> int:
		"""X counts weight, not characters. See `bwh_os.social.x_text`."""
		return weighted_length(text)

	@classmethod
	def validate(cls, parts: list[dict], settings: dict | None = None) -> list[str]:
		problems = super().validate(parts, settings)
		who = (settings or {}).get("reply_settings") or EVERYONE
		if who not in REPLY_SETTINGS:
			problems.append(_("X cannot keep replies to {0}").format(who))
		return problems

	@classmethod
	def post(
		cls,
		account: Account,
		parts: list[dict],
		settings: dict,
		released: list[dict],
		on_release: Callable[[Release], None],
	) -> None:
		"""The thread, oldest first. Each part replies to the one before it."""
		done = {row["part_no"]: row for row in released}
		previous = None

		for part_no, part in enumerate(parts, start=1):
			if part_no in done:
				previous = done[part_no]["id"]
				continue

			# Who may reply is a property of the conversation, so it rides on its first tweet.
			reply_settings = settings.get("reply_settings") if part_no == 1 else None
			previous = cls.create_tweet(
				account,
				part.get("text") or "",
				media_ids=cls.upload_media(account, part.get("media") or []),
				reply_to=previous,
				reply_settings=reply_settings,
			)
			on_release(Release(part_no=part_no, id=previous, url=cls.TWEET_URL.format(id=previous)))

	@classmethod
	def create_tweet(
		cls,
		account: Account,
		text: str,
		media_ids: list[str] | None = None,
		reply_to: str | None = None,
		reply_settings: str | None = None,
	) -> str:
		body: dict = {"text": text}
		if media_ids:
			body["media"] = {"media_ids": media_ids}
		if reply_to:
			body["reply"] = {"in_reply_to_tweet_id": reply_to}
		if reply_settings and reply_settings != EVERYONE:
			body["reply_settings"] = reply_settings

		response = cls.request(
			"POST", cls.TWEETS_URL, account.token_cache, post_name=account.post_name, json=body
		)
		tweet_id = response.json().get("data", {}).get("id")
		if not tweet_id:
			raise BadRequest(_("X took the tweet but named no id"))
		return tweet_id

	@classmethod
	def upload_media(cls, account: Account, media: list[dict]) -> list[str]:
		"""Every file of one part, in the order it was written, as the ids the tweet names."""
		return [cls.upload_one(account, item) for item in media]

	@classmethod
	def upload_one(cls, account: Account, item: dict) -> str:
		"""One file, in the three steps X asks for: say what is coming, send it, say it is done.

		The file goes up in chunks whatever its size. X takes an image in one piece, but the
		same three calls work for both, and one road is easier to keep right than two.
		"""
		content = file_bytes(item["file_url"])
		media_id = cls.initialize_media(account, item, len(content))
		for index, offset in enumerate(range(0, len(content), MEDIA_CHUNK_BYTES)):
			cls.append_media(account, media_id, index, content[offset : offset + MEDIA_CHUNK_BYTES])
		cls.finalize_media(account, media_id)
		return media_id

	@classmethod
	def initialize_media(cls, account: Account, item: dict, size: int) -> str:
		"""Ask X for the id the chunks and the tweet will name."""
		response = cls.request(
			"POST",
			cls.MEDIA_INITIALIZE_URL,
			account.token_cache,
			post_name=account.post_name,
			json={
				"media_type": media_type(item),
				"total_bytes": size,
				"media_category": media_category(item),
			},
		)
		media_id = response.json().get("data", {}).get("id")
		if not media_id:
			raise BadRequest(_("X took the upload but named no media id"))
		return media_id

	@classmethod
	def append_media(cls, account: Account, media_id: str, index: int, chunk: bytes) -> None:
		"""One chunk. It goes as a form, not as JSON, because this call carries the bytes."""
		cls.request(
			"POST",
			cls.MEDIA_APPEND_URL.format(id=media_id),
			account.token_cache,
			post_name=account.post_name,
			data={"segment_index": index},
			files={"media": chunk},
		)

	@classmethod
	def finalize_media(cls, account: Account, media_id: str) -> None:
		"""Tell X the file is all there, then wait if it has work to do on it.

		An image is ready the moment it lands. A video is transcoded, and a tweet that names
		one too early is refused, so `processing_info` decides whether this waits.
		"""
		response = cls.request(
			"POST",
			cls.MEDIA_FINALIZE_URL.format(id=media_id),
			account.token_cache,
			post_name=account.post_name,
		)
		cls.wait_for_media(account, media_id, response.json().get("data", {}).get("processing_info"))

	@classmethod
	def wait_for_media(cls, account: Account, media_id: str, processing: dict | None) -> None:
		"""Until X says the file can be tweeted, or until waiting is pointless."""
		waited = 0
		while processing and processing.get("state") not in ("succeeded", None):
			if processing.get("state") == "failed":
				raise BadRequest(_("X could not process the file: {0}").format(processing.get("error")))
			# X says when to come back; its own wait is the one to keep.
			pause = int(processing.get("check_after_secs") or MEDIA_POLL_SECONDS)
			if waited + pause > MEDIA_WAIT_SECONDS:
				raise Retryable(_("X is still processing the file"))
			time.sleep(pause)
			waited += pause
			processing = (
				cls.request(
					"GET",
					cls.MEDIA_URL,
					account.token_cache,
					params={"command": "STATUS", "media_id": media_id},
				)
				.json()
				.get("data", {})
				.get("processing_info")
			)

	@classmethod
	def error_for(cls, response: requests.Response) -> SocialError:
		"""X says 403 to a post it will not take, not to a token it does not like.

		The same text twice is the common one, and that is the writing to change rather
		than the connection to mend, so a 403 here is a refusal and not a reconnect.
		"""
		if response.status_code == 403:
			return BadRequest(_("X said 403: {0}").format(response.text[:500]))
		return super().error_for(response)

	@classmethod
	def active_token(cls, app: Document, user: str) -> Document | None:
		"""The live token of the account, renewed when it is nearly out.

		X rotates the refresh token on every call, so the answer to one refresh kills the
		token the other worker is holding. The lock keeps them in line, as
		`ConnectedApp.get_active_token` does for the platforms the framework can refresh.
		"""
		name = f"{app.name}-{user}"
		if not frappe.db.exists("Token Cache", name):
			return None

		token_cache = frappe.get_doc("Token Cache", name)
		if token_cache.get_expires_in() > REFRESH_MARGIN_SECONDS:
			return token_cache

		with filelock(f"x_token_cache_{name}"):
			# The worker that held the lock may have renewed it already.
			token_cache.reload()
			if token_cache.get_expires_in() > REFRESH_MARGIN_SECONDS:
				return token_cache
			return cls.refresh(app, token_cache)

	@classmethod
	def refresh(cls, app: Document, token_cache: Document) -> Document | None:
		"""Trade the refresh token for a new pair. Returns nothing when there is none to trade."""
		refresh_token = token_cache.get_password("refresh_token", False)
		if not refresh_token:
			return None
		token = cls.fetch_token(app, grant_type="refresh_token", refresh_token=refresh_token)
		return token_cache.update_data(token)

	@classmethod
	def fetch_token(cls, app: Document, **data: str) -> dict:
		"""Ask the token endpoint for a token.

		X authenticates the app itself with HTTP Basic, so the secret never rides in the
		body. This call carries no bearer token, which is why it does not go through
		`Provider.request`.
		"""
		try:
			response = requests.post(
				app.token_uri,
				data=data,
				auth=(app.client_id, app.get_password("client_secret")),
				timeout=cls.timeout,
			)
		except requests.RequestException as error:
			raise Retryable(_("X did not answer: {0}").format(error)) from error

		if not response.ok:
			raise cls.token_error(response)
		return response.json()

	@classmethod
	def token_error(cls, response: requests.Response) -> Exception:
		"""A refused token call. The grant is gone for good, so this asks for a reconnect
		rather than sending the user round the same failing loop."""
		message = _("X said {0}: {1}").format(response.status_code, response.text[:500])
		if response.status_code in (400, 401, 403):
			return ReconnectRequired(message)
		if response.status_code == 429 or response.status_code >= 500:
			return Retryable(message)
		return BadRequest(message)


def media_type(item: dict) -> str:
	"""The MIME type of a file. X wants it before the bytes arrive."""
	guess, _encoding = mimetypes.guess_type(item.get("file_url") or "")
	return guess or ("video/mp4" if item.get("kind") == "video" else "image/jpeg")


def media_category(item: dict) -> str:
	"""What the file is for. X keeps a different pipeline per category."""
	if item.get("kind") == "video":
		return "tweet_video"
	return "tweet_gif" if media_type(item) == "image/gif" else "tweet_image"
