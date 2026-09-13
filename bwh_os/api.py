import frappe


@frappe.whitelist(methods=["GET"])
def get_count(doctype: str, filters: dict | list | str | None = None) -> int:
	"""Row count for a paged list in OS. Takes the same filters as /api/v2/document, child table ones too.

	A GET request carries `filters` as a JSON string.
	"""
	if isinstance(filters, str):
		filters = frappe.parse_json(filters)
	rows = frappe.get_list(doctype, filters=filters or {}, fields=[{"COUNT": "*", "as": "count"}])
	return rows[0]["count"] if rows else 0
