# Copyright (c) 2026, BWH and contributors
# For license information, please see license.txt

import re

import frappe
from frappe import _
from frappe.model.document import Document

from bwh_os.mailing.doctype.subscriber.subscriber import normalize_email
from bwh_os.mailing.emails import ListEmail

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
		lead_magnet: DF.Link | None
		success_message: DF.SmallText
		tags: DF.TableMultiSelect[SubscriberTagItem]
		title: DF.Data
		welcome_body: DF.TextEditor | None
		welcome_subject: DF.Data | None
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
		"""Add a signup from this form. A known email gets the form tags and is made Active again.

		Only a new subscriber gets the welcome email, so a second signup does not send it twice.
		"""
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
		is_new = subscriber.is_new()
		subscriber.save(ignore_permissions=True)
		if is_new:
			self.send_welcome_email(subscriber)
		return subscriber

	def send_welcome_email(self, subscriber):
		# A missing Email Account must not lose the signup. The error log shows what failed.
		try:
			self.queue_welcome_email(subscriber)
		except Exception:
			frappe.log_error(
				f"Welcome email for {subscriber.name} failed",
				reference_doctype="Signup Form",
				reference_name=self.name,
			)

	def queue_welcome_email(self, subscriber):
		if not self.welcome_subject:
			return
		button = None
		if self.lead_magnet:
			lead_magnet = frappe.get_cached_doc("Lead Magnet", self.lead_magnet)
			button = {
				"label": _("Download {0}").format(lead_magnet.title),
				"url": lead_magnet.get_download_url(subscriber.token),
			}
		ListEmail(subscriber, self.welcome_subject, self.welcome_body, button=button).send()
