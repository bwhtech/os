# Copyright (c) 2026, BWH and contributors
# For license information, please see license.txt

from frappe.model.document import Document


class SocialPostTarget(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		channel: DF.Link
		error: DF.SmallText | None
		error_kind: DF.Literal["", "Reconnect", "Bad Request", "Retryable", "Unconfirmed"]
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		provider: DF.Data | None
		publish_attempted_at: DF.Datetime | None
		published_at: DF.Datetime | None
		release_id: DF.Data | None
		release_url: DF.Data | None
		released_parts: DF.JSON | None
		settings: DF.JSON | None
		status: DF.Literal["Pending", "Publishing", "Published", "Failed"]
		use_custom_content: DF.Check
	# end: auto-generated types

	pass
