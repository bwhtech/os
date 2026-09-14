"""A small client for the Turso HTTP API. See "Turso client" in specs/02-blog.md.

The blog's Netlify functions own the database. OS reads and writes it live with the credentials in
Blog Settings.
"""

import re
from urllib.parse import urlparse

import frappe
import requests
from frappe import _

TIMEOUT = 10
# The Turso dashboard gives `libsql://` and `turso://` URLs. The HTTP API is the same host.
SCHEME = re.compile(r"^(libsql|turso|https?)://")

Statement = str | tuple[str, list]


class TursoNotConfiguredError(frappe.ValidationError):
	pass


class TursoError(frappe.ValidationError):
	pass


class Turso:
	def __init__(self, url: str, token: str):
		self.base_url = SCHEME.sub("https://", url.strip()).rstrip("/")
		self.token = token

	@classmethod
	def from_settings(cls) -> "Turso":
		settings = frappe.get_cached_doc("Blog Settings")
		token = settings.get_password("turso_token", raise_exception=False)
		if not settings.turso_url or not token:
			raise TursoNotConfiguredError(_("Set the Turso URL and token in Blog settings"))
		return cls(settings.turso_url, token)

	@property
	def host(self) -> str:
		return urlparse(self.base_url).hostname or ""

	def query(self, sql: str, args: list | None = None) -> list[dict]:
		return self.pipeline([(sql, args or [])])[0]

	def pipeline(self, statements: list[Statement]) -> list[list[dict]]:
		"""Run the statements in one request. Returns the rows of each statement, as dicts."""
		executes = [execute_request(statement) for statement in statements]
		results = self.post({"requests": [*executes, {"type": "close"}]})["results"]
		return [read_rows(result) for result in results[: len(statements)]]

	def post(self, body: dict) -> dict:
		try:
			response = requests.post(
				f"{self.base_url}/v2/pipeline",
				json=body,
				headers={"Authorization": f"Bearer {self.token}"},
				timeout=TIMEOUT,
			)
		except requests.RequestException as error:
			raise TursoError(_("Could not reach Turso at {0}").format(self.host)) from error
		if response.status_code in (401, 403):
			raise TursoError(_("Turso did not accept the token for {0}").format(self.host))
		if not response.ok:
			raise TursoError(_("Turso responded with {0}").format(response.status_code))
		return response.json()


def execute_request(statement: Statement) -> dict:
	sql, args = (statement, []) if isinstance(statement, str) else statement
	return {"type": "execute", "stmt": {"sql": sql, "args": [to_value(arg) for arg in args]}}


def read_rows(result: dict) -> list[dict]:
	if result["type"] == "error":
		raise TursoError(result["error"]["message"])
	data = result["response"]["result"]
	names = [column["name"] for column in data["cols"]]
	return [dict(zip(names, map(from_value, row), strict=True)) for row in data["rows"]]


def to_value(value) -> dict:
	"""Turso takes each argument with its type. Integers go as strings, so they keep 64 bits."""
	if value is None:
		return {"type": "null"}
	if isinstance(value, bool | int):
		return {"type": "integer", "value": str(int(value))}
	if isinstance(value, float):
		return {"type": "float", "value": value}
	return {"type": "text", "value": str(value)}


def from_value(cell: dict):
	match cell["type"]:
		case "null":
			return None
		case "integer":
			return int(cell["value"])
		case _:
			return cell["value"]
