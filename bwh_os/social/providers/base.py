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

	@classmethod
	@abstractmethod
	def identity(cls, token_cache: Document) -> dict:
		"""Who the token belongs to.

		Returns `account_id`, `display_name`, `handle`, `avatar_url` and `profile_url`.
		The channel is named after `account_id`, so it has to be the id that never changes.
		"""

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
