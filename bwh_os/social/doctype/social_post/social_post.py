# Copyright (c) 2026, BWH and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document

from bwh_os.social.validation import PostValidator

# What fits in a list row. A title is a handle for the post, not the post.
TITLE_LENGTH = 60

# Once a publish starts, what went out has to stay what the record says went out.
# A Scheduled post is not here: it can still change until its time comes.
LOCKED_STATUSES = ("Publishing", "Published", "Partial", "Failed")

# A target of a post that has not gone out anywhere yet.
FRESH_TARGET = {
	"status": "Pending",
	"publish_attempted_at": None,
	"released_parts": None,
	"release_id": None,
	"release_url": None,
	"published_at": None,
	"error": None,
	"error_kind": None,
}


class SocialPost(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from bwh_os.social.doctype.social_post_part.social_post_part import SocialPostPart
		from bwh_os.social.doctype.social_post_target.social_post_target import SocialPostTarget

		name: DF.Int | None
		parts: DF.Table[SocialPostPart]
		published_at: DF.Datetime | None
		scheduled_at: DF.Datetime | None
		status: DF.Literal["Draft", "Scheduled", "Publishing", "Published", "Partial", "Failed"]
		targets: DF.Table[SocialPostTarget]
		title: DF.Data | None
		video: DF.Link | None
	# end: auto-generated types

	@property
	def validator(self) -> PostValidator:
		return PostValidator(self)

	def validate(self):
		self.ensure_unchanged_after_publish()
		self.validator.structure()
		self.set_title()

	def ensure_unchanged_after_publish(self):
		"""A post that has gone out, or is going out, keeps the content it went out with."""
		before = self.get_doc_before_save()
		if not before or before.status not in LOCKED_STATUSES:
			return
		if content_of(self) != content_of(before):
			frappe.throw(_("A post cannot change after the publish starts"))

	def set_title(self):
		"""A post you never titled is known by how it starts."""
		if self.title:
			return
		first_line = (self.first_text() or "").strip().splitlines()
		self.title = first_line[0][:TITLE_LENGTH] if first_line else None

	def first_text(self) -> str | None:
		"""The shared part 1. Custom content is per channel, so it names nothing."""
		for row in self.parts:
			if not row.channel and row.part_no == 1:
				return row.text
		return None

	def parts_for(self, target: Document) -> list[dict]:
		"""What one target publishes: its own parts, or else the shared ones."""
		return self.validator.parts_for(target)

	def settings_of(self, target: Document) -> dict:
		"""What the platform needs beyond the text, as a dict."""
		return self.validator.settings_of(target)

	def check(self):
		"""The strict pass. Throws the first thing that would stop a publish."""
		self.validator.check()

	def duplicate(self) -> Document:
		"""A fresh draft saying the same thing, for the channels that have not had it.

		A channel that already published is left off, because sending it the same post
		twice is the one mistake a duplicate is here to avoid. Where every channel got it,
		the copy is a repost and keeps them all.
		"""
		copy = frappe.copy_doc(self)
		copy.status = "Draft"
		copy.scheduled_at = None
		copy.published_at = None
		copy.targets = [row for row in copy.targets if row.status != "Published"] or copy.targets
		for row in copy.targets:
			row.update(FRESH_TARGET)
		copy.insert()
		return copy


def content_of(post: Document) -> tuple:
	"""What the reader would see. Statuses and results change while publishing; this does not."""
	return (
		tuple((row.channel, row.part_no, row.text, row.media) for row in post.parts),
		tuple((row.channel, row.use_custom_content) for row in post.targets),
	)
