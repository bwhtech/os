# Copyright (c) 2026, BWH and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import now_datetime

from bwh_os.mailing.lms_sync import LMSSync


class LMSSyncSettings(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from bwh_os.mailing.doctype.subscriber_tag_item.subscriber_tag_item import SubscriberTagItem

		api_key: DF.Data | None
		api_secret: DF.Password | None
		enabled: DF.Check
		enrollment_tags: DF.TableMultiSelect[SubscriberTagItem]
		enrollments_synced_until: DF.Datetime | None
		last_sync_message: DF.SmallText | None
		last_sync_status: DF.Literal["", "Success", "Failed"]
		last_synced_on: DF.Datetime | None
		site_url: DF.Data | None
		user_tags: DF.TableMultiSelect[SubscriberTagItem]
		users_synced_until: DF.Datetime | None
	# end: auto-generated types

	def sync(self) -> dict:
		"""Run one sync and record how it went. It does not raise, so the daily job stays quiet."""
		frappe.db.savepoint("lms_sync")
		try:
			result = LMSSync(self).run()
		except Exception as e:
			frappe.db.rollback(save_point="lms_sync")
			frappe.log_error("LMS sync failed")
			self.record("Failed", frappe.utils.strip_html(str(e)))
			return {"status": "Failed", "message": self.last_sync_message}

		frappe.db.release_savepoint("lms_sync")
		self.record("Success", result.summary())
		return {"status": "Success", "message": self.last_sync_message, **result.as_dict()}

	def record(self, status: str, message: str):
		self.last_synced_on = now_datetime()
		self.last_sync_status = status
		self.last_sync_message = message
		# A failed sync was rolled back, so the cursors in the database are still the old ones.
		fields = ["last_synced_on", "last_sync_status", "last_sync_message"]
		if status == "Success":
			fields += ["users_synced_until", "enrollments_synced_until"]
		frappe.db.set_single_value(self.doctype, {field: self.get(field) for field in fields})
