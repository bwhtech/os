import frappe
from frappe.tests import IntegrationTestCase

from bwh_os.videos.api import get_attachment_counts, get_series, move_video


def make_series(title: str = "Frappe Monthly") -> str:
	return frappe.get_doc({"doctype": "BWH Video Series", "title": title}).insert().name


def make_video(title: str, series: str | None = None, **values) -> str:
	return frappe.get_doc({"doctype": "BWH Video", "title": title, "series": series, **values}).insert().name


def positions(series: str) -> dict[str, int]:
	rows = frappe.get_all("BWH Video", filters={"series": series}, fields=["title", "position"])
	return {row.title: row.position for row in rows}


class IntegrationTestVideos(IntegrationTestCase):
	def test_new_video_is_an_idea(self):
		video = frappe.get_doc("BWH Video", make_video("One-off"))

		self.assertEqual(video.status, "Idea")
		self.assertEqual(video.position, 0)

	def test_videos_join_a_series_at_the_end(self):
		series = make_series()
		make_video("One", series)
		make_video("Two", series)

		self.assertEqual(positions(series), {"One": 1, "Two": 2})

	def test_saving_keeps_the_position(self):
		series = make_series()
		video = frappe.get_doc("BWH Video", make_video("One", series))
		make_video("Two", series)

		# Loaded fresh, like the API does, so `series` comes back from the database as text.
		video = frappe.get_doc("BWH Video", video.name)
		video.research = "<p>Notes</p>"
		video.save()

		# The saved document itself, not only the database after the on_update repair.
		self.assertEqual(video.position, 1)
		self.assertEqual(positions(series), {"One": 1, "Two": 2})

	def test_client_cannot_set_the_position(self):
		series = make_series()
		make_video("One", series)
		video = frappe.get_doc("BWH Video", make_video("Two", series))

		video.position = 9
		video.save()

		self.assertEqual(frappe.db.get_value("BWH Video", video.name, "position"), 2)

	def test_move_shifts_the_other_videos(self):
		series = make_series()
		make_video("One", series)
		make_video("Two", series)
		three = make_video("Three", series)

		move_video(three, 1)

		self.assertEqual(positions(series), {"Three": 1, "One": 2, "Two": 3})

	def test_leaving_a_series_closes_the_gap(self):
		first, second = make_series("First"), make_series("Second")
		make_video("One", first)
		two = frappe.get_doc("BWH Video", make_video("Two", first))
		make_video("Three", first)
		make_video("Other", second)

		two.series = second
		two.save()

		self.assertEqual(positions(first), {"One": 1, "Three": 2})
		self.assertEqual(positions(second), {"Other": 1, "Two": 2})

	def test_delete_closes_the_gap(self):
		series = make_series()
		one = make_video("One", series)
		make_video("Two", series)

		frappe.delete_doc("BWH Video", one)

		self.assertEqual(positions(series), {"Two": 1})

	def test_removing_the_series_resets_the_position(self):
		series = make_series()
		video = frappe.get_doc("BWH Video", make_video("One", series))

		video.series = None
		video.save()

		self.assertEqual(video.position, 0)

	def test_series_counts_videos(self):
		series = make_series("Counted")
		make_video("One", series, status="Published")
		make_video("Two", series)
		make_series("Empty")

		rows = {row.title: row for row in get_series()}

		self.assertEqual(rows["Counted"].video_count, 2)
		self.assertEqual(rows["Counted"].published_count, 1)
		self.assertEqual(rows["Empty"].video_count, 0)
		self.assertEqual(rows["Empty"].published_count, 0)

	def test_attachment_counts_include_links(self):
		video = make_video("With files")
		for url in ("https://frappe.io/docs", "https://github.com/frappe/frappe"):
			frappe.get_doc(
				{"doctype": "File", "file_url": url, "attached_to_doctype": "BWH Video", "attached_to_name": video}
			).insert()

		self.assertEqual(get_attachment_counts()[str(video)], 2)

	def test_move_needs_a_series(self):
		with self.assertRaises(frappe.ValidationError):
			move_video(make_video("One-off"), 1)

	def test_only_system_managers_use_the_api(self):
		frappe.set_user("Guest")
		try:
			with self.assertRaises(frappe.PermissionError):
				get_series()
		finally:
			frappe.set_user("Administrator")
