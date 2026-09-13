import frappe

TEMPLATE = "bwh_os/templates/emails/list_email.html"


class ListEmail:
	"""An email to one subscriber, with the company footer from Mailing Settings."""

	def __init__(self, subscriber, subject: str, body: str, button: dict | None = None):
		self.subscriber = subscriber
		self.subject = subject
		self.body = body
		# {"label": ..., "url": ...}, shown below the body
		self.button = button

	def send(self):
		settings = frappe.get_cached_doc("Mailing Settings")
		unsubscribe_url = self.subscriber.get_unsubscribe_url()
		frappe.sendmail(
			recipients=[self.subscriber.email],
			sender=settings.get_sender(),
			subject=self.render(self.subject),
			message=frappe.render_template(
				TEMPLATE,
				{
					"body": self.render(self.body),
					"button": self.button,
					"settings": settings,
					"unsubscribe_url": unsubscribe_url,
				},
			),
			reference_doctype="Subscriber",
			reference_name=self.subscriber.name,
			# Frappe's own link needs an Email Unsubscribe record. Ours uses the subscriber token.
			add_unsubscribe_link=0,
			# Frappe puts "X-" before these names. See rename_list_headers.
			email_headers={
				"List-Unsubscribe": f"<{unsubscribe_url}>",
				"List-Unsubscribe-Post": "List-Unsubscribe=One-Click",
			},
		)

	def render(self, text: str) -> str:
		"""Subjects and bodies can use Jinja, for example {{ first_name }}."""
		return frappe.render_template(text or "", {"first_name": self.subscriber.first_name or ""})


LIST_HEADERS = ("List-Unsubscribe", "List-Unsubscribe-Post")


def rename_list_headers(mail):
	"""The make_email_body_message hook. Gmail and Yahoo read only the standard header names."""
	for name in LIST_HEADERS:
		if value := mail.msg_root.get(f"X-{name}"):
			del mail.msg_root[f"X-{name}"]
			mail.set_header(name, value)
