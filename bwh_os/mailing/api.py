import frappe
from frappe import _
from frappe.query_builder.functions import Count
from frappe.utils import validate_email_address
from werkzeug.utils import redirect

from bwh_os.mailing import stats, youtube_video
from bwh_os.mailing.emails import render_footer
from bwh_os.mailing.newsletter_engagement import NewsletterEngagement
from bwh_os.mailing.newsletter_send import Audience, NewsletterSend
from bwh_os.mailing.newsletter_tracking import is_signed, pixel_response
from bwh_os.mailing.subscriber_import import SubscriberImport

SIGNUP_API_ROLE = "OS Signup API"


@frappe.whitelist(methods=["POST"])
def subscribe(
	form_id: str,
	email: str,
	first_name: str | None = None,
	source_url: str | None = None,
	utm: dict | None = None,
	consent_ip: str | None = None,
) -> dict:
	"""Public signup, called by the website's Netlify function with an API key.

	The reply is the same for a new and a known email, so the caller learns nothing about the list.
	"""
	frappe.only_for((SIGNUP_API_ROLE, "System Manager"))
	form = frappe.get_doc("Signup Form", form_id)
	form.subscribe(email, first_name=first_name, source_url=source_url, utm=utm, consent_ip=consent_ip)
	return {"message": form.success_message}


@frappe.whitelist(methods=["POST"])
def add_subscriber(email: str, first_name: str | None = None, tags: list[str] | None = None) -> str:
	"""Add a subscriber by hand from OS. Missing tags are created."""
	subscriber = frappe.new_doc("Subscriber")
	subscriber.email = email
	subscriber.first_name = first_name
	subscriber.status = "Active"
	subscriber.add_tags(tags or [])
	subscriber.insert()
	return subscriber.name


@frappe.whitelist(methods=["POST"])
def preview_subscriber_import(content: str, mapping: dict | None = None, tags: list[str] | None = None) -> dict:
	"""Read CSV text and say what an import would do. With no mapping, the columns are mapped by name."""
	frappe.only_for("System Manager")
	return SubscriberImport(content, mapping, tags).preview()


@frappe.whitelist(methods=["POST"])
def import_subscribers(content: str, mapping: dict, tags: list[str] | None = None) -> dict:
	"""Start a background import of CSV text. Progress comes as `subscriber_import_progress` events.

	New emails become Active. Known emails only get the tags.
	"""
	frappe.only_for("System Manager")
	return SubscriberImport(content, mapping, tags).enqueue()


@frappe.whitelist(methods=["POST"])
def send_test_newsletter(issue: str, email: str) -> str:
	"""Send the saved issue to one address. Returns the address."""
	frappe.only_for("System Manager")
	recipient = validate_email_address(email.strip())
	if not recipient:
		frappe.throw(_("Enter a valid email address"))
	frappe.get_doc("Newsletter Issue", issue).send_test(recipient)
	return recipient


@frappe.whitelist(methods=["GET"])
def get_newsletter_audience(
	audience: str, tags: list[str] | str | None = None, hourly_limit: int | None = None
) -> dict:
	"""Who a send would reach now. Takes the unsaved values from the issue page.

	A GET request carries `tags` as a JSON array string.
	"""
	frappe.only_for("System Manager")
	if isinstance(tags, str):
		tags = frappe.parse_json(tags)
	return Audience(audience, tags or [], hourly_limit or 0).preview()


@frappe.whitelist(methods=["POST"])
def send_newsletter(issue: str) -> str:
	"""Start sending the saved issue to its audience. Returns the new status."""
	frappe.only_for("System Manager")
	doc = frappe.get_doc("Newsletter Issue", issue)
	doc.send()
	return doc.status


@frappe.whitelist(methods=["POST"])
def schedule_newsletter(issue: str, scheduled_at: str) -> str:
	"""Send the saved issue at `scheduled_at`, in system time. Returns the new status."""
	frappe.only_for("System Manager")
	doc = frappe.get_doc("Newsletter Issue", issue)
	doc.schedule(scheduled_at)
	return doc.status


