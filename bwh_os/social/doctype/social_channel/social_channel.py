# Copyright (c) 2026, BWH and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class SocialChannel(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		account_id: DF.Data
		avatar_url: DF.Data | None
		connected_app: DF.Link
		connected_on: DF.Datetime | None
		display_name: DF.Data | None
		expires_on: DF.Datetime | None
		handle: DF.Data | None
		last_error: DF.SmallText | None
		profile_url: DF.Data | None
		provider: DF.Literal["LinkedIn", "X"]
		reminder_sent_on: DF.Date | None
		status: DF.Literal["Connected", "Expired", "Disconnected"]
		token_cache: DF.Link | None
		user: DF.Link
	# end: auto-generated types

	def mark_expired(self, error: str | None = None) -> None:
		"""The token is gone. Say so on the channel, so the UI can ask for a reconnect."""
		self.db_set({"status": "Expired", "last_error": error}, notify=True)

	def days_left(self) -> int | None:
		"""Whole days until the token expires. None when the channel has no expiry."""
		if not self.expires_on:
			return None
		return frappe.utils.date_diff(self.expires_on, frappe.utils.now_datetime())
