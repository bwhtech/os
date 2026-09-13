# Copyright (c) 2026, BWH and contributors
# For license information, please see license.txt

import re
from contextlib import contextmanager
from urllib.parse import urlencode

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import get_url

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
		confirm_body: DF.TextEditor | None
		confirm_subject: DF.Data | None
		double_opt_in: DF.Check
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
		# The desk enforces mandatory_depends_on, but a save through the API does not.
		if self.double_opt_in and not self.confirm_subject:
			frappe.throw(_("Set a confirm subject for a double opt-in form"))

	def subscribe(
		self,
		email: str,
		first_name: str | None = None,
		source_url: str | None = None,
		utm: dict | None = None,
		consent_ip: str | None = None,
	):
		"""Add a signup from this form. A known email gets the form tags.

		Active and Bounced people keep their status. Anyone else becomes Active, or Pending with a
		confirm email when the form has double opt-in. The welcome email goes out only once.
		"""
		if not self.is_active:
			frappe.throw(_("This form is closed"), FormClosedError)

		subscriber = self.get_or_new_subscriber(
			email, first_name=first_name, source_url=source_url, utm=utm, consent_ip=consent_ip
		)
		subscriber.add_tags([row.tag for row in self.tags])
		if not subscriber.is_new() and subscriber.status in ("Active", "Bounced"):
			subscriber.save(ignore_permissions=True)
		elif self.double_opt_in:
			subscriber.status = "Pending"
			subscriber.save(ignore_permissions=True)
			self.send_confirm_email(subscriber)
		else:
			# A signup is consent, even from someone who unsubscribed before.
			self.activate(subscriber)
		return subscriber

	def confirm(self, subscriber):
		"""The subscriber clicked the link in the confirm email from this form."""
		if subscriber.status == "Pending":
			self.activate(subscriber)

	def activate(self, subscriber):
		send_welcome = subscriber.activate()
		subscriber.save(ignore_permissions=True)
		if send_welcome:
			self.send_welcome_email(subscriber)

	def get_or_new_subscriber(
		self,
		email: str,
		first_name: str | None,
		source_url: str | None,
		utm: dict | None,
		consent_ip: str | None,
	):
		email = normalize_email(email)
		if frappe.db.exists("Subscriber", email):
			subscriber = frappe.get_doc("Subscriber", email)
			subscriber.first_name = subscriber.first_name or first_name
			return subscriber

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
		return subscriber

	def get_confirm_url(self, subscriber_token: str) -> str:
		query = urlencode({"form_id": self.name, "token": subscriber_token})
		return get_url(f"/api/method/bwh_os.mailing.api.confirm_subscription?{query}")

	def send_confirm_email(self, subscriber):
		with log_email_failure(subscriber, self.name, "Confirm"):
			button = {"label": _("Confirm subscription"), "url": self.get_confirm_url(subscriber.token)}
			ListEmail(subscriber, self.confirm_subject, self.confirm_body, button=button).send()

	def send_welcome_email(self, subscriber):
		if not self.welcome_subject:
			return
		with log_email_failure(subscriber, self.name, "Welcome"):
			button = None
			if self.lead_magnet:
				lead_magnet = frappe.get_cached_doc("Lead Magnet", self.lead_magnet)
				button = {
					"label": _("Download {0}").format(lead_magnet.title),
					"url": lead_magnet.get_download_url(subscriber.token),
				}
			ListEmail(subscriber, self.welcome_subject, self.welcome_body, button=button).send()


@contextmanager
def log_email_failure(subscriber, form_name: str, kind: str):
	"""A missing Email Account must not lose the signup. The error log shows what failed."""
	try:
		yield
	except Exception:
		frappe.log_error(
			f"{kind} email for {subscriber.name} failed",
			reference_doctype="Signup Form",
			reference_name=form_name,
		)
