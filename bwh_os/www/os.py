import frappe
from frappe.utils import get_system_timezone

no_cache = 1


def get_context():
	if frappe.session.user == "Guest":
		frappe.local.flags.redirect_location = "/login?redirect-to=/os"
		raise frappe.Redirect

	frappe.only_for("System Manager")
	context = frappe._dict()
	context.boot = get_boot()
	context.boot.csrf_token = frappe.sessions.get_csrf_token()
	return context


@frappe.whitelist(methods=["POST"], allow_guest=True)
def get_context_for_dev() -> dict:
	if not frappe.conf.developer_mode:
		frappe.throw("This method is only meant for developer mode")
	return get_boot()


def get_boot() -> frappe._dict:
	return frappe._dict(
		{
			"frappe_version": frappe.__version__,
			"site_name": frappe.local.site,
			"read_only_mode": frappe.flags.read_only,
			"system_timezone": get_system_timezone(),
		}
	)
