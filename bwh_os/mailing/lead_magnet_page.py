"""The public download page at /download/<route>.

The page stands between the link in an email and the file. A GET shows the title and a
button; only the POST behind that button hands the file over and logs the download. Mail
scanners follow links but do not submit forms, so this keeps robots out of the download
count. `bwh_os.mailing.api.unsubscribe` splits GET and POST for the same reason.
"""

import mimetypes

import frappe
from frappe.website.page_renderers.base_renderer import BaseRenderer
from frappe.website.utils import cleanup_page_name
from werkzeug.wrappers import Response

ROUTE_PREFIX = "download/"
TEMPLATE = "bwh_os/templates/pages/lead_magnet_download.html"


class LeadMagnetRoute:
	"""Gives a lead magnet a unique slug for its download page."""

	def __init__(self, magnet):
		self.magnet = magnet

	def validate(self):
		self.magnet.route = self.unique(cleanup_page_name(self.magnet.route or self.magnet.title))

	def unique(self, slug: str) -> str:
		slug = slug or self.magnet.name
		candidate, number = slug, 1
		while frappe.db.exists("Lead Magnet", {"route": candidate, "name": ("!=", self.magnet.name)}):
			number += 1
			candidate = f"{slug}-{number}"
		return candidate


class LeadMagnetDownloadPage(BaseRenderer):
	"""Serves /download/<route>. The subscriber token in the query stands in for a login."""

	def __init__(self, path=None, http_status_code=None):
		super().__init__(path=path, http_status_code=http_status_code)
		self.magnet = (
			find_magnet(self.path.removeprefix(ROUTE_PREFIX)) if self.path.startswith(ROUTE_PREFIX) else None
		)

	def can_render(self) -> bool:
		return bool(self.magnet)

	def render(self) -> Response:
		# A Pending subscriber has not confirmed, so the file waits for the confirm link.
		subscriber = frappe.db.get_value(
			"Subscriber", {"token": frappe.form_dict.get("token"), "status": ("!=", "Pending")}
		)
		if not subscriber:
			return self.page({"invalid": True}, http_status_code=404)

		magnet = frappe.get_doc("Lead Magnet", self.magnet)
		if frappe.request and frappe.request.method == "POST":
			return send_file(magnet, subscriber)

		file = magnet.get_file()
		return self.page(
			{
				"magnet": magnet,
				"file_name": file.file_name,
				"file_size": readable_size(file.file_size),
				# A logged-in browser must send the CSRF token with the POST.
				"csrf_token": frappe.sessions.get_csrf_token() if frappe.session.user != "Guest" else None,
			}
		)

	def page(self, context: dict, http_status_code: int | None = None) -> Response:
		company_name = frappe.get_cached_value("Mailing Settings", "Mailing Settings", "company_name")
		return self.build_response(
			frappe.render_template(TEMPLATE, {**context, "company_name": company_name}),
			http_status_code,
		)


def send_file(magnet, subscriber: str) -> Response:
	"""Log the download and hand the file over. POST commits by itself."""
	magnet.log_download(subscriber)
	file = magnet.get_file()
	return Response(
		file.get_content(),
		mimetype=mimetypes.guess_type(file.file_name)[0] or "application/octet-stream",
		headers={"Content-Disposition": f'attachment; filename="{file.file_name}"'},
	)


def find_magnet(route: str) -> str | None:
	return frappe.db.get_value("Lead Magnet", {"route": route}) if route else None


def readable_size(size: int | None) -> str:
	"""Enough to tell a one-page checklist from a 90-page book."""
	if not size:
		return ""
	if size < 1024 * 1024:
		return f"{round(size / 1024)} KB"
	return f"{size / (1024 * 1024):.1f} MB"
