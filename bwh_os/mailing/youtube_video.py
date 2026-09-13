"""The YouTube video block in the email editor. See slice 13 in specs/01-email-list.md.

Email clients do not play video, so the block is a thumbnail that links to YouTube. Many clients
also drop CSS overlays, so the play button is drawn into the thumbnail image.
"""

import io
import re

import frappe
import requests
from frappe import _
from frappe.utils import get_url
from PIL import Image, ImageDraw

VIDEO_ID = re.compile(r"(?:youtube\.com/(?:watch\?(?:\S*&)?v=|shorts/|live/|embed/)|youtu\.be/)([\w-]{11})")
OEMBED_URL = "https://www.youtube.com/oembed"
# The largest thumbnail first. Old and small videos have no maxresdefault.
THUMBNAILS = ("maxresdefault", "hqdefault")
TIMEOUT = 10

PLAY_RED = (255, 0, 0, 235)
# Draw the button this many times bigger, then scale down, for smooth edges.
SUPERSAMPLE = 4


def get_video(url: str) -> dict:
	"""The title, link, and thumbnail with a play button for a YouTube URL."""
	video_id = parse_video_id(url)
	watch_url = f"https://www.youtube.com/watch?v={video_id}"
	return {
		"video_id": video_id,
		"url": watch_url,
		"title": fetch_title(watch_url),
		"thumbnail": get_url(thumbnail_file_url(video_id)),
	}


def parse_video_id(url: str) -> str:
	match = VIDEO_ID.search(url or "")
	if not match:
		frappe.throw(_("Paste a link to a YouTube video"))
	return match.group(1)


def fetch_title(watch_url: str) -> str:
	response = requests.get(OEMBED_URL, params={"url": watch_url, "format": "json"}, timeout=TIMEOUT)
	if response.status_code in (401, 403, 404):
		frappe.throw(_("YouTube did not find this video, or the video is private"))
	response.raise_for_status()
	return response.json()["title"]


def thumbnail_file_url(video_id: str) -> str:
	"""A public file of the thumbnail with a play button. Made once for each video."""
	file_name = f"youtube-{video_id}.jpg"
	if file_url := frappe.db.get_value("File", {"file_name": file_name, "is_private": 0}, "file_url"):
		return file_url
	file = frappe.get_doc(
		{
			"doctype": "File",
			"file_name": file_name,
			"is_private": 0,
			"content": with_play_button(download_thumbnail(video_id)),
		}
	).insert()
	return file.file_url


def download_thumbnail(video_id: str) -> Image.Image:
	for size in THUMBNAILS:
		response = requests.get(f"https://img.youtube.com/vi/{video_id}/{size}.jpg", timeout=TIMEOUT)
		if response.ok:
			return crop_to_widescreen(Image.open(io.BytesIO(response.content)).convert("RGB"))
	frappe.throw(_("YouTube has no thumbnail for this video"))


def crop_to_widescreen(image: Image.Image) -> Image.Image:
	"""hqdefault is 4:3 with black bars above and below a 16:9 video."""
	width, height = image.size
	target = round(width * 9 / 16)
	if height <= target:
		return image
	top = (height - target) // 2
	return image.crop((0, top, width, top + target))


def with_play_button(image: Image.Image) -> bytes:
	"""A YouTube-style play button in the center of the image, as JPEG bytes."""
	width, height = image.size
	button_width = round(width * 0.12)
	button_height = round(button_width * 0.7)

	button = Image.new("RGBA", (button_width * SUPERSAMPLE, button_height * SUPERSAMPLE))
	draw = ImageDraw.Draw(button)
	big_width, big_height = button.size
	draw.rounded_rectangle((0, 0, big_width - 1, big_height - 1), radius=big_height // 4, fill=PLAY_RED)
	side = big_height * 0.42
	left = (big_width - side * 0.87) / 2
	top = (big_height - side) / 2
	draw.polygon([(left, top), (left, top + side), (left + side * 0.87, big_height / 2)], fill="white")
	button = button.resize((button_width, button_height), Image.Resampling.LANCZOS)

	image.paste(button, ((width - button_width) // 2, (height - button_height) // 2), button)
	output = io.BytesIO()
	image.save(output, format="JPEG", quality=85)
	return output.getvalue()
