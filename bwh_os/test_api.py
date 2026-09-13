# Copyright (c) 2026, BWH and contributors
# For license information, please see license.txt

import frappe
from frappe.tests import IntegrationTestCase

from bwh_os.api import get_count
from bwh_os.mailing.api import add_subscriber


class IntegrationTestApi(IntegrationTestCase):
	def tearDown(self):
		frappe.set_user("Administrator")

	def test_count_follows_status_and_child_table_filters(self):
		tag = f"test-count-{frappe.generate_hash(length=6)}"
		for index in range(3):
			add_subscriber(f"count{index}-{tag}@example.com", tags=[tag])
		frappe.db.set_value("Subscriber", f"count0-{tag}@example.com", "status", "Unsubscribed")

		self.assertEqual(get_count("Subscriber", {"tags.tag": tag}), 3)
		self.assertEqual(get_count("Subscriber", f'{{"tags.tag": "{tag}", "status": "Active"}}'), 2)

	def test_count_needs_read_permission(self):
		frappe.set_user("Guest")

		with self.assertRaises(frappe.PermissionError):
			get_count("Subscriber")
