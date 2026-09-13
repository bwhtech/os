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
		frappe.sendmail(
			recipients=[self.subscriber.email],
			sender=settings.get_sender(),
			subject=self.render(self.subject),
			message=frappe.render_template(
				TEMPLATE,
				{"body": self.render(self.body), "button": self.button, "settings": settings},
			),
			reference_doctype="Subscriber",
			reference_name=self.subscriber.name,
			# Slice 5 adds our own unsubscribe link and List-Unsubscribe header.
			add_unsubscribe_link=0,
		)

	def render(self, text: str) -> str:
		"""Subjects and bodies can use Jinja, for example {{ first_name }}."""
		return frappe.render_template(text or "", {"first_name": self.subscriber.first_name or ""})
