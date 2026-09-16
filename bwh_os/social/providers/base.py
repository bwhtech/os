"""What every platform can do, and what can go wrong. See specs/04-social-posts.md."""

from abc import ABC, abstractmethod
from typing import ClassVar

import frappe
import requests
from frappe import _
from frappe.model.document import Document


class SocialError(frappe.ValidationError):
	"""A call to a platform did not work out."""


class ReconnectRequired(SocialError):
	"""The token is gone or too old. Only the user can fix it, by connecting again."""


class BadRequest(SocialError):
	"""The platform refused what we sent. Sending it again changes nothing."""


class Retryable(SocialError):
	"""The platform was busy or unreachable. The same call may work later."""


class Provider(ABC):
	"""One platform. A subclass holds the endpoints and the shape of its requests."""

	key: ClassVar[str]
	timeout: ClassVar[int] = 30

	# What the platform takes in one part. Postiz learnt these the hard way, so the
	# numbers and the rules below follow `gitroomhq/postiz-app`.
	max_length: ClassVar[int]
	max_images: ClassVar[int]
	max_videos: ClassVar[int] = 1
	# A LinkedIn comment and an X reply differ here: LinkedIn takes text only.
	media_after_part_one: ClassVar[bool] = True

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

		videos = [item for item in media if item.get("kind") == "video"]
		images = [item for item in media if item.get("kind") != "video"]
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
	def request(cls, method: str, url: str, token_cache: Document, **kwargs) -> requests.Response:
		"""A call to the platform with the token of a channel, with the failures named."""
		headers = {**token_cache.get_auth_header(), **kwargs.pop("headers", {})}
		try:
			response = requests.request(method, url, headers=headers, timeout=cls.timeout, **kwargs)
		except requests.RequestException as error:
			raise Retryable(_("{0} did not answer: {1}").format(cls.key, error)) from error

		if not response.ok:
			raise cls.error_for(response)
		return response

	@classmethod
	def error_for(cls, response: requests.Response) -> SocialError:
		"""Turn a failed response into the error that says what to do about it."""
		message = _("{0} said {1}: {2}").format(cls.key, response.status_code, response.text[:500])
		if response.status_code in (401, 403):
			return ReconnectRequired(message)
		if response.status_code == 429 or response.status_code >= 500:
			return Retryable(message)
		return BadRequest(message)
