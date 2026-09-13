# Copyright (c) 2026, BWH and contributors
# For license information, please see license.txt

import frappe
from frappe.tests import IntegrationTestCase

from bwh_os.mailing.api import add_subscriber, import_subscribers, preview_subscriber_import

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

	def test_import_adds_new_rows_and_tags_known_ones(self):
		mapping = preview_subscriber_import(CSV)["mapping"]

		counts = import_subscribers(CSV, mapping, tags=["test-import"])

		self.assertEqual(counts, {"New": 1, "Existing": 1, "Invalid": 1, "Duplicate": 1})
		new = frappe.get_doc("Subscriber", "new.one@example.com")
		self.assertEqual(new.status, "Active")
		self.assertEqual(new.first_name, "Ana")
		self.assertEqual([row.tag for row in new.tags], ["test-import", "test-cohort-1"])

		known = frappe.get_doc("Subscriber", "known@example.com")
		self.assertEqual(
			[row.tag for row in known.tags], ["test-existing", "test-import", "test-cohort-1", "test-discord"]
		)

	def test_import_keeps_known_subscriber_status(self):
		frappe.db.set_value("Subscriber", "known@example.com", "status", "Unsubscribed")

		import_subscribers("email\nknown@example.com\n", {"email": "email"})

		self.assertEqual(frappe.db.get_value("Subscriber", "known@example.com", "status"), "Unsubscribed")
		frappe.db.set_value("Subscriber", "known@example.com", "status", "Active")

	def test_first_name_column_wins_over_full_name(self):
		csv = "Email;First Name;Name\nsemi@example.com;Sam;Samuel Jones\n"

		preview = preview_subscriber_import(csv)

		self.assertEqual(preview["mapping"]["first_name"], "First Name")
		self.assertEqual(preview["rows"][0]["first_name"], "Sam")

	def test_import_needs_an_email_column(self):
		with self.assertRaises(frappe.ValidationError):
			import_subscribers("Name\nAna\n", {"first_name": "Name"})
