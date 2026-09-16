"""Social channels and posts for the OS. See specs/04-social-posts.md."""

import frappe
from frappe.utils import date_diff, now_datetime

from bwh_os.social.oauth_apps import PROVIDERS, get_app, redirect_uri

CHANNEL_FIELDS = [
	"name",
	"provider",
	"display_name",
	"handle",
	"avatar_url",
	"profile_url",
	"status",
	"connected_on",
	"expires_on",
	"last_error",
]


@frappe.whitelist(methods=["GET"])
def get_channels() -> list[dict]:
	"""Every channel with the days left on its token, for the Settings panel."""
	frappe.only_for("System Manager")
	channels = frappe.get_all("Social Channel", fields=CHANNEL_FIELDS, order_by="provider asc")
	today = now_datetime()
	for channel in channels:
		channel["days_left"] = date_diff(channel.expires_on, today) if channel.expires_on else None
	return channels


@frappe.whitelist(methods=["GET"])
def get_provider_apps() -> list[dict]:
	"""The OAuth app of each platform, with the URI to register and whether it can connect yet."""
	frappe.only_for("System Manager")
	apps = []
	for provider in PROVIDERS:
		app = get_app(provider)
		apps.append(
			{
				"provider": provider,
				"app": app.name,
				"redirect_uri": redirect_uri(provider, app),
				"scopes": [row.scope for row in app.scopes],
				"client_id": app.client_id,
				"has_credentials": bool(app.client_id and app.get_password("client_secret", False)),
			}
		)
	return apps


@frappe.whitelist(methods=["POST"])
def set_credentials(provider: str, client_id: str, client_secret: str = "") -> None:
	"""Save the client id and secret of a platform. An empty secret keeps the saved one."""
	frappe.only_for("System Manager")
	app = get_app(provider)
	app.client_id = client_id.strip()
	if client_secret:
		app.client_secret = client_secret
	app.save(ignore_permissions=True)
