"""Open and click tracking in newsletter emails. See slice 10 in specs/01-email-list.md."""

import base64
import hashlib
import hmac
import re
from html import escape, unescape
from urllib.parse import urlencode, urlparse

from frappe.utils import get_url
from frappe.utils.verified_command import get_secret
from werkzeug.wrappers import Response

from bwh_os.mailing.lead_magnet_page import ROUTE_PREFIX

LINK_HREF = re.compile(r'(<a\b[^>]*?\bhref\s*=\s*")([^"]*)(")', re.IGNORECASE)
TRACKED_SCHEMES = ("http://", "https://")
# A transparent 1x1 GIF
PIXEL_GIF = base64.b64decode("R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7")


class EmailTracking:
	"""Makes the tracking links and the pixel for one delivery."""

	def __init__(self, delivery: str):
		self.delivery = delivery

	def rewrite_links(self, html: str) -> str:
		"""Point every web link at the click redirect. Other links (mailto:, #) stay as they are.

		The download link is the one exception. It carries a different URL for every reader, so
		click tracking would turn it into thousands of one-click "top links" instead of one. The
		real event is already `Lead Magnet Download`, which is the better number anyway.
		"""

		def rewrite(match: re.Match) -> str:
			url = unescape(match.group(2)).strip()
			if not url.lower().startswith(TRACKED_SCHEMES) or is_download_link(url):
				return match.group(0)
			return match.group(1) + escape(self.click_url(url)) + match.group(3)

		return LINK_HREF.sub(rewrite, html)

	def click_url(self, url: str) -> str:
		params = urlencode({"delivery": self.delivery, "url": url, "signature": sign(self.delivery, url)})
		return get_url(f"/api/method/bwh_os.mailing.api.track_click?{params}")

	def pixel(self) -> str:
		src = get_url(f"/api/method/bwh_os.mailing.api.track_open?delivery={self.delivery}")
		return (
			f'<img src="{escape(src)}" width="1" height="1" alt="" '
			'style="display:block;width:1px;height:1px;border:0;overflow:hidden">'
		)

	def unsubscribe_url(self, subscriber_url: str) -> str:
		"""The subscriber's link, plus the delivery, so the issue report counts the unsubscribe."""
		return f"{subscriber_url}&delivery={self.delivery}"


def is_download_link(url: str) -> bool:
	return urlparse(url).path.strip("/").startswith(ROUTE_PREFIX)


def sign(delivery: str, url: str) -> str:
	"""The click endpoint redirects only to URLs that we signed, so it is not an open redirect."""
	message = f"{delivery}\n{url}".encode()
	return hmac.new(get_secret().encode(), message, hashlib.sha256).hexdigest()[:32]


def is_signed(delivery: str, url: str, signature: str) -> bool:
	return hmac.compare_digest(sign(delivery, url), signature or "")


def pixel_response() -> Response:
	return Response(
		PIXEL_GIF,
		mimetype="image/gif",
		# Every load is an open, so no client or proxy may cache the image.
		headers={"Cache-Control": "no-store, no-cache, must-revalidate, max-age=0", "Pragma": "no-cache"},
	)
