"""LinkedIn, the personal profile. See specs/04-social-posts.md."""

from frappe.model.document import Document

from bwh_os.social.providers.base import Provider


class LinkedInProvider(Provider):
	key = "LinkedIn"

	max_length = 3000
	# `multiImage` holds 20. A comment on a personal post is text, so media stops at part 1.
	max_images = 20
	media_after_part_one = False

	USERINFO_URL = "https://api.linkedin.com/v2/userinfo"

	@classmethod
	def identity(cls, token_cache: Document) -> dict:
		"""The person behind the token. `sub` is the id that goes into `urn:li:person:{sub}`."""
		data = cls.request("GET", cls.USERINFO_URL, token_cache).json()
		return {
			"account_id": data["sub"],
			"display_name": data.get("name"),
			# A personal profile has no handle, and the vanity name needs a scope we do not ask for.
			"handle": None,
			"avatar_url": data.get("picture"),
			"profile_url": None,
		}
