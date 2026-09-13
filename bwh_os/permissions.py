import frappe


def has_os_access() -> bool:
	return "System Manager" in frappe.get_roles()