@frappe.whitelist(methods=["POST"])
def unschedule_newsletter(issue: str) -> str:
	"""Make a Scheduled issue a Draft again, so it can change. Returns the new status."""
	frappe.only_for("System Manager")
	doc = frappe.get_doc("Newsletter Issue", issue)
	doc.unschedule()
	return doc.status


@frappe.whitelist(methods=["GET"])
def get_newsletter_progress(issue: str) -> dict:
	"""Delivery counts in total and per hourly batch."""
	frappe.only_for("System Manager")
	return NewsletterSend(frappe.get_doc("Newsletter Issue", issue)).progress()


@frappe.whitelist(methods=["GET"])
def get_newsletter_engagement(issue: str) -> dict:
	"""Open and click rates against the previous issue, the funnel, opens per hour, and top links."""
	frappe.only_for("System Manager")
	return NewsletterEngagement(frappe.get_doc("Newsletter Issue", issue)).report()


@frappe.whitelist(allow_guest=True, methods=["GET"])
def track_open(delivery: str):
	"""The open pixel in every newsletter email. It always returns the image."""
	if frappe.db.exists("Newsletter Delivery", delivery):
		frappe.get_doc("Newsletter Delivery", delivery).record_open()
		# Pixel loads are GET requests, which Frappe does not commit by default.
		frappe.local.flags.commit = True
	return pixel_response()


@frappe.whitelist(allow_guest=True, methods=["GET"])
def track_click(delivery: str, url: str, signature: str):
	"""The click redirect for every link in a newsletter email."""
	if not is_signed(delivery, url, signature):
		frappe.respond_as_web_page(
			_("Link not valid"),
			_("This link is not valid. Use the link in your email."),
			http_status_code=404,
			indicator_color="red",
		)
		return
	if frappe.db.exists("Newsletter Delivery", delivery):
		frappe.get_doc("Newsletter Delivery", delivery).record_click(url)
		frappe.local.flags.commit = True
	return redirect(url)


@frappe.whitelist(allow_guest=True, methods=["GET"])
def download_lead_magnet(lead_magnet: str, token: str) -> None:
	"""The link in the welcome email. The subscriber token stands in for a login."""
	subscriber = frappe.db.get_value("Subscriber", {"token": token, "status": ("!=", "Pending")})
	if not subscriber or not frappe.db.exists("Lead Magnet", lead_magnet):
		frappe.respond_as_web_page(
			_("Link not valid"),
			_("This download link is not valid. Use the link in your latest email."),
			http_status_code=404,
			indicator_color="red",
		)
		return
	frappe.get_doc("Lead Magnet", lead_magnet).send_file(subscriber)


@frappe.whitelist(allow_guest=True, methods=["GET"])
def confirm_subscription(form_id: str, token: str) -> None:
	"""The link in the confirm email. It makes a Pending subscriber Active and sends the welcome email."""
	subscriber = frappe.db.get_value("Subscriber", {"token": token, "status": ("in", ("Pending", "Active"))})
	if not subscriber or not frappe.db.exists("Signup Form", form_id):
		frappe.respond_as_web_page(
			_("Link not valid"),
			_("This confirm link is not valid. Sign up again to get a new one."),
			http_status_code=404,
			indicator_color="red",
		)
		return

	form = frappe.get_doc("Signup Form", form_id)
	form.confirm(frappe.get_doc("Subscriber", subscriber))
	# Confirm links are GET requests, which Frappe does not commit by default.
	frappe.local.flags.commit = True
	message = _("Thanks for confirming.")
	if form.welcome_subject:
		message += " " + _("Check your inbox for the welcome email.")
	frappe.respond_as_web_page(_("You are subscribed"), message, indicator_color="green")


