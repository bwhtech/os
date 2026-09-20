# Copyright (c) 2026, BWH and contributors
# For license information, please see license.txt

import re
from contextlib import contextmanager
from urllib.parse import urlencode

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import get_url, validate_email_address

from bwh_os.mailing import email_variables
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
		confirm_content_html: DF.Code | None
		confirm_content_json: DF.JSON | None
		confirm_reply_to: DF.Data | None
		confirm_subject: DF.Data | None
		confirm_theme: DF.Literal["Frappe UI", "Basic", "Minimal"]
		double_opt_in: DF.Check
		form_id: DF.Data
		is_active: DF.Check
		lead_magnet: DF.Link | None
		send_welcome_with_lead_magnet: DF.Check
		success_message: DF.SmallText
		tags: DF.TableMultiSelect[SubscriberTagItem]
		title: DF.Data
		welcome_content_html: DF.Code | None
		welcome_content_json: DF.JSON | None
		welcome_reply_to: DF.Data | None
		welcome_subject: DF.Data | None
		welcome_theme: DF.Literal["Frappe UI", "Basic", "Minimal"]
	# end: auto-generated types

	def before_validate(self):
		self.form_id = (self.form_id or "").strip().lower()

	def validate(self):
		if not FORM_ID_PATTERN.match(self.form_id):
			frappe.throw(_("Form ID can only have lowercase letters, digits, and single hyphens"))
		self.validate_confirm_email()
		self.validate_welcome_email()
		self.validate_lead_magnet()
		for field in ("confirm_reply_to", "welcome_reply_to"):
			if self.get(field):
				validate_email_address(self.get(field), throw=True)

	def validate_confirm_email(self):
		if not self.double_opt_in:
			return
		# The desk enforces mandatory_depends_on, but a save through the API does not.
		if not self.confirm_subject:
			frappe.throw(_("Set a confirm subject for a double opt-in form"))
		if not self.confirm_content_html:
			frappe.throw(_("Write the confirm email for a double opt-in form"))
		email_variables.check(self.confirm_subject, email_variables.CONFIRM, _("The confirm subject"))
		email_variables.check(
			self.confirm_content_html,
			email_variables.CONFIRM,
			_("The confirm email"),
			required=["confirm_url"],
		)

	def validate_welcome_email(self):
		if not self.welcome_subject:
			return
		if not self.welcome_content_html:
			frappe.throw(_("Write the welcome email, or clear its subject to send nothing"))
		email_variables.check(self.welcome_subject, email_variables.WELCOME, _("The welcome subject"))
		email_variables.check(self.welcome_content_html, email_variables.WELCOME, _("The welcome email"))

	def validate_lead_magnet(self):
		if not self.lead_magnet:
			return
		magnet = frappe.get_cached_doc("Lead Magnet", self.lead_magnet)
		if not magnet.has_email():
			frappe.throw(
				_("Write the delivery email on {0} before a form can give it away").format(magnet.title)
			)

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
		confirm email when the form has double opt-in.

		The lead magnet, if any, goes out on every signup, not once per person. A reader already
		on the list who fills in a form is asking for what that form gives away. The greeting is
		not repeated: it already said "thanks for joining" the first time. A dead address is the
		one exception to both.
		"""
		if not self.is_active:
			frappe.throw(_("This form is closed"), FormClosedError)

		subscriber = self.get_or_new_subscriber(
			email, first_name=first_name, source_url=source_url, utm=utm, consent_ip=consent_ip
		)
		subscriber.add_tags([row.tag for row in self.tags])
		if not subscriber.is_new() and subscriber.status in ("Active", "Bounced"):
			subscriber.save(ignore_permissions=True)
			# A confirmed reader has no second opt-in to give, so a double opt-in form skips
			# straight to the file. Bounced gets nothing: the address is dead.
			if subscriber.status == "Active":
				self.send_emails(subscriber, greeting=False)
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
		subscriber.activate()
		subscriber.save(ignore_permissions=True)
		self.send_emails(subscriber, greeting=True)

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
			values = {"confirm_url": self.get_confirm_url(subscriber.token)}
			ListEmail(
				subscriber,
				self.confirm_subject,
				self.confirm_content_html,
				values,
				reply_to=self.confirm_reply_to,
			).send()

	def send_emails(self, subscriber, greeting: bool = True):
		"""The form's greeting, then the file. Either may be absent.

		`greeting` is False on a repeat signup: the reader already got "thanks for joining"
		the first time, so only the lead magnet goes out again.
		"""
		send_greeting = (
			greeting and self.welcome_subject and (not self.lead_magnet or self.send_welcome_with_lead_magnet)
		)
		if send_greeting:
			with log_email_failure(subscriber, self.name, "Welcome"):
				ListEmail(
					subscriber,
					self.welcome_subject,
					self.welcome_content_html,
					reply_to=self.welcome_reply_to,
				).send()
		if self.lead_magnet:
			with log_email_failure(subscriber, self.name, "Lead Magnet"):
				frappe.get_cached_doc("Lead Magnet", self.lead_magnet).send_to(
					subscriber, source="Signup Form", reference=self.name
				)


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
