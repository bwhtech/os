import frappe
from frappe.tests import IntegrationTestCase

from bwh_os.canvas.api import get_video_canvas


def make_video(title: str = "Signup flow") -> str:
	return str(frappe.get_doc({"doctype": "BWH Video", "title": title}).insert().name)


class IntegrationTestCanvas(IntegrationTestCase):
	def test_video_canvas_is_made_once(self):
		video = make_video()

		first = get_video_canvas(video)
		second = get_video_canvas(video)

		self.assertEqual(first, second)
		self.assertEqual(frappe.db.get_value("BWH Canvas", first, "title"), "Signup flow")

	def test_video_has_one_canvas(self):
		video = make_video()
		get_video_canvas(video)

		with self.assertRaises(frappe.ValidationError):
			frappe.get_doc({"doctype": "BWH Canvas", "title": "Another", "video": video}).insert()

	def test_scratch_canvases_have_no_limit(self):
		frappe.get_doc({"doctype": "BWH Canvas", "title": "One"}).insert()
		frappe.get_doc({"doctype": "BWH Canvas", "title": "Two"}).insert()

	def test_deleting_a_video_deletes_its_canvas(self):
		video = make_video()
		canvas = get_video_canvas(video)

		frappe.delete_doc("BWH Video", video)

		self.assertFalse(frappe.db.exists("BWH Canvas", canvas))

	def test_unknown_video_has_no_canvas(self):
		with self.assertRaises(frappe.DoesNotExistError):
			get_video_canvas("999999")
