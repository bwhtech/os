# Copyright (c) 2026, BWH and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import get_url, validate_email_address

from bwh_os.mailing import email_variables
from bwh_os.mailing.emails import add_footer
from bwh_os.mailing.newsletter_archive import NewsletterRoute
from bwh_os.mailing.newsletter_schedule import NewsletterSchedule
from bwh_os.mailing.newsletter_send import DEFAULT_HOURLY_LIMIT, NewsletterSend
from bwh_os.mailing.newsletter_tracking import EmailTracking

# What the reader gets. Tags are compared on their own, because they are a table.
LOCKED_FIELDS = (
	"subject",
	"preview_text",
	"reply_to",
	"theme",
	"lead_magnet",
	"content_json",
	"content_html",
	"audience",
	"hourly_limit",
)


class NewsletterIssue(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from bwh_os.mailing.doctype.subscriber_tag_item.subscriber_tag_item import SubscriberTagItem

		audience: DF.Literal["All Active", "Tags"]
		clicked_count: DF.Int
		completed_at: DF.Datetime | None
		content_html: DF.Code | None
		content_json: DF.JSON | None
		failed_count: DF.Int
		hourly_limit: DF.Int
		is_public: DF.Check
		lead_magnet: DF.Link | None
		opened_count: DF.Int
		preview_text: DF.Data | None
		recipient_count: DF.Int
		reply_to: DF.Data | None
		route: DF.Data | None
		scheduled_at: DF.Datetime | None
		sent_at: DF.Datetime | None
		sent_count: DF.Int
		skipped_count: DF.Int
		status: DF.Literal["Draft", "Scheduled", "Sending", "Sent", "Failed"]
		subject: DF.Data
		tags: DF.TableMultiSelect[SubscriberTagItem]
		theme: DF.Literal["Frappe UI", "Basic", "Minimal"]
		unsubscribed_count: DF.Int
	# end: auto-generated types

	def before_insert(self):
		self.hourly_limit = (
			self.hourly_limit
			or frappe.get_cached_doc("Mailing Settings").default_hourly_limit
			or DEFAULT_HOURLY_LIMIT
		)

	def validate(self):
		self.ensure_unchanged_after_send()
		if self.reply_to:
			validate_email_address(self.reply_to, throw=True)
		if not self.lead_magnet and self.content_html and "download_url" in self.content_html:
			# The generic "cannot fill this variable" message is right but unhelpful here: the
			# reader just removed the one thing that made the link fillable.
			frappe.throw(_("Remove the download button, or pick the lead magnet again."))
		email_variables.check(self.subject, self.allowed_variables(), _("The subject"))
		email_variables.check(
			self.content_html,
			self.allowed_variables(),
			_("The newsletter"),
			required=["download_url"] if self.lead_magnet else [],
		)
		NewsletterRoute(self).validate()

	def allowed_variables(self) -> tuple[str, ...]:
		"""`download_url` and `lead_magnet` are fillable only once a lead magnet is picked."""
		return email_variables.with_lead_magnet(email_variables.NEWSLETTER, self.lead_magnet)

	def send(self):
		"""Send to the audience in hourly batches. See NewsletterSend."""
		NewsletterSend(self).start()

	def schedule(self, at: str):
		"""Send at a later time. See NewsletterSchedule."""
		NewsletterSchedule(self).schedule(at)

	def unschedule(self):
		NewsletterSchedule(self).cancel()

	def ensure_unchanged_after_send(self):
		before = self.get_doc_before_save()
		if not before or before.status == "Draft":
			return
		changed = [field for field in LOCKED_FIELDS if self.get(field) != before.get(field)]
		if [row.tag for row in self.tags] != [row.tag for row in before.tags]:
			changed.append("tags")
		if changed:
			frappe.throw(_("A newsletter cannot change after the send starts"))

	def send_test(self, recipient: str):
		"""Send the saved content to one address, with "[Test]" before the subject."""
		if not self.content_html:
			frappe.throw(_("Write the newsletter before you send a test"))

		settings = frappe.get_cached_doc("Mailing Settings")
		# A test goes to a user, not a subscriber, so the link has no real token.
		unsubscribe_url = get_url("/api/method/bwh_os.mailing.api.unsubscribe?token=test")
		values = self.test_values()
		queued = frappe.sendmail(
			recipients=[recipient],
			sender=settings.get_sender(),
			reply_to=settings.get_reply_to(self.reply_to),
			subject=_("[Test] {0}").format(email_variables.fill(self.subject, values, html=False)),
			message=self.get_email_html(unsubscribe_url, values=values),
			# The editor makes a full HTML document. Frappe's wrapper would nest it.
			raw_html=True,
			reference_doctype=self.doctype,
			reference_name=self.name,
			add_unsubscribe_link=0,
		)
		# Frappe drops an address with a global Email Unsubscribe record and raises nothing.
		if not queued:
			frappe.throw(
				_(
					"{0} is unsubscribed from all email in Frappe. Remove its Email Unsubscribe record."
				).format(recipient)
			)

	def test_values(self) -> dict[str, str | None]:
		"""Fallbacks, except a real link for a lead magnet: `?token=test` 404s cleanly, and a blank
		{{ download_url }} in a test send would look broken rather than say so."""
		values = email_variables.fallback_values(self.allowed_variables())
		if self.lead_magnet:
			magnet = frappe.get_cached_doc("Lead Magnet", self.lead_magnet)
			values |= {"download_url": magnet.get_download_url("test"), "lead_magnet": magnet.title}
		return values

	def get_web_html(self) -> str:
		"""The page in the web archive: the content and the company footer, with no pixel and no unsubscribe link."""
		return self.get_email_html(unsubscribe_url=None)

	def get_email_html(
		self,
		unsubscribe_url: str | None,
		tracking: "EmailTracking | None" = None,
		values: dict[str, str | None] | None = None,
	) -> str:
		"""The content with the reader's values, the company footer, and the unsubscribe link.

		With no values, every variable gets its fallback. With tracking, the content links go through
		the click redirect and the footer has the open pixel.
		"""
		html = email_variables.fill(
			self.content_html, values or email_variables.fallback_values(self.allowed_variables())
		)
		if not tracking:
			return add_footer(html, unsubscribe_url)
		# Fill before rewriting links: the download link is a real URL by the time tracking sees it,
		# and rewriting first would sign the literal `{{ download_url }}` text instead.
		return add_footer(tracking.rewrite_links(html), unsubscribe_url, extra=tracking.pixel())
