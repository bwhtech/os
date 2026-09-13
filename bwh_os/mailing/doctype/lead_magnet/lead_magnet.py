# Copyright (c) 2026, BWH and contributors
# For license information, please see license.txt

from urllib.parse import urlencode

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import get_url, now_datetime


class LeadMagnet(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		description: DF.SmallText | None
		file: DF.Attach
		title: DF.Data
	# end: auto-generated types

	def validate(self):
		# A public file would be open to anyone with the URL, with no download logged.
		if not self.file.startswith("/private/files/"):
			frappe.throw(_("Upload the lead magnet as a private file"))

	def get_download_url(self, subscriber_token: str) -> str:
		query = urlencode({"lead_magnet": self.name, "token": subscriber_token})
		return get_url(f"/api/method/bwh_os.mailing.api.download_lead_magnet?{query}")

	def send_file(self, subscriber: str):
		"""Log a download and put the file in the response."""
		frappe.get_doc(
			{
				"doctype": "Lead Magnet Download",
				"lead_magnet": self.name,
				"subscriber": subscriber,
				"downloaded_on": now_datetime(),
			}
		).insert(ignore_permissions=True)
		# Downloads are GET requests, which Frappe does not commit by default.
		frappe.local.flags.commit = True

		file = frappe.get_doc("File", {"file_url": self.file})
		frappe.local.response.update(
			{"type": "download", "filename": file.file_name, "filecontent": file.get_content()}
		)
