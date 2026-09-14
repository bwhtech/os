from unittest.mock import MagicMock, patch

import requests
from frappe.tests import UnitTestCase

from bwh_os.blog.turso import Turso, TursoError


def ok(cols: list[str], rows: list[list[dict]]) -> dict:
	return {
		"type": "ok",
		"response": {"type": "execute", "result": {"cols": [{"name": c} for c in cols], "rows": rows}},
	}


def response(results: list[dict], status: int = 200) -> MagicMock:
	mock = MagicMock(status_code=status, ok=status < 400)
	mock.json.return_value = {"results": [*results, {"type": "ok", "response": {"type": "close"}}]}
	return mock


class UnitTestTurso(UnitTestCase):
	def test_url_schemes_become_https(self):
		for url in ("libsql://db.turso.io", "turso://db.turso.io/", " https://db.turso.io "):
			turso = Turso(url, "token")
			self.assertEqual(turso.base_url, "https://db.turso.io")
			self.assertEqual(turso.host, "db.turso.io")

	@patch("bwh_os.blog.turso.requests.post")
	def test_pipeline_sends_typed_args_and_reads_rows(self, post):
		post.return_value = response(
			[
				ok(
					["id", "name", "note"],
					[[{"type": "integer", "value": "7"}, {"type": "text", "value": "Ada"}, {"type": "null"}]],
				),
				ok(["n"], [[{"type": "integer", "value": "0"}]]),
			]
		)

		rows = Turso("libsql://db.turso.io", "secret").pipeline(
			[
				("SELECT * FROM comments WHERE id = ? AND name = ? AND x IS ?", [7, "Ada", None]),
				"SELECT 0 AS n",
			]
		)

		self.assertEqual(rows, [[{"id": 7, "name": "Ada", "note": None}], [{"n": 0}]])
		url = post.call_args.args[0]
		body = post.call_args.kwargs["json"]
		self.assertEqual(url, "https://db.turso.io/v2/pipeline")
		self.assertEqual(post.call_args.kwargs["headers"], {"Authorization": "Bearer secret"})
		self.assertEqual(
			body["requests"][0]["stmt"]["args"],
			[{"type": "integer", "value": "7"}, {"type": "text", "value": "Ada"}, {"type": "null"}],
		)
		self.assertEqual(body["requests"][-1], {"type": "close"})

	@patch("bwh_os.blog.turso.requests.post")
	def test_statement_error_raises_with_the_message(self, post):
		post.return_value = response([{"type": "error", "error": {"message": "no such column: nope"}}])

		with self.assertRaisesRegex(TursoError, "no such column"):
			Turso("libsql://db.turso.io", "token").query("SELECT nope FROM comments")

	@patch("bwh_os.blog.turso.requests.post")
	def test_rejected_token_raises(self, post):
		post.return_value = response([], status=401)

		with self.assertRaisesRegex(TursoError, "did not accept the token"):
			Turso("libsql://db.turso.io", "bad").query("SELECT 1")

	@patch("bwh_os.blog.turso.requests.post", side_effect=requests.ConnectionError)
	def test_network_error_raises(self, _post):
		with self.assertRaisesRegex(TursoError, "Could not reach"):
			Turso("libsql://db.turso.io", "token").query("SELECT 1")
