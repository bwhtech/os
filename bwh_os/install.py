import frappe

from bwh_os.mailing.api import SIGNUP_API_ROLE
from bwh_os.social.oauth_apps import ensure_connected_apps


def after_install():
	ensure_signup_api_role()
	ensure_connected_apps()


def after_migrate():
	ensure_signup_api_role()
	ensure_connected_apps()


def ensure_signup_api_role():
	"""The role for the API user that the website uses to post signups. It has no desk access."""
	if frappe.db.exists("Role", SIGNUP_API_ROLE):
		return
	frappe.get_doc({"doctype": "Role", "role_name": SIGNUP_API_ROLE, "desk_access": 0}).insert(
		ignore_permissions=True
	)
