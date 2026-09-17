"""X, the personal account. See specs/04-social-posts.md.

The token endpoint of X lives here rather than in the framework. `Connected App` signs
its calls the way `requests_oauthlib` does, with the client id in the body and no PKCE,
and X answers that with a refusal. Both legs of the connect come through this class: the
browser leg in `bwh_os/social/x_oauth.py`, and every later refresh from
`bwh_os.social.tokens`.

X is not in `PROVIDERS` yet, so nothing can post to it and the composer says so. Slice
4.2 writes the posting and puts it there.
"""

import frappe
import requests
from frappe import _
from frappe.model.document import Document
from frappe.utils.synchronization import filelock

from bwh_os.social.providers.base import (
	BadRequest,
	Provider,
	ReconnectRequired,
	Retryable,
)

# An X access token lives two hours. Refresh it before the last minutes, so a long upload
# that started on a healthy token does not end on a dead one. This sits above the margin
# `bwh_os.social.tokens` calls expired, or a token would be refused before it is renewed.
REFRESH_MARGIN_SECONDS = 300


class XProvider(Provider):
	key = "X"

	# Weighted characters, which slice 4.2 counts properly. Until then `count` is the
	# plain length of the base class and nothing posts here anyway.
	max_length = 280
	max_images = 4

	USERS_ME_URL = "https://api.x.com/2/users/me?user.fields=profile_image_url,username,name"
	PROFILE_URL = "https://x.com/{handle}"

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
