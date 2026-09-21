"""Turn the welcome email switch on for every form that sent one before it existed.

Until now a form sent its welcome email whenever it had a subject, and a form with a lead
magnet also needed `send_welcome_with_lead_magnet`. That column is gone from the doctype but
still in the table on a site that migrated to it, so read it where it is there.
"""

import frappe

OLD_SWITCH = "send_welcome_with_lead_magnet"


def execute():
	has_old_switch = frappe.db.has_column("Signup Form", OLD_SWITCH)
	fields = ["name", "welcome_subject", "lead_magnet"] + ([OLD_SWITCH] if has_old_switch else [])

	for form in frappe.get_all("Signup Form", fields=fields):
		sends = bool(form.welcome_subject) and (
			not form.lead_magnet or not has_old_switch or bool(form.get(OLD_SWITCH))
		)
		# set_value, not save: the new check would throw on a form with a subject but no content.
		frappe.db.set_value("Signup Form", form.name, "send_welcome_email", int(sends))
