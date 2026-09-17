"""What a post must look like before it goes out. See specs/04-social-posts.md.

Two passes. The structure pass runs on every save and keeps the document sane: one row
per channel, parts numbered from 1, no content left behind by a target that is gone. The
strict pass runs before a schedule or a publish, and asks each platform whether it would
take this content. The composer shows the same answers while you type, so nothing waits
for the publish to say a text is too long.
"""

import json

import frappe
from frappe import _
from frappe.model.document import Document

from bwh_os.social.providers import PROVIDERS, get_provider

MEDIA_KINDS = ("image", "video")


def unsupported(provider: str) -> str:
	return _("The OS cannot post to {0} yet").format(provider)


class PostValidator:
	"""The rules of one `Social Post`."""

	def __init__(self, post: Document):
		self.post = post

	def structure(self) -> None:
		"""Clean up the tables and refuse what no platform could read. Runs on save."""
		self.check_one_row_per_channel()
		self.drop_orphan_parts()
		self.number_parts()
		self.check_media_json()

	def check(self) -> None:
		"""The strict pass. Throws the first problem, for Schedule and Publish."""
		if not self.post.targets:
			frappe.throw(_("Pick a channel to post to"))

		for result in self.results():
			if result["errors"]:
				frappe.throw(_("{0}: {1}").format(result["provider"], result["errors"][0]))

	def results(self) -> list[dict]:
		"""One result per target, for the composer. Nothing throws, so every target reports."""
		return [self.result_for(target) for target in self.post.targets]

	def result_for(self, target: Document) -> dict:
		parts = self.parts_for(target)
		name = self.provider_name(target)
		if name not in PROVIDERS:
			# One channel the OS cannot post to yet is that channel's problem, not the post's:
			# the composer keeps working for the others and says what this one is waiting for.
			return self.result(target, name, limit=0, counts=[], errors=[unsupported(name)])

		provider = get_provider(name)
		errors = [] if parts else [_("Write the post first")]
		errors += provider.validate(parts, self.settings_of(target))
		errors += self.media_errors(parts, provider)
		errors += self.channel_errors(target)
		return self.result(
			target,
			name,
			limit=provider.max_length,
			counts=[provider.count(part["text"]) for part in parts],
			errors=errors,
			max_images=provider.max_images,
			media_after_part_one=provider.media_after_part_one,
		)

	def result(
		self,
		target: Document,
		provider: str,
		*,
		limit: int,
		counts: list[int],
		errors: list[str],
		max_images: int = 0,
		media_after_part_one: bool = False,
	) -> dict:
		"""One target's verdict, in the shape the composer reads."""
		return {
			"channel": target.channel,
			"provider": provider,
			"use_custom_content": bool(target.use_custom_content),
			"limit": limit,
			"max_images": max_images,
			"media_after_part_one": media_after_part_one,
			"counts": counts,
			"errors": errors,
		}

	def provider_name(self, target: Document) -> str:
		"""`provider` rides along with the channel, but a document the browser sent never
		ran the fetch, so the channel answers for it."""
		return target.provider or frappe.db.get_value("Social Channel", target.channel, "provider")

	def channel_errors(self, target: Document) -> list[str]:
		status = frappe.db.get_value("Social Channel", target.channel, "status")
		if status == "Connected":
			return []
		return [_("The channel is {0}. Connect it again in Settings.").format(status or _("gone"))]

	def parts_for(self, target: Document) -> list[dict]:
		"""The content this target publishes: its own parts, or else the shared ones."""
		channel = target.channel if target.use_custom_content else None
		rows = sorted(
			(row for row in self.post.parts if (row.channel or None) == channel),
			key=lambda row: row.part_no,
		)
		return [{"text": row.text or "", "media": media_of(row)} for row in rows]

	def media_errors(self, parts: list[dict], provider) -> list[str]:
		"""What is wrong with the files themselves: one that left the post, one too big."""
		items = [item for part in parts for item in part["media"]]
		if not items:
			return []

		sizes = {
			row.file_url: row.file_size
			for row in frappe.get_all(
				"File",
				filters={"file_url": ("in", [item.get("file_url") for item in items])},
				fields=["file_url", "file_size"],
			)
		}
		problems = []
		for item in items:
			url = item.get("file_url")
			if url not in sizes:
				problems.append(_("{0} is not on the post any more").format(url))
			elif item.get("kind") == "video" and sizes[url] > provider.max_video_bytes:
				problems.append(
					_("{0} takes a video of {1} MB at most").format(
						provider.key, provider.max_video_bytes // (1024 * 1024)
					)
				)
		return problems

	def settings_of(self, target: Document) -> dict:
		return parse_json(target.settings) or {}

	def check_one_row_per_channel(self) -> None:
		channels = [target.channel for target in self.post.targets]
		if len(channels) != len(set(channels)):
			frappe.throw(_("A post goes to each channel once"))

	def drop_orphan_parts(self) -> None:
		"""Custom content belongs to a target that wants it. The rest is dead weight."""
		custom = {target.channel for target in self.post.targets if target.use_custom_content}
		self.post.parts = [row for row in self.post.parts if not row.channel or row.channel in custom]

	def number_parts(self) -> None:
		"""`part_no` runs from 1 inside each group. `idx` counts the whole table, so it cannot."""
		groups: dict[str | None, int] = {}
		for row in self.post.parts:
			key = row.channel or None
			groups[key] = groups.get(key, 0) + 1
			row.part_no = groups[key]

	def check_media_json(self) -> None:
		for row in self.post.parts:
			for item in media_of(row):
				if not item.get("file_url"):
					frappe.throw(_("A media item has no file"))
				if item.get("kind") not in MEDIA_KINDS:
					frappe.throw(_("{0} is not an image or a video").format(item.get("file_url")))


def media_of(row: Document) -> list[dict]:
	"""The media of a part. The column holds JSON, and the browser may send it as a string."""
	media = parse_json(row.media) or []
	if not isinstance(media, list):
		frappe.throw(_("The media of part {0} is not a list").format(row.part_no))
	return media


def parse_json(value):
	if not value:
		return None
	if isinstance(value, str):
		try:
			return json.loads(value)
		except ValueError:
			frappe.throw(_("Could not read {0}").format(value[:100]))
	return value
