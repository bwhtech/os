"""X, the personal account. See specs/04-social-posts.md.

The token endpoint of X lives here rather than in the framework. `Connected App` signs
its calls the way `requests_oauthlib` does, with the client id in the body and no PKCE,
and X answers that with a refusal. Both legs of the connect come through this class: the
browser leg in `bwh_os/social/x_oauth.py`, and every later refresh from
`bwh_os.social.tokens`.

A post goes out as a thread: part 1 is a tweet, and each part after it replies to the one
before, which is how X itself makes one.
"""

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


class XProvider(Provider):
	key = "X"

	max_length = 280
	max_images = 4

	USERS_ME_URL = "https://api.x.com/2/users/me?user.fields=profile_image_url,username,name"
	PROFILE_URL = "https://x.com/{handle}"
	TWEETS_URL = "https://api.x.com/2/tweets"
	# The handle is not on the account the publisher carries, and X redirects `i` to it.
	TWEET_URL = "https://x.com/i/status/{id}"

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
		# Images and video come in slice 4.3. Until then a post that carries one would go
		# out as text, which is not what anyone wrote, so it does not go out at all.
		if any(part.get("media") for part in parts):
			problems.append(_("The OS cannot put media on X yet"))
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
				account, part.get("text") or "", reply_to=previous, reply_settings=reply_settings
			)
			on_release(Release(part_no=part_no, id=previous, url=cls.TWEET_URL.format(id=previous)))

	@classmethod
	def create_tweet(
		cls,
		account: Account,
		text: str,
		reply_to: str | None = None,
		reply_settings: str | None = None,
	) -> str:
		body: dict = {"text": text}
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
