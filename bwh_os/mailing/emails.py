import re

import frappe

from bwh_os.mailing import email_variables

FOOTER_TEMPLATE = "bwh_os/templates/emails/newsletter_footer.html"
BLOCK_FOOTER_TEMPLATE = "bwh_os/templates/emails/list_footer.html"
# The Footer block from the editor. Keep in step with frontend/src/lib/emailFooter.ts.
FOOTER_BLOCK = re.compile(r"<div[^>]*\bdata-email-footer\b[^>]*>\s*</div\s*>", re.IGNORECASE)
BODY_END = re.compile(r"</body\s*>", re.IGNORECASE)
CELL_END = re.compile(r"</td\s*>", re.IGNORECASE)


class ListEmail:
	"""An email from the OS editor to one subscriber, with the company footer from Mailing Settings."""

	def __init__(self, subscriber, subject: str, html: str, values: dict[str, str | None] | None = None):
		self.subscriber = subscriber
		self.subject = subject
		self.html = html
		# Values for the variables besides the subscriber's own, for example confirm_url
		self.values = {**email_variables.subscriber_values(subscriber), **(values or {})}

	def send(self):
		if not self.html:
			frappe.throw(frappe._("Write the email before it can go out"))
		settings = frappe.get_cached_doc("Mailing Settings")
		unsubscribe_url = self.subscriber.get_unsubscribe_url()
		frappe.sendmail(
			recipients=[self.subscriber.email],
			sender=settings.get_sender(),
			subject=email_variables.fill(self.subject, self.values, html=False),
			message=add_footer(email_variables.fill(self.html, self.values), unsubscribe_url),
			# The editor makes a full HTML document. Frappe's wrapper would nest it.
			raw_html=True,
			reference_doctype="Subscriber",
			reference_name=self.subscriber.name,
			# Frappe's own link needs an Email Unsubscribe record. Ours uses the subscriber token.
			add_unsubscribe_link=0,
			email_headers=list_headers(unsubscribe_url),
		)


def add_footer(html: str, unsubscribe_url: str | None, extra: str = "") -> str:
	"""Put the company footer and the unsubscribe link in the email, and `extra` at its end.

	The footer takes the place of a Footer block from the editor. With no block, it goes at the end.
	With no unsubscribe URL, as in the web archive, the footer has no link.
	"""
	if FOOTER_BLOCK.search(html):
		footer = render_footer(unsubscribe_url)
		return append_to_body(FOOTER_BLOCK.sub(lambda _: footer, html), extra)
	return append_to_body(html, frappe.render_template(FOOTER_TEMPLATE, footer_context(unsubscribe_url)) + extra)


def render_footer(unsubscribe_url: str | None) -> str:
	return frappe.render_template(BLOCK_FOOTER_TEMPLATE, footer_context(unsubscribe_url))


def footer_context(unsubscribe_url: str | None) -> dict:
	settings = frappe.get_cached_doc("Mailing Settings")
	return {
		"settings": settings,
		"social_links": settings.get_social_links(),
		"unsubscribe_url": unsubscribe_url,
	}


def append_to_body(html: str, footer: str) -> str:
	if not footer:
		return html
	body_ends = list(BODY_END.finditer(html))
	if not body_ends:
		return html + footer

	# The editor puts the email in one outer table cell that has the theme background.
	# Its closing tag is the last </td>, so the footer goes before it.
	body_end = body_ends[-1].start()
	cell_ends = list(CELL_END.finditer(html, 0, body_end))
	at = cell_ends[-1].start() if cell_ends else body_end
	return html[:at] + footer + html[at:]


LIST_HEADERS = ("List-Unsubscribe", "List-Unsubscribe-Post")


def list_headers(unsubscribe_url: str) -> dict[str, str]:
	"""One-click unsubscribe headers (RFC 8058). Frappe puts "X-" before these names. See rename_list_headers."""
	return {
		"List-Unsubscribe": f"<{unsubscribe_url}>",
		"List-Unsubscribe-Post": "List-Unsubscribe=One-Click",
	}


def rename_list_headers(mail):
	"""The make_email_body_message hook. Gmail and Yahoo read only the standard header names."""
	for name in LIST_HEADERS:
		if value := mail.msg_root.get(f"X-{name}"):
			del mail.msg_root[f"X-{name}"]
			mail.set_header(name, value)
