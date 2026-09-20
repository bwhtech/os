"""Give every lead magnet the slug its download page is served at.

Oldest first, so the plain slug goes to the magnet that has been around longest and a
later namesake takes the `-2`.
"""

import frappe

from bwh_os.mailing.lead_magnet_page import LeadMagnetRoute


def execute():
	for name in frappe.get_all("Lead Magnet", filters={"route": ("is", "not set")}, order_by="creation", pluck="name"):
		magnet = frappe.get_doc("Lead Magnet", name)
		LeadMagnetRoute(magnet).validate()
		# set_value, not save: a magnet written before this change has no delivery email yet,
		# and the validations added later in this series would throw on it.
		frappe.db.set_value("Lead Magnet", name, "route", magnet.route)
