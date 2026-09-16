"""Every platform the OS can post to, by the name on `Social Channel.provider`."""

import frappe
from frappe import _

from bwh_os.social.providers.base import (
	Account,
	BadRequest,
	Provider,
	ReconnectRequired,
	Release,
	Retryable,
	SocialError,
)
from bwh_os.social.providers.linkedin import LinkedInProvider

__all__ = [
	"Account",
	"BadRequest",
	"Provider",
	"ReconnectRequired",
	"Release",
	"Retryable",
	"SocialError",
	"get_provider",
]

PROVIDERS: dict[str, type[Provider]] = {
	"LinkedIn": LinkedInProvider,
}


def get_provider(provider: str) -> type[Provider]:
	"""The class that talks to a platform."""
	if provider not in PROVIDERS:
		frappe.throw(_("The OS cannot post to {0} yet").format(provider))
	return PROVIDERS[provider]
