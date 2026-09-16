"""The OAuth app of each platform. See specs/04-social-posts.md.

One `Connected App` per platform holds the endpoints, the scopes, and the client
credentials. `Connected App` has no autoname, so nothing may look one up by name.
Everything here finds it by `provider_name`.
"""

from dataclasses import dataclass, field

import frappe
from frappe import _


@dataclass(frozen=True)
class ProviderApp:
	"""What the code owns on the `Connected App` of a platform. The user owns the credentials."""

	authorization_uri: str
	token_uri: str
	userinfo_uri: str
	scopes: list[str] = field(default_factory=list)
	# The path that takes the callback. Empty means the callback of `Connected App` itself.
	callback_path: str = ""


PROVIDERS: dict[str, ProviderApp] = {
	"LinkedIn": ProviderApp(
		authorization_uri="https://www.linkedin.com/oauth/v2/authorization",
		token_uri="https://www.linkedin.com/oauth/v2/accessToken",
		userinfo_uri="https://api.linkedin.com/v2/userinfo",
		scopes=["openid", "profile", "w_member_social"],
	),
	"X": ProviderApp(
		authorization_uri="https://x.com/i/oauth2/authorize",
		token_uri="https://api.x.com/2/oauth2/token",
		userinfo_uri="https://api.x.com/2/users/me",
		scopes=["tweet.read", "tweet.write", "users.read", "offline.access"],
		# X needs PKCE, which `Connected App` cannot do. See bwh_os/social/x_oauth.py.
		callback_path="/api/method/bwh_os.social.x_oauth.callback",
	),
}


def ensure_connected_apps() -> None:
	"""Make the `Connected App` of each platform, and keep its endpoints in step with the code.

	Runs on install and on migrate. It never touches `client_id` or `client_secret`,
	because those come from the platform console and only the user has them.
	"""
	for provider, app in PROVIDERS.items():
		name = frappe.db.get_value("Connected App", {"provider_name": provider})
		doc = frappe.get_doc("Connected App", name) if name else frappe.new_doc("Connected App")
		if name and _matches(doc, app):
			continue

		doc.provider_name = provider
		doc.authorization_uri = app.authorization_uri
		doc.token_uri = app.token_uri
		doc.userinfo_uri = app.userinfo_uri
		doc.set("scopes", [{"scope": scope} for scope in app.scopes])
		doc.save(ignore_permissions=True)


def _matches(doc: "frappe.Document", app: ProviderApp) -> bool:
	"""Whether the record already says what the code says. Setting the child rows anew
	always makes the document look dirty, so compare the values instead."""
	return (
		doc.authorization_uri == app.authorization_uri
		and doc.token_uri == app.token_uri
		and doc.userinfo_uri == app.userinfo_uri
		and [row.scope for row in doc.scopes] == app.scopes
	)


def get_app(provider: str) -> "frappe.Document":
	"""The `Connected App` of a platform. Throws when install or migrate has not run."""
	name = frappe.db.get_value("Connected App", {"provider_name": provider})
	if not name:
		frappe.throw(_("No Connected App for {0}. Run bench migrate.").format(provider))
	return frappe.get_doc("Connected App", name)


def redirect_uri(provider: str, app_doc: "frappe.Document") -> str:
	"""The URI to register in the console of the platform."""
	path = PROVIDERS[provider].callback_path
	return frappe.utils.get_url(path) if path else app_doc.redirect_uri
