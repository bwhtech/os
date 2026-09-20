# Copyright (c) 2026, BWH and contributors
# For license information, please see license.txt

from urllib.parse import urlencode

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import get_url, now_datetime

from bwh_os.mailing.lead_magnet_page import ROUTE_PREFIX, LeadMagnetRoute


class LeadMagnet(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		blurb: DF.SmallText | None
		description: DF.SmallText | None
		file: DF.Attach
		route: DF.Data | None
		title: DF.Data
	# end: auto-generated types

	def validate(self):
		# A public file would be open to anyone with the URL, with no download logged.
		if not self.file.startswith("/private/files/"):
			frappe.throw(_("Upload the lead magnet as a private file"))
		LeadMagnetRoute(self).validate()

	def get_download_url(self, subscriber_token: str) -> str:
		"""The link that goes in an email. The token says who is asking."""
		return get_url(f"/{ROUTE_PREFIX}{self.route}?{urlencode({'token': subscriber_token})}")

	def get_file(self):
		return frappe.get_doc("File", {"file_url": self.file})

	def log_download(self, subscriber: str):
		frappe.get_doc(
			{
				"doctype": "Lead Magnet Download",
				"lead_magnet": self.name,
				"subscriber": subscriber,
				"downloaded_on": now_datetime(),
			}
		).insert(ignore_permissions=True)
