"""Connecting an account of a platform. See specs/04-social-posts.md.

LinkedIn runs the web flow of the framework `Connected App`. That flow saves the
token and then sends the browser to `success_uri`, which is where this module
takes over: it asks the platform who the token belongs to and writes the channel.
"""

import frappe
from frappe import _
from frappe.utils import now_datetime

from bwh_os.social.oauth_apps import get_app
from bwh_os.social.providers import get_provider
from bwh_os.social.tokens import expires_on

# Where the `Connected App` flow sends the browser once it holds the token.
LINKEDIN_SUCCESS_URI = "/api/method/bwh_os.social.oauth.linkedin_connected"


@frappe.whitelist(methods=["GET"])
def linkedin_connected() -> None:
	"""The last step of the LinkedIn connect. Writes the channel and goes back to the OS."""
	frappe.only_for("System Manager")
	provider = "LinkedIn"
	upsert_channel(provider, frappe.session.user)
	frappe.local.response["type"] = "redirect"
	frappe.local.response["location"] = f"/os/social?connected={provider}"


def upsert_channel(provider: str, user: str) -> str:
	"""Write the channel of the account that just connected, and return its name.

	A reconnect lands on the same row, because the channel is named after the
	account id. So the posts of a channel survive a reconnect.
	"""
	app = get_app(provider)
	token_cache_name = f"{app.name}-{user}"
	if not frappe.db.exists("Token Cache", token_cache_name):
		frappe.throw(_("{0} sent no token. Start the connect again.").format(provider))

	token_cache = frappe.get_doc("Token Cache", token_cache_name)
	identity = get_provider(provider).identity(token_cache)

	name = f"{provider}-{identity['account_id']}"
	channel = (
		frappe.get_doc("Social Channel", name)
		if frappe.db.exists("Social Channel", name)
		else frappe.new_doc("Social Channel")
	)
	channel.update(
		{
			"provider": provider,
			**identity,
			"user": user,
			"connected_app": app.name,
			"token_cache": token_cache.name,
			"status": "Connected",
			"connected_on": now_datetime(),
			"expires_on": expires_on(token_cache),
			"last_error": None,
			"reminder_sent_on": None,
		}
	)
	channel.save(ignore_permissions=True)
	return channel.name
