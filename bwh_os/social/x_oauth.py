"""Connecting an X account. See specs/04-social-posts.md.

X wants PKCE, and the framework `Connected App` flow cannot do it, so the browser leg of
the connect lives here: this module makes the verifier, sends the browser to X, and takes
the code back. The token itself goes into `Token Cache` like every other, so the
publisher reads tokens one way. The calls to the token endpoint belong to the provider,
in `bwh_os/social/providers/x.py`.
"""

import base64
import hashlib
import secrets
from urllib.parse import urlencode

import frappe
from frappe import _
from frappe.model.document import Document

from bwh_os.social.oauth import upsert_channel
from bwh_os.social.oauth_apps import get_app, redirect_uri
from bwh_os.social.providers.x import XProvider

PROVIDER = "X"

# How long the browser has to come back from X with the code. Ten minutes covers a
# consent screen that waits for a password manager; after that the connect starts again.
FLOW_TTL_SECONDS = 600

# Where the OS lands once X is done with the browser, one way or the other.
DONE_URI = "/os/social?connected={provider}"
FAILED_URI = "/os/social?connect_failed={provider}"


def start() -> str:
	"""Begin the connect. Returns the URL of X to send the browser to.

	The verifier stays here and the challenge goes to X, so the code X hands back is worth
	nothing to anyone who did not start this.
	"""
	app = get_app(PROVIDER)
	verifier = secrets.token_urlsafe(64)
	state = frappe.generate_hash(length=32)
	frappe.cache.set_value(
		cache_key(state),
		{"verifier": verifier, "user": frappe.session.user},
		expires_in_sec=FLOW_TTL_SECONDS,
	)
	params = {
		"response_type": "code",
		"client_id": app.client_id,
		"redirect_uri": redirect_uri(PROVIDER, app),
		"scope": " ".join(row.scope for row in app.scopes),
		"state": state,
		"code_challenge": challenge_for(verifier),
		"code_challenge_method": "S256",
	}
	return f"{app.authorization_uri}?{urlencode(params)}"


@frappe.whitelist(methods=["GET"])
def callback(code: str | None = None, state: str | None = None, error: str | None = None) -> None:
	"""The last step of the connect. Writes the token and the channel, then goes back to the OS."""
	frappe.only_for("System Manager")
	flow = take_flow(state)
	if error or not code:
		# Saying no on the consent screen is an answer, not a crash. The OS says so.
		frappe.local.response["type"] = "redirect"
		frappe.local.response["location"] = FAILED_URI.format(provider=PROVIDER)
		return

	app = get_app(PROVIDER)
	token = XProvider.fetch_token(
		app,
		grant_type="authorization_code",
		code=code,
		redirect_uri=redirect_uri(PROVIDER, app),
		code_verifier=flow["verifier"],
	)
	store_token(app, frappe.session.user, token)
	upsert_channel(PROVIDER, frappe.session.user, XProvider)

	frappe.local.response["type"] = "redirect"
	frappe.local.response["location"] = DONE_URI.format(provider=PROVIDER)


def take_flow(state: str | None) -> dict:
	"""The connect this callback belongs to, used once.

	The state is dropped as it is read, so a code replayed with the same state finds
	nothing to spend it on.
	"""
	flow = frappe.cache.get_value(cache_key(state)) if state else None
	if state:
		frappe.cache.delete_value(cache_key(state))
	if not flow:
		frappe.throw(_("This connect has gone stale. Start it again from Settings."))
	if flow.get("user") != frappe.session.user:
		frappe.throw(_("This connect was started by someone else"))
	return flow


def store_token(app: Document, user: str, token: dict) -> Document:
	"""Put the token where every platform keeps it. A reconnect writes over the old one."""
	name = f"{app.name}-{user}"
	token_cache = (
		frappe.get_doc("Token Cache", name)
		if frappe.db.exists("Token Cache", name)
		else frappe.new_doc("Token Cache")
	)
	token_cache.user = user
	token_cache.connected_app = app.name
	token_cache.provider_name = PROVIDER
	return token_cache.update_data(token)


def challenge_for(verifier: str) -> str:
	"""The S256 challenge: the SHA-256 of the verifier, base64url and without padding."""
	digest = hashlib.sha256(verifier.encode("ascii")).digest()
	return base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")


def cache_key(state: str) -> str:
	return f"bwh_os:x_oauth:{state}"
