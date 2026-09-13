# Copyright (c) 2026, BWH and contributors
# For license information, please see license.txt

import re

import frappe
from frappe import _
from frappe.model.document import Document

from bwh_os.mailing.doctype.subscriber.subscriber import normalize_email

FORM_ID_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


class FormClosedError(frappe.ValidationError):
	pass


class SignupForm(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from bwh_os.mailing.doctype.subscriber_tag_item.subscriber_tag_item import SubscriberTagItem

		collect_name: DF.Check
		form_id: DF.Data
		is_active: DF.Check
		success_message: DF.SmallText
		tags: DF.TableMultiSelect[SubscriberTagItem]
		title: DF.Data
	# end: auto-generated types

	def before_validate(self):
		self.form_id = (self.form_id or "").strip().lower()

	def validate(self):
		if not FORM_ID_PATTERN.match(self.form_id):
			frappe.throw(_("Form ID can only have lowercase letters, digits, and single hyphens"))

	def subscribe(
		self,
		email: str,
		first_name: str | None = None,
		source_url: str | None = None,
		utm: dict | None = None,
		consent_ip: str | None = None,
	):
		"""Add a signup from this form. A known email gets the form tags and is made Active again."""
		if not self.is_active:
			frappe.throw(_("This form is closed"), FormClosedError)

		email = normalize_email(email)
		if frappe.db.exists("Subscriber", email):
			subscriber = frappe.get_doc("Subscriber", email)
			subscriber.first_name = subscriber.first_name or first_name
		else:
			subscriber = frappe.new_doc("Subscriber")
			subscriber.update(
				{
					"email": email,
					"first_name": first_name,
					"source_form": self.name,
					"source_url": source_url,
					"utm": frappe.as_json(utm) if utm else None,
					"consent_ip": consent_ip,
				}
			)

		# Single opt-in: a signup is consent, even from someone who unsubscribed before.
		if subscriber.status != "Bounced":
			subscriber.status = "Active"
		subscriber.add_tags([row.tag for row in self.tags])
		subscriber.save(ignore_permissions=True)
		return subscriber
