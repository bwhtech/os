import frappe
from werkzeug.wrappers import Response


@frappe.whitelist(methods=["GET"], allow_guest=True)
def service_worker() -> Response:
	"""The OS service worker, served so it can control /os.

	A worker controls only the paths under its own URL. Its file lives under /assets, so this
	response gives the `Service-Worker-Allowed` header that lifts that limit.
	"""
	with open(frappe.get_app_path("bwh_os", "public", "service-worker.js")) as file:
		script = file.read()

	return Response(
		script,
		content_type="application/javascript",
		headers={"Service-Worker-Allowed": "/os", "Cache-Control": "no-cache"},
	)
