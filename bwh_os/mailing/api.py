import frappe


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
