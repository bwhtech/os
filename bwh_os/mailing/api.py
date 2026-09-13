import frappe
from frappe import _
from frappe.query_builder.functions import Count

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


@frappe.whitelist(methods=["GET"])
def get_signup_counts() -> dict[str, int]:
	"""Subscriber count per signup form."""
	return count_by("Subscriber", "source_form")


@frappe.whitelist(methods=["GET"])
def get_download_counts() -> dict[str, int]:
	"""Download count per lead magnet."""
	return count_by("Lead Magnet Download", "lead_magnet")


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
