# Copyright (c) 2026, BWH and contributors
# For license information, please see license.txt

import frappe
from frappe.tests import IntegrationTestCase

from bwh_os.mailing.emails import add_footer
from bwh_os.mailing.youtube_video import crop_to_widescreen, parse_video_id

EMAIL = "<html><body><table><tr><td><p>Hello</p>{block}</td></tr></table></body></html>"
FOOTER_BLOCK = '<div data-email-footer=""></div>'


class IntegrationTestEditorBlocks(IntegrationTestCase):
	def setUp(self):
		settings = frappe.get_single("Mailing Settings")
		settings.company_name = "BWH Technologies LLP"
		settings.youtube_url = "https://www.youtube.com/@bwh"
		settings.x_url = ""
		settings.save()

	def test_footer_block_takes_the_place_of_the_auto_footer(self):
		html = add_footer(EMAIL.format(block=FOOTER_BLOCK + "<p>After</p>"), "https://x.test/unsub", extra="<img pixel>")

		self.assertNotIn("data-email-footer", html)
		self.assertEqual(html.count("BWH Technologies LLP"), 1)
		self.assertLess(html.index("BWH Technologies LLP"), html.index("After"))
		self.assertIn('href="https://x.test/unsub"', html)
		self.assertIn('href="https://www.youtube.com/@bwh"', html)
		self.assertNotIn(">X<", html)
		self.assertLess(html.index("After"), html.index("<img pixel>"))

	def test_email_without_block_gets_the_footer_at_the_end(self):
		html = add_footer(EMAIL.format(block=""), None)

		self.assertLess(html.index("Hello"), html.index("BWH Technologies LLP"))
		self.assertNotIn("Unsubscribe", html)

	def test_parse_video_id(self):
		for url in (
			"https://www.youtube.com/watch?v=dQw4w9WgXcQ",
			"https://youtube.com/watch?feature=share&v=dQw4w9WgXcQ&t=10",
			"https://youtu.be/dQw4w9WgXcQ?si=abc",
			"https://www.youtube.com/shorts/dQw4w9WgXcQ",
			"https://www.youtube.com/live/dQw4w9WgXcQ",
		):
			self.assertEqual(parse_video_id(url), "dQw4w9WgXcQ", url)

		with self.assertRaises(frappe.ValidationError):
			parse_video_id("https://vimeo.com/123")

	def test_crop_removes_the_bars_of_a_4_3_thumbnail(self):
		from PIL import Image

		self.assertEqual(crop_to_widescreen(Image.new("RGB", (480, 360))).size, (480, 270))
		self.assertEqual(crop_to_widescreen(Image.new("RGB", (1280, 720))).size, (1280, 720))
