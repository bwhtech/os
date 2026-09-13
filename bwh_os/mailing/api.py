import frappe
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


@frappe.whitelist(methods=["GET"])
def get_signup_counts() -> dict[str, int]:
	"""Subscriber count per signup form."""
	frappe.only_for("System Manager")
	subscriber = frappe.qb.DocType("Subscriber")
	rows = (
		frappe.qb.from_(subscriber)
		.select(subscriber.source_form, Count("*").as_("count"))
		.where(subscriber.source_form.isnotnull())
		.groupby(subscriber.source_form)
		.run(as_dict=True)
	)
	return {row.source_form: row.count for row in rows}
