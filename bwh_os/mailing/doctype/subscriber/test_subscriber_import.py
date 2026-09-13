# Copyright (c) 2026, BWH and contributors
# For license information, please see license.txt

from unittest.mock import patch

import frappe
from frappe.tests import IntegrationTestCase

from bwh_os.mailing.api import add_subscriber, import_subscribers, preview_subscriber_import
from bwh_os.mailing.subscriber_import import PROGRESS_EVENT, SubscriberImport, run_import_job

CSV = """\ufeffE-mail Address,Full Name,Tags,Country
new.one@example.com,Ana Maria Lopez,test-cohort-1,IN
known@example.com,Known Person,test-cohort-1; test-discord,US
not-an-email,Nobody,,IN
NEW.ONE@example.com,Ana Again,,IN

"""


class IntegrationTestSubscriberImport(IntegrationTestCase):
	# Records live for the whole class, so each test uses its own new emails.
	def setUp(self):
		if not frappe.db.exists("Subscriber", "known@example.com"):
			add_subscriber("known@example.com", tags=["test-existing"])

	def test_preview_maps_columns_by_name_and_counts_rows(self):
		preview = preview_subscriber_import(CSV.replace("new.one@", "preview.only@").replace("NEW.ONE@", "PREVIEW.ONLY@"))

		self.assertEqual(
			preview["mapping"],
			{"email": "E-mail Address", "first_name": None, "full_name": "Full Name", "tags": "Tags"},
		)
		self.assertEqual(preview["total"], 4)
		self.assertEqual(preview["counts"], {"New": 1, "Existing": 1, "Invalid": 1, "Duplicate": 1})
		self.assertEqual(preview["rows"][0]["first_name"], "Ana")
		self.assertEqual(preview["columns"][3], {"name": "Country", "samples": ["IN", "US", "IN"]})
		self.assertFalse(frappe.db.exists("Subscriber", "preview.only@example.com"))

	def test_import_starts_a_background_job(self):
		with patch("bwh_os.mailing.subscriber_import.frappe.enqueue") as enqueue:
			reply = import_subscribers(CSV, {"email": "E-mail Address"}, tags=["test-import"])

		self.assertEqual(reply["total"], 4)
		self.assertEqual(len(reply["import_id"]), 12)
		kwargs = enqueue.call_args.kwargs
		self.assertEqual(enqueue.call_args.args[0], run_import_job)
		self.assertEqual(kwargs["queue"], "long")
		self.assertEqual(kwargs["import_id"], reply["import_id"])
		self.assertEqual(kwargs["tags"], ["test-import"])
		self.assertFalse(frappe.db.exists("Subscriber", "new.one@example.com"))

	def test_job_adds_new_rows_and_tags_known_ones(self):
		mapping = preview_subscriber_import(CSV)["mapping"]

		events = run_job(CSV, mapping, tags=["test-import"])

		self.assertEqual(events[0]["status"], "Running")
		self.assertEqual(events[-1]["status"], "Done")
		self.assertEqual(events[-1]["done"], 4)
		self.assertEqual(
			events[-1]["counts"], {"New": 1, "Existing": 1, "Invalid": 1, "Duplicate": 1, "Failed": 0}
		)
		new = frappe.get_doc("Subscriber", "new.one@example.com")
		self.assertEqual(new.status, "Active")
		self.assertEqual(new.first_name, "Ana")
		self.assertEqual([row.tag for row in new.tags], ["test-import", "test-cohort-1"])

		known = frappe.get_doc("Subscriber", "known@example.com")
		self.assertEqual(
			[row.tag for row in known.tags], ["test-existing", "test-import", "test-cohort-1", "test-discord"]
		)

	def test_job_keeps_known_subscriber_status(self):
		frappe.db.set_value("Subscriber", "known@example.com", "status", "Unsubscribed")

		run_job("email\nknown@example.com\n", {"email": "email"}, tags=["test-import-2"])

		self.assertEqual(frappe.db.get_value("Subscriber", "known@example.com", "status"), "Unsubscribed")
		frappe.db.set_value("Subscriber", "known@example.com", "status", "Active")

	def test_failed_row_does_not_stop_the_others(self):
		csv = "email\nfails@example.com\nafter.fail@example.com\n"
		insert = SubscriberImport.insert

		def insert_or_fail(self, row):
			insert(self, row)
			if row.email == "fails@example.com":
				raise frappe.ValidationError("Row broke")

		with patch.object(SubscriberImport, "insert", insert_or_fail):
			events = run_job(csv, {"email": "email"})

		self.assertEqual(events[-1]["counts"]["Failed"], 1)
		self.assertEqual(events[-1]["counts"]["New"], 1)
		self.assertEqual(events[-1]["errors"], [{"email": "fails@example.com", "error": "Row broke"}])
		self.assertFalse(frappe.db.exists("Subscriber", "fails@example.com"))
		self.assertTrue(frappe.db.exists("Subscriber", "after.fail@example.com"))

	def test_first_name_column_wins_over_full_name(self):
		csv = "Email;First Name;Name\nsemi@example.com;Sam;Samuel Jones\n"

		preview = preview_subscriber_import(csv)

		self.assertEqual(preview["mapping"]["first_name"], "First Name")
		self.assertEqual(preview["rows"][0]["first_name"], "Sam")

	def test_import_needs_an_email_column(self):
		with self.assertRaises(frappe.ValidationError):
			import_subscribers("Name\nAna\n", {"first_name": "Name"})


def run_job(content: str, mapping: dict, tags: list[str] | None = None) -> list[dict]:
	"""Run the import job in the test transaction and return its progress events."""
	with (
		patch("bwh_os.mailing.subscriber_import.frappe.db.commit"),
		patch("bwh_os.mailing.subscriber_import.frappe.publish_realtime") as publish,
	):
		run_import_job("test-import", content, mapping, tags or [])
	return [c.args[1] for c in publish.call_args_list if c.args[0] == PROGRESS_EVENT]
