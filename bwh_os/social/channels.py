"""Watching the tokens of the channels. See slice 1.3 in specs/04-social-posts.md.

LinkedIn gives no refresh token, so a connection dies 60 days after you make it. Nothing
in the app notices that on its own: the first sign would be a scheduled post that fails.
The daily task below looks ahead instead. It asks for a reconnect a week early, and it
marks a channel Expired the day its token runs out, so the OS says so before a post does.
"""

import frappe
from frappe import _
from frappe.utils import get_url, getdate, today

from bwh_os.social.doctype.social_channel.social_channel import SocialChannel

TEMPLATE = "bwh_os/templates/emails/social_token_expiry.html"

# How early the reminder goes out. LinkedIn tokens last 60 days, so a week is enough
# time to reconnect without the reminder arriving while the token is still young.
REMINDER_DAYS = 7


def check_expiry() -> None:
	"""Mark the channels whose token has run out, and remind about the ones close to it.

	Runs daily. One channel that fails does not stop the rest, because a broken email
	account must not leave a dead token looking Connected.
	"""
	names = frappe.get_all(
		"Social Channel",
		filters={"status": ["!=", "Disconnected"], "expires_on": ["is", "set"]},
		pluck="name",
	)
	for name in names:
		try:
			check_channel(frappe.get_doc("Social Channel", name))
		except Exception:
			frappe.log_error(
				"Could not check the token of a social channel",
				reference_doctype="Social Channel",
				reference_name=name,
			)


def check_channel(channel: SocialChannel) -> None:
	"""Act on one channel: too early to care, or expired, or worth a reminder."""
	days_left = channel.days_left()
	if days_left is None or days_left > REMINDER_DAYS:
		return

	if days_left <= 0 and channel.status == "Connected":
		channel.mark_expired(_("The token ran out. Connect {0} again to publish.").format(channel.provider))

	# `reminder_sent_on` holds the window open: a reconnect clears it, so the next token
	# gets its own reminder and this one never sends twice.
	if not channel.reminder_sent_on:
		send_reminder(channel, days_left)


def send_reminder(channel: SocialChannel, days_left: int) -> None:
	"""One email about a token that is about to go, or has gone."""
	recipient = frappe.db.get_value("User", channel.user, "email") or channel.user
	settings = frappe.get_cached_doc("Mailing Settings")
	frappe.sendmail(
		recipients=[recipient],
		sender=settings.get_sender(),
		subject=subject(channel, days_left),
		message=frappe.render_template(
			TEMPLATE,
			{
				"provider": channel.provider,
				"account": channel.display_name or channel.provider,
				"days_left": days_left,
				"expires_on": frappe.utils.format_datetime(channel.expires_on, "d MMM YYYY"),
				"expired": days_left <= 0,
				"settings_url": get_url("/os/social"),
			},
		),
		reference_doctype=channel.doctype,
		reference_name=channel.name,
	)
	channel.db_set("reminder_sent_on", getdate(today()), notify=True)


def subject(channel: SocialChannel, days_left: int) -> str:
	if days_left <= 0:
		return _("{0} is disconnected from BWH OS").format(channel.provider)
	if days_left == 1:
		return _("{0} disconnects from BWH OS tomorrow").format(channel.provider)
	return _("{0} disconnects from BWH OS in {1} days").format(channel.provider, days_left)