@frappe.whitelist(allow_guest=True, methods=["GET", "POST"])
def unsubscribe(token: str, delivery: str | None = None) -> None:
	"""The unsubscribe link and the List-Unsubscribe header in every list email.

	GET shows a page with a button, so a link scanner cannot unsubscribe anyone. POST unsubscribes.
	Mail clients send the one-click POST (RFC 8058) with no cookies and no CSRF token.
	A link in a newsletter also carries the delivery, so the issue report counts the unsubscribe.
	"""
	subscriber = frappe.db.get_value("Subscriber", {"token": token})
	if not subscriber:
		frappe.respond_as_web_page(
			_("Link not valid"),
			_("This unsubscribe link is not valid. Use the link in your latest email."),
			http_status_code=404,
			indicator_color="red",
		)
		return

	if frappe.request and frappe.request.method == "POST":
		subscriber = frappe.get_doc("Subscriber", subscriber)
		subscriber.unsubscribe()
		subscriber.save(ignore_permissions=True)
		if delivery and frappe.db.get_value("Newsletter Delivery", delivery, "subscriber") == subscriber.name:
			frappe.get_doc("Newsletter Delivery", delivery).record_unsubscribe()
		frappe.respond_as_web_page(
			_("You are unsubscribed"),
			_("You will not get more emails from this list."),
			indicator_color="green",
		)
		return

	frappe.respond_as_web_page(
		_("Unsubscribe"),
		frappe.render_template(
			"bwh_os/templates/includes/unsubscribe_form.html",
			{
				"email": subscriber,
				# A logged-in browser must send the CSRF token with the POST.
				"csrf_token": frappe.sessions.get_csrf_token() if frappe.session.user != "Guest" else None,
			},
		),
		indicator_color="orange",
	)


@frappe.whitelist(methods=["GET"])
def get_signup_counts() -> dict[str, int]:
	"""Subscriber count per signup form."""
	return count_by("Subscriber", "source_form")


@frappe.whitelist(methods=["GET"])
def get_download_counts() -> dict[str, int]:
	"""Download count per lead magnet."""
	return count_by("Lead Magnet Download", "lead_magnet")


@frappe.whitelist(methods=["GET"])
def get_list_overview() -> dict:
	"""Subscriber, unsubscribe and download activity for the dashboard."""
	frappe.only_for("System Manager")
	return stats.list_overview()


@frappe.whitelist(methods=["GET"])
def get_lead_magnet_activity(lead_magnet: str) -> dict:
	"""Download activity for one lead magnet."""
	frappe.only_for("System Manager")
	return stats.activity("Lead Magnet Download", "downloaded_on", {"lead_magnet": lead_magnet})


@frappe.whitelist(methods=["GET"])
def get_form_activity(form_id: str) -> dict:
	"""Signup activity for one signup form."""
	frappe.only_for("System Manager")
	return stats.activity("Subscriber", "subscribed_on", {"source_form": form_id})


@frappe.whitelist(methods=["POST"])
def get_youtube_video(url: str) -> dict:
	"""The title, link, and thumbnail for the YouTube video block in the email editor.

	POST, because the first call for a video saves its thumbnail file.
	"""
	frappe.only_for("System Manager")
	return youtube_video.get_video(url)


@frappe.whitelist(methods=["GET"])
def get_email_footer() -> str:
	"""The company footer for the Footer block in the editor and preview, with a sample unsubscribe link."""
	frappe.only_for("System Manager")
	return render_footer(unsubscribe_url="#")


def count_by(doctype: str, field: str) -> dict[str, int]:
	frappe.only_for("System Manager")
	table = frappe.qb.DocType(doctype)
	rows = (
		frappe.qb.from_(table)
		.select(table[field], Count("*").as_("count"))
		.where(table[field].isnotnull())
		.groupby(table[field])
		.run(as_dict=True)
	)
	return {row[field]: row.count for row in rows}
