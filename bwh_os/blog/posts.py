"""Post titles for the blog. The blog sends only post ids, so the titles come from its feed."""

import xml.etree.ElementTree as ET
from urllib.parse import urlparse

import frappe
import requests

BLOG_URL = "https://bwh.tech/blog"
FEED_URL = "https://bwh.tech/rss.xml"
CACHE_KEY = "bwh_os:blog_post_titles"
CACHE_SECONDS = 60 * 60
# A failed fetch is cached for a short time, so a feed outage does not slow every comment.
FAILED_CACHE_SECONDS = 5 * 60
TIMEOUT = 5


def get_post_titles() -> dict[str, str]:
	"""Titles by post id, for example `stories/one-year`. Empty when the feed cannot be read."""
	titles = frappe.cache.get_value(CACHE_KEY)
	if titles is None:
		titles = fetch_post_titles()
		expires = CACHE_SECONDS if titles else FAILED_CACHE_SECONDS
		frappe.cache.set_value(CACHE_KEY, titles, expires_in_sec=expires)
	return titles


def post_url(post_id: str) -> str:
	return f"{BLOG_URL}/{post_id}/"


def fetch_post_titles() -> dict[str, str]:
	try:
		response = requests.get(FEED_URL, timeout=TIMEOUT)
		response.raise_for_status()
		items = ET.fromstring(response.content).iter("item")
	except (requests.RequestException, ET.ParseError):
		frappe.log_error("Could not read the blog feed")
		return {}
	return {post_id_of(item.findtext("link", "")): item.findtext("title", "") for item in items}


def post_id_of(link: str) -> str:
	"""`https://bwh.tech/blog/stories/one-year/` becomes `stories/one-year`."""
	return urlparse(link).path.removeprefix("/blog/").strip("/")
