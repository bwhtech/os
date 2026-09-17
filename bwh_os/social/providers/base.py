"""What every platform can do, and what can go wrong. See specs/04-social-posts.md."""

from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass
from typing import ClassVar

import frappe
import requests
from frappe import _
from frappe.integrations.utils import create_request_log
from frappe.model.document import Document


class SocialError(frappe.ValidationError):
	"""A call to a platform did not work out."""


class ReconnectRequired(SocialError):
	"""The token is gone or too old. Only the user can fix it, by connecting again."""


class BadRequest(SocialError):
	"""The platform refused what we sent. Sending it again changes nothing."""


class Retryable(SocialError):
	"""The platform was busy or unreachable. The same call may work later."""


@dataclass(frozen=True)
class Account:
	"""Who the post goes out as. The publisher reads the token, so no provider has to."""

	token_cache: Document
	account_id: str
	# The post the calls belong to, for the `Integration Request` records.
	post_name: str


@dataclass(frozen=True)
class Release:
	"""One part that made it onto the platform."""

	part_no: int
	id: str
	url: str | None = None

	def as_dict(self) -> dict:
		return {"part_no": self.part_no, "id": self.id, "url": self.url}


class Provider(ABC):
	"""One platform. A subclass holds the endpoints and the shape of its requests."""

	key: ClassVar[str]
	timeout: ClassVar[int] = 30

	# What the platform takes in one part. Postiz learnt these the hard way, so the
	# numbers and the rules below follow `gitroomhq/postiz-app`.
	max_length: ClassVar[int]
	max_images: ClassVar[int]
	max_videos: ClassVar[int] = 1
	# What the platform takes in one video. The site's own `max_file_size` sits above this.
	max_video_bytes: ClassVar[int] = 512 * 1024 * 1024
	# What the platform takes in one image. LinkedIn's number, which is the looser of the two.
	max_image_bytes: ClassVar[int] = 36 * 1024 * 1024
	# A LinkedIn comment and an X reply differ here: LinkedIn takes text only.
	media_after_part_one: ClassVar[bool] = True
	# Whether the life of the token is the life of the connection. It is for LinkedIn,
	# which gives no way to renew one; a platform that refreshes in the background has
	# nothing to count down to, so its channel keeps no expiry and gets no reminder.
	connection_expires: ClassVar[bool] = True

	@classmethod
	@abstractmethod
	def identity(cls, token_cache: Document) -> dict:
		"""Who the token belongs to.

		Returns `account_id`, `display_name`, `handle`, `avatar_url` and `profile_url`.
		The channel is named after `account_id`, so it has to be the id that never changes.
		"""

	@classmethod
	def count(cls, text: str) -> int:
		"""What the platform counts as the length of a text. X weighs its characters."""
		return len(text or "")

	@classmethod
	def validate(cls, parts: list[dict], settings: dict | None = None) -> list[str]:
		"""Everything wrong with this content, in the words the composer shows.

		`parts` are dicts of `text` and `media`, part 1 first. An empty list is a
		problem of the post, not of the platform, so the caller reports that one.
		"""
		problems = []
		for index, part in enumerate(parts):
			problems += cls.validate_part(part, part_no=index + 1)
		return problems

	@classmethod
	def validate_part(cls, part: dict, part_no: int) -> list[str]:
		problems = []
		text = part.get("text") or ""
		media = part.get("media") or []
		length = cls.count(text)
		if not text.strip() and not media:
			problems.append(_("Part {0} is empty").format(part_no))
		if length > cls.max_length:
			problems.append(
				_("Part {0} is {1} characters. {2} takes {3}.").format(
					part_no, length, cls.key, cls.max_length
				)
			)

		if media and part_no > 1 and not cls.media_after_part_one:
			problems.append(_("A {0} comment takes text only").format(cls.key))
			return problems

		videos = videos_of(media)
		images = images_of(media)
		if videos and len(media) > 1:
			# Postiz: a video goes on its own, whatever the platform allows for images.
			problems.append(_("Part {0} can hold a video or images, not both").format(part_no))
		if len(videos) > cls.max_videos:
			problems.append(
				_("Part {0} has {1} videos. {2} takes {3}.").format(
					part_no, len(videos), cls.key, cls.max_videos
				)
			)
		if len(images) > cls.max_images:
			problems.append(
				_("Part {0} has {1} images. {2} takes {3}.").format(
					part_no, len(images), cls.key, cls.max_images
				)
			)
		return problems

	@classmethod
	def upload_media(cls, account: Account, media: list[dict]) -> list[str]:
		"""Put each file on the platform and give back the ids the post refers to.

		Media goes up before the post does, because both platforms take an id, never a file.
		"""
		raise NotImplementedError

	@classmethod
	@abstractmethod
	def post(
		cls,
		account: Account,
		parts: list[dict],
		settings: dict,
		released: list[dict],
		on_release: Callable[[Release], None],
	) -> None:
		"""Put each part on the platform, oldest first.

		A part already in `released` is skipped, so a job that died halfway carries on
		where it stopped. `on_release` runs after each part and is what makes that work:
		it writes the part down before the next call goes out.
		"""

	@classmethod
	def request(
		cls, method: str, url: str, token_cache: Document, post_name: str | None = None, **kwargs
	) -> requests.Response:
		"""A call to the platform with the token of a channel, with the failures named.

		A call that writes keeps an `Integration Request`, so every post has a record of
		what went out and what came back.
		"""
		headers = {**token_cache.get_auth_header(), **kwargs.pop("headers", {})}
		log = cls.log_request(method, url, post_name, kwargs.get("json"))
		try:
			response = requests.request(method, url, headers=headers, timeout=cls.timeout, **kwargs)
		except requests.RequestException as error:
			finish_log(log, "Failed", str(error))
			raise Retryable(_("{0} did not answer: {1}").format(cls.key, error)) from error

		finish_log(log, "Completed" if response.ok else "Failed", response.text[:5000])
		if not response.ok:
			raise cls.error_for(response)
		return response

	@classmethod
	def log_request(cls, method: str, url: str, post_name: str | None, data) -> Document | None:
		"""A record of one write call. Reads are noise, so they keep none."""
		if method == "GET" or not post_name:
			return None
		return create_request_log(
			data or {},
			service_name=cls.key,
			url=url,
			reference_doctype="Social Post",
			reference_docname=post_name,
			is_remote_request=True,
		)

	@classmethod
	def error_for(cls, response: requests.Response) -> SocialError:
		"""Turn a failed response into the error that says what to do about it."""
		message = _("{0} said {1}: {2}").format(cls.key, response.status_code, response.text[:500])
		if response.status_code in (401, 403):
			return ReconnectRequired(message)
		if response.status_code == 429 or response.status_code >= 500:
			return Retryable(message)
		return BadRequest(message)


def file_bytes(file_url: str) -> bytes:
	"""The content of one piece of media. It lives in a private `File` on the post."""
	name = frappe.db.get_value("File", {"file_url": file_url})
	if not name:
		raise BadRequest(_("{0} is not on the post any more").format(file_url))
	content = frappe.get_doc("File", name).get_content()
	return content.encode() if isinstance(content, str) else content


def images_of(media: list[dict]) -> list[dict]:
	"""The images of a part. A video takes another road, and never shares a part."""
	return [item for item in media if item.get("kind") != "video"]


def videos_of(media: list[dict]) -> list[dict]:
	return [item for item in media if item.get("kind") == "video"]


def finish_log(log: Document | None, status: str, output: str) -> None:
	"""Close an `Integration Request` with what the platform said."""
	if not log:
		return
	log.db_set({"status": status, "output": output}, commit=False)
