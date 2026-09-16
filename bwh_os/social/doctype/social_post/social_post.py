# Copyright (c) 2026, BWH and contributors
# For license information, please see license.txt

from frappe.model.document import Document

from bwh_os.social.validation import PostValidator

# What fits in a list row. A title is a handle for the post, not the post.
TITLE_LENGTH = 60


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
		self.validator.structure()
		self.set_title()

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

	def check(self):
		"""The strict pass. Throws the first thing that would stop a publish."""
		self.validator.check()
