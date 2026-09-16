"""Reading the token of a channel. See specs/04-social-posts.md.

Every platform keeps its token in the framework `Token Cache`, so the publisher
reads tokens one way whatever the platform is.
"""

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import add_to_date

from bwh_os.social.providers import ReconnectRequired

# `Token Cache.is_expired()` has no margin, so a token with seconds left counts as
# live. An upload takes longer than that. Treat the last two minutes as expired.
SKEW_SECONDS = 120


def get_token(channel: Document) -> Document:
	"""The live token of a channel, refreshed when the platform allows it.

	Raises `ReconnectRequired` and marks the channel when the token cannot be had.
	LinkedIn gives no refresh token, so its tokens end this way every 60 days.
	"""
	app = frappe.get_doc("Connected App", channel.connected_app)
	token_cache = app.get_active_token(channel.user)
	if not token_cache:
		channel.mark_expired(_("The token has run out. Connect {0} again.").format(channel.provider))
		raise ReconnectRequired(_("{0} needs a new connection").format(channel.provider))

	if token_cache.get_expires_in() < SKEW_SECONDS:
		channel.mark_expired(_("The token runs out now. Connect {0} again.").format(channel.provider))
		raise ReconnectRequired(_("{0} needs a new connection").format(channel.provider))

	return token_cache


def expires_on(token_cache: Document) -> str | None:
	"""When the token dies. `Token Cache` counts from its own `modified`, so this does too."""
	if not token_cache.expires_in:
		return None
	return add_to_date(token_cache.modified, seconds=token_cache.expires_in)
