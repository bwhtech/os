# Copyright (c) 2026, BWH and contributors
# For license information, please see license.txt

import re

import frappe
from frappe import _
from frappe.model.document import Document

from bwh_os.blog.posts import get_post_titles

# `category/slug`, the key the blog uses for a post.
POST_ID = re.compile(r"^[a-z0-9][a-z0-9-]*/[a-z0-9][a-z0-9-]*$")


class BWHBlogPost(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		likes: DF.Int
		post_id: DF.Data
		title: DF.Data | None
	# end: auto-generated types

	def validate(self):
		if len(self.post_id) > 120 or not POST_ID.match(self.post_id):
			frappe.throw(_("Post ID must look like category/slug"))

	def before_insert(self):
		self.title = self.title or get_post_titles().get(self.post_id)

	def add_like(self) -> int:
		"""Add one like in one statement, so parallel likes do not overwrite each other. Returns the total."""
		frappe.db.sql("UPDATE `tabBWH Blog Post` SET likes = likes + 1 WHERE name = %s", self.name)
		# The raw update sends no realtime event, so tell open OS pages here.
		frappe.publish_realtime(
			"list_update", {"doctype": self.doctype, "name": self.name}, after_commit=True
		)
		return frappe.db.get_value("BWH Blog Post", self.name, "likes")


def get_or_create_post(post_id: str) -> BWHBlogPost:
	"""The blog makes a post in OS on its first like or comment."""
	if not frappe.db.exists("BWH Blog Post", post_id):
		try:
			frappe.get_doc({"doctype": "BWH Blog Post", "post_id": post_id}).insert(ignore_permissions=True)
		except frappe.DuplicateEntryError:
			# A parallel request made it first.
			pass
	return frappe.get_doc("BWH Blog Post", post_id)
