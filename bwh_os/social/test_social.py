import json
from unittest.mock import MagicMock, patch

import frappe
from frappe.integrations.doctype.connected_app.connected_app import ConnectedApp
from frappe.model.document import Document
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, add_to_date, get_datetime, getdate, now_datetime, today

from bwh_os.mailing.doctype.lead_magnet.test_lead_magnet import last_email_to, use_test_email_account
from bwh_os.social.api import (
	connect_channel,
	disconnect_channel,
	get_channels,
	get_posts,
	get_provider_apps,
	publish_post,
	reschedule_post,
	schedule_post,
	set_credentials,
	unschedule_post,
	validate_post,
)
from bwh_os.social.channels import check_expiry
from bwh_os.social.oauth import upsert_channel
from bwh_os.social.oauth_apps import PROVIDERS, ensure_connected_apps, get_app
from bwh_os.social.publisher import JOB_TIMEOUT, Publisher, publish_due_posts, resume_stuck_posts
from bwh_os.social.providers import BadRequest, ReconnectRequired, Release, Retryable
from bwh_os.social.providers.base import Account
from bwh_os.social.providers.linkedin import IMAGE_WAIT_SECONDS, LinkedInProvider
from bwh_os.social.tokens import SKEW_SECONDS, get_token


class SocialTestCase(IntegrationTestCase):
	"""The `Connected App` rows are the ones the site really uses, and the channels outlive a
	test, so every test puts back what it changed."""

	def setUp(self):
		self.channels: list[str] = []
		self.credentials = {
			provider: (app.client_id, app.get_password("client_secret", False))
			for provider, app in ((provider, get_app(provider)) for provider in PROVIDERS)
		}

	def tearDown(self):
		for name in self.channels:
			frappe.delete_doc("Social Channel", name, force=True, ignore_missing=True)
		for provider, (client_id, secret) in self.credentials.items():
			app = get_app(provider)
			app.client_id = client_id
			app.client_secret = secret
			app.save(ignore_permissions=True)
		ensure_connected_apps()

	def make_channel(self, provider: str = "LinkedIn", **values) -> str:
		"""A channel that looks like one a connect just made."""
		name = (
			frappe.get_doc(
				{
					"doctype": "Social Channel",
					"provider": provider,
					"account_id": values.pop("account_id", frappe.generate_hash(length=8)),
					"display_name": values.pop("display_name", "Hussain Nagaria"),
					"user": "Administrator",
					"connected_app": get_app(provider).name,
					**values,
				}
			)
			.insert()
			.name
		)
		self.channels.append(name)
		return name


class IntegrationTestSocialApps(SocialTestCase):
	def test_every_platform_has_a_connected_app(self):
		for provider, wanted in PROVIDERS.items():
			app = get_app(provider)

			self.assertEqual(app.token_uri, wanted.token_uri)
			self.assertEqual([row.scope for row in app.scopes], wanted.scopes)

	def test_a_second_run_writes_nothing(self):
		before = {provider: get_app(provider).modified for provider in PROVIDERS}

		ensure_connected_apps()

		for provider, modified in before.items():
			self.assertEqual(get_app(provider).modified, modified)

	def test_the_endpoints_go_back_to_what_the_code_says(self):
		get_app("LinkedIn").db_set("token_uri", "https://example.com/stale")

		ensure_connected_apps()

		self.assertEqual(get_app("LinkedIn").token_uri, PROVIDERS["LinkedIn"].token_uri)

	def test_the_redirect_uri_of_x_is_our_own_callback(self):
		apps = {app["provider"]: app for app in get_provider_apps()}

		self.assertTrue(apps["X"]["redirect_uri"].endswith("bwh_os.social.x_oauth.callback"))
		self.assertIn("connected_app.callback", apps["LinkedIn"]["redirect_uri"])

	def test_credentials_are_set_without_losing_the_secret(self):
		set_credentials("LinkedIn", "client-one", "secret-one")
		set_credentials("LinkedIn", "client-two")

		app = get_app("LinkedIn")
		self.assertEqual(app.client_id, "client-two")
		self.assertEqual(app.get_password("client_secret"), "secret-one")

	def test_the_panel_knows_when_a_platform_can_connect(self):
		set_credentials("X", "client", "secret")

		apps = {app["provider"]: app for app in get_provider_apps()}
		self.assertTrue(apps["X"]["has_credentials"])


class IntegrationTestSocialChannels(SocialTestCase):
	def test_a_channel_is_named_after_the_account(self):
		name = self.make_channel("LinkedIn", account_id="urn-42")

		self.assertEqual(name, "LinkedIn-urn-42")
		self.assertEqual(frappe.db.get_value("Social Channel", name, "status"), "Connected")

	def test_the_panel_reports_the_days_left(self):
		name = self.make_channel(expires_on=frappe.utils.add_days(frappe.utils.now_datetime(), 6))

		channel = next(row for row in get_channels() if row["name"] == name)
		self.assertEqual(channel["days_left"], 6)

	def test_a_channel_without_an_expiry_reports_none(self):
		name = self.make_channel("X")

		channel = next(row for row in get_channels() if row["name"] == name)
		self.assertIsNone(channel["days_left"])

	def test_an_expired_token_says_why(self):
		channel = frappe.get_doc("Social Channel", self.make_channel())

		channel.mark_expired("LinkedIn asked for a new consent")

		channel.reload()
		self.assertEqual(channel.status, "Expired")
		self.assertEqual(channel.last_error, "LinkedIn asked for a new consent")

	def test_only_system_managers_read_the_channels(self):
		frappe.set_user("Guest")
		self.addCleanup(frappe.set_user, "Administrator")

		self.assertRaises(frappe.PermissionError, get_channels)
		self.assertRaises(frappe.PermissionError, get_provider_apps)


class IntegrationTestSocialConnect(SocialTestCase):
	IDENTITY = {
		"account_id": "urn-connect",
		"display_name": "Hussain Nagaria",
		"handle": None,
		"avatar_url": "https://media.licdn.com/pic.jpg",
		"profile_url": None,
	}

	def make_token_cache(self, provider: str = "LinkedIn", expires_in: int = 60 * 60 * 24 * 60) -> str:
		app = get_app(provider)
		name = f"{app.name}-Administrator"
		frappe.delete_doc("Token Cache", name, force=True, ignore_missing=True)
		cache = frappe.new_doc("Token Cache")
		cache.update(
			{
				"user": "Administrator",
				"connected_app": app.name,
				"access_token": "a-token",
				"expires_in": expires_in,
				"token_type": "bearer",
			}
		)
		cache.insert(ignore_permissions=True)
		self.addCleanup(frappe.delete_doc, "Token Cache", name, force=True, ignore_missing=True)
		return cache.name

	def test_connecting_writes_the_channel(self):
		self.make_token_cache()

		with patch.object(LinkedInProvider, "identity", return_value=self.IDENTITY):
			name = upsert_channel("LinkedIn", "Administrator")
		self.channels.append(name)

		channel = frappe.get_doc("Social Channel", name)
		self.assertEqual(name, "LinkedIn-urn-connect")
		self.assertEqual(channel.status, "Connected")
		self.assertEqual(channel.display_name, "Hussain Nagaria")
		self.assertTrue(channel.expires_on)

	def test_connecting_again_clears_the_old_failure(self):
		self.make_token_cache()
		with patch.object(LinkedInProvider, "identity", return_value=self.IDENTITY):
			name = upsert_channel("LinkedIn", "Administrator")
			self.channels.append(name)
			frappe.get_doc("Social Channel", name).mark_expired("The token has run out")

			self.assertEqual(upsert_channel("LinkedIn", "Administrator"), name)

		channel = frappe.get_doc("Social Channel", name)
		self.assertEqual(channel.status, "Connected")
		self.assertIsNone(channel.last_error)

	def test_a_connect_without_a_token_says_to_start_again(self):
		app = get_app("LinkedIn")
		frappe.delete_doc("Token Cache", f"{app.name}-Administrator", force=True, ignore_missing=True)

		self.assertRaises(frappe.ValidationError, upsert_channel, "LinkedIn", "Administrator")

	def test_connecting_needs_the_credentials_first(self):
		self.assertRaises(frappe.ValidationError, connect_channel, "LinkedIn")

	def test_x_cannot_connect_yet(self):
		set_credentials("X", "client", "secret")

		self.assertRaises(frappe.ValidationError, connect_channel, "X")

	def test_disconnecting_drops_the_token_and_keeps_the_channel(self):
		cache = self.make_token_cache()
		with patch.object(LinkedInProvider, "identity", return_value=self.IDENTITY):
			name = upsert_channel("LinkedIn", "Administrator")
		self.channels.append(name)

		disconnect_channel(name)

		channel = frappe.get_doc("Social Channel", name)
		self.assertEqual(channel.status, "Disconnected")
		self.assertIsNone(channel.expires_on)
		self.assertFalse(frappe.db.exists("Token Cache", cache))


class IntegrationTestSocialTokens(SocialTestCase):
	def test_a_token_that_cannot_refresh_expires_the_channel(self):
		channel = frappe.get_doc("Social Channel", self.make_channel())

		with patch.object(ConnectedApp, "get_active_token", return_value=None):
			self.assertRaises(ReconnectRequired, get_token, channel)

		self.assertEqual(frappe.db.get_value("Social Channel", channel.name, "status"), "Expired")

	def test_a_token_in_its_last_seconds_counts_as_gone(self):
		channel = frappe.get_doc("Social Channel", self.make_channel())
		token_cache = MagicMock()
		token_cache.get_expires_in.return_value = SKEW_SECONDS - 1

		with patch.object(ConnectedApp, "get_active_token", return_value=token_cache):
			self.assertRaises(ReconnectRequired, get_token, channel)

	def test_a_live_token_comes_back(self):
		channel = frappe.get_doc("Social Channel", self.make_channel())
		token_cache = MagicMock()
		token_cache.get_expires_in.return_value = 3600

		with patch.object(ConnectedApp, "get_active_token", return_value=token_cache):
			self.assertIs(get_token(channel), token_cache)


class IntegrationTestLinkedInProvider(SocialTestCase):
	def test_the_identity_comes_from_userinfo(self):
		response = MagicMock()
		response.json.return_value = {"sub": "abc", "name": "Hussain", "picture": "https://p.jpg"}

		with patch.object(LinkedInProvider, "request", return_value=response):
			identity = LinkedInProvider.identity(MagicMock())

		self.assertEqual(identity["account_id"], "abc")
		self.assertEqual(identity["display_name"], "Hussain")
		self.assertEqual(identity["avatar_url"], "https://p.jpg")

	def test_a_dead_token_asks_for_a_reconnect(self):
		response = MagicMock(ok=False, status_code=401, text="expired")

		self.assertIsInstance(LinkedInProvider.error_for(response), ReconnectRequired)

	def test_a_busy_platform_is_worth_another_go(self):
		for status in (429, 503):
			response = MagicMock(ok=False, status_code=status, text="busy")

			self.assertIsInstance(LinkedInProvider.error_for(response), Retryable)

	def test_a_refused_body_is_not(self):
		response = MagicMock(ok=False, status_code=422, text="no")

		self.assertIsInstance(LinkedInProvider.error_for(response), BadRequest)


class IntegrationTestLinkedInMedia(SocialTestCase):
	"""Images go up before the post names them. See `bwh_os.social.providers.linkedin`."""

	def setUp(self):
		super().setUp()
		self.account = Account(token_cache=MagicMock(), account_id="abc", post_name="1")
		self.files: list[str] = []
		# The wait is real seconds LinkedIn needs, and no test has that long.
		self.wait = patch("bwh_os.social.providers.linkedin.time.sleep")
		self.wait.start()
		self.addCleanup(self.wait.stop)

	def tearDown(self):
		for name in self.files:
			frappe.delete_doc("File", name, force=True, ignore_missing=True)
		super().tearDown()

	def make_image(self, name: str = "shot.png") -> dict:
		"""A private `File` like the one the composer uploads onto a post."""
		image = frappe.get_doc(
			{
				"doctype": "File",
				"file_name": f"{frappe.generate_hash(length=6)}-{name}",
				"is_private": 1,
				"content": b"\x89PNG\r\n\x1a\n",
				"decode": False,
			}
		).insert()
		self.files.append(image.name)
		return {"file_url": image.file_url, "kind": "image"}

	def responses(self, urns: list[str]):
		"""What LinkedIn answers: an upload slot per image, then the id of the post."""
		calls = []
		for urn in urns:
			slot = MagicMock()
			slot.json.return_value = {"value": {"uploadUrl": f"https://upload/{urn}", "image": urn}}
			calls += [slot, MagicMock()]
		post = MagicMock()
		post.headers = {"x-restli-id": "urn:li:share:1"}
		return [*calls, post]

	def published_body(self, media: list[dict]) -> dict:
		"""Publish one part with this media and give back the body the post went out with."""
		with patch.object(
			LinkedInProvider, "request", side_effect=self.responses(["urn:li:image:1", "urn:li:image:2"])
		) as request:
			LinkedInProvider.post(self.account, [{"text": "Look", "media": media}], {}, [], lambda _: None)
		return request.call_args.kwargs["json"]

	def test_one_image_rides_along_as_media(self):
		body = self.published_body([self.make_image()])

		self.assertEqual(body["content"], {"media": {"id": "urn:li:image:1", "altText": ""}})

	def test_two_images_become_a_multi_image_post(self):
		body = self.published_body([self.make_image(), self.make_image()])

		self.assertEqual(
			body["content"]["multiImage"]["images"],
			[{"id": "urn:li:image:1", "altText": ""}, {"id": "urn:li:image:2", "altText": ""}],
		)

	def test_a_post_without_images_names_no_content(self):
		body = self.published_body([])

		self.assertNotIn("content", body)

	def test_the_post_waits_for_the_images_it_cannot_ask_about(self):
		with (
			patch("bwh_os.social.providers.linkedin.time.sleep") as sleep,
			patch.object(LinkedInProvider, "request", side_effect=self.responses(["urn:li:image:1"])),
		):
			LinkedInProvider.post(
				self.account, [{"text": "Look", "media": [self.make_image()]}], {}, [], lambda _: None
			)

		sleep.assert_called_once_with(IMAGE_WAIT_SECONDS)

	def test_the_file_goes_up_before_the_post_asks_for_it(self):
		image = self.make_image()

		with patch.object(
			LinkedInProvider, "request", side_effect=self.responses(["urn:li:image:1"])
		) as request:
			LinkedInProvider.post(self.account, [{"text": "Look", "media": [image]}], {}, [], lambda _: None)

		methods = [call.args[0] for call in request.call_args_list]
		self.assertEqual(methods, ["POST", "PUT", "POST"])
		self.assertEqual(request.call_args_list[1].kwargs["data"], b"\x89PNG\r\n\x1a\n")

	def test_a_file_that_is_gone_stops_the_post(self):
		self.assertRaises(
			BadRequest,
			LinkedInProvider.post,
			self.account,
			[{"text": "Look", "media": [{"file_url": "/private/files/nothing.png", "kind": "image"}]}],
			{},
			[],
			lambda _: None,
		)

	def test_a_video_waits_for_its_own_slice(self):
		self.assertRaises(
			BadRequest,
			LinkedInProvider.post,
			self.account,
			[{"text": "Look", "media": [{"file_url": "/private/files/clip.mp4", "kind": "video"}]}],
			{},
			[],
			lambda _: None,
		)


class IntegrationTestSocialExpiry(SocialTestCase):
	"""The daily watch over the tokens. See `bwh_os.social.channels`."""

	def setUp(self):
		super().setUp()
		use_test_email_account()

	def make_channel(self, provider: str = "LinkedIn", **values) -> str:
		values.setdefault("user", "Administrator")
		return super().make_channel(provider, **values)

	def expiring_in(self, days: int, **values) -> Document:
		"""A connected channel whose token dies in `days` days. A negative number is the past."""
		expires_on = add_days(now_datetime(), days)
		return frappe.get_doc("Social Channel", self.make_channel(expires_on=expires_on, **values))

	def emails_about(self, channel: Document) -> int:
		return frappe.db.count(
			"Email Queue", {"reference_doctype": "Social Channel", "reference_name": channel.name}
		)

	def test_a_token_that_ran_out_turns_the_channel_red(self):
		channel = self.expiring_in(-1)

		check_expiry()

		channel.reload()
		self.assertEqual(channel.status, "Expired")
		self.assertIn("Connect LinkedIn again", channel.last_error)

	def test_a_token_with_a_week_left_gets_one_reminder(self):
		channel = self.expiring_in(5)

		check_expiry()
		check_expiry()

		channel.reload()
		self.assertEqual(channel.status, "Connected")
		self.assertEqual(channel.reminder_sent_on, getdate(today()))
		self.assertEqual(self.emails_about(channel), 1)

	def test_the_reminder_says_when_the_token_goes_and_where_to_fix_it(self):
		self.expiring_in(5)

		check_expiry()

		email = last_email_to(frappe.db.get_value("User", "Administrator", "email"))
		self.assertIn("LinkedIn disconnects from BWH OS in 5 days", email["Subject"])
		self.assertIn("/os/social", email.get_body(("html",)).get_content())

	def test_a_young_token_is_left_alone(self):
		channel = self.expiring_in(30)

		check_expiry()

		channel.reload()
		self.assertIsNone(channel.reminder_sent_on)
		self.assertEqual(self.emails_about(channel), 0)

	def test_a_disconnected_channel_is_not_reminded(self):
		channel = self.expiring_in(2, status="Disconnected")

		check_expiry()

		self.assertEqual(self.emails_about(channel), 0)

	def test_a_channel_without_an_expiry_is_skipped(self):
		channel = frappe.get_doc("Social Channel", self.make_channel("X"))

		check_expiry()

		channel.reload()
		self.assertEqual(channel.status, "Connected")
		self.assertEqual(self.emails_about(channel), 0)

	def test_one_broken_channel_does_not_stop_the_rest(self):
		broken = self.expiring_in(-1)
		other = self.expiring_in(-1)

		with patch("bwh_os.social.channels.send_reminder", side_effect=[Exception("no mail"), None]):
			check_expiry()

		self.assertEqual(
			{frappe.db.get_value("Social Channel", name, "status") for name in (broken.name, other.name)},
			{"Expired"},
		)

	def test_a_reconnect_opens_a_new_reminder_window(self):
		channel = self.expiring_in(3)
		check_expiry()

		channel.db_set({"status": "Connected", "reminder_sent_on": None})
		check_expiry()

		self.assertEqual(self.emails_about(channel), 2)


class IntegrationTestSocialPosts(SocialTestCase):
	"""The post document: what it cleans up on save, and what it refuses. See `bwh_os.social.validation`."""

	def setUp(self):
		super().setUp()
		self.posts: list[str] = []

	def tearDown(self):
		for name in self.posts:
			frappe.delete_doc("Social Post", name, force=True, ignore_missing=True)
		super().tearDown()

	def make_post(
		self,
		channels: list[str] | None = None,
		parts: list[dict] | None = None,
		custom: bool = False,
		**values,
	):
		post = frappe.get_doc(
			{
				"doctype": "Social Post",
				"targets": [
					{"channel": channel, "use_custom_content": int(custom)} for channel in (channels or [])
				],
				"parts": parts if parts is not None else [{"text": "Hello from the OS"}],
				**values,
			}
		).insert()
		self.posts.append(post.name)
		return post

	def test_the_title_is_the_start_of_the_first_part(self):
		post = self.make_post(parts=[{"text": "A" * 80 + "\nthe second line"}])

		self.assertEqual(post.title, "A" * 60)

	def test_a_title_you_wrote_stays(self):
		post = self.make_post(title="Launch thread", parts=[{"text": "Something else"}])

		self.assertEqual(post.title, "Launch thread")

	def test_parts_are_numbered_from_one_inside_each_group(self):
		channel = self.make_channel()
		post = self.make_post(
			[channel],
			parts=[
				{"text": "shared one"},
				{"text": "custom one", "channel": channel},
				{"text": "shared two"},
			],
			custom=True,
		)

		numbers = [(row.channel, row.part_no) for row in post.parts]
		self.assertEqual(numbers, [(None, 1), (channel, 1), (None, 2)])

	def test_custom_content_goes_when_the_target_stops_wanting_it(self):
		channel = self.make_channel()
		post = self.make_post(
			[channel],
			parts=[{"text": "shared"}, {"text": "custom", "channel": channel}],
			custom=True,
		)
		self.assertEqual(len(post.parts), 2)

		post.targets[0].use_custom_content = 0
		post.save()

		self.assertEqual([row.text for row in post.parts], ["shared"])

	def test_a_target_reads_its_own_parts_when_it_customizes(self):
		channel = self.make_channel()
		post = self.make_post(
			[channel],
			parts=[{"text": "shared"}, {"text": "custom", "channel": channel}],
			custom=True,
		)

		self.assertEqual([part["text"] for part in post.parts_for(post.targets[0])], ["custom"])

	def test_a_channel_takes_one_row_per_post(self):
		channel = self.make_channel()

		self.assertRaises(frappe.ValidationError, self.make_post, [channel, channel])

	def test_media_needs_a_file_and_a_kind(self):
		self.assertRaises(
			frappe.ValidationError,
			self.make_post,
			parts=[{"text": "Look", "media": json.dumps([{"kind": "image"}])}],
		)
		self.assertRaises(
			frappe.ValidationError,
			self.make_post,
			parts=[{"text": "Look", "media": json.dumps([{"file_url": "/files/a.pdf", "kind": "pdf"}])}],
		)

	def test_a_text_over_the_limit_of_the_platform_is_reported(self):
		channel = self.make_channel()
		post = self.make_post([channel], parts=[{"text": "A" * 3001}])

		result = validate_post(post.name)[0]

		self.assertEqual(result["limit"], 3000)
		self.assertEqual(result["counts"], [3001])
		self.assertIn("LinkedIn takes 3000", result["errors"][0])
		self.assertRaises(frappe.ValidationError, post.check)

	def test_a_linkedin_comment_takes_no_media(self):
		channel = self.make_channel()
		media = json.dumps([{"file_url": "/private/files/a.png", "kind": "image"}])
		post = self.make_post(
			[channel], parts=[{"text": "The post"}, {"text": "The comment", "media": media}]
		)

		self.assertIn("comment takes text only", validate_post(post.name)[0]["errors"][0])

	def test_media_that_left_the_post_is_reported(self):
		channel = self.make_channel()
		post = self.make_post(
			[channel],
			parts=[
				{
					"text": "Look",
					"media": json.dumps([{"file_url": "/private/files/gone.png", "kind": "image"}]),
				}
			],
		)

		self.assertIn("not on the post any more", validate_post(post.name)[0]["errors"][0])

	def test_the_composer_learns_what_the_platform_takes(self):
		channel = self.make_channel()
		post = self.make_post([channel])

		result = validate_post(post.name)[0]

		self.assertEqual(result["max_images"], 20)
		self.assertFalse(result["media_after_part_one"])

	def test_a_post_without_a_channel_cannot_go_out(self):
		post = self.make_post()

		self.assertRaises(frappe.ValidationError, post.check)

	def test_a_dead_channel_stops_the_post(self):
		channel = self.make_channel(status="Expired")
		post = self.make_post([channel])

		self.assertIn("Expired", validate_post(post.name)[0]["errors"][0])

	def test_the_composer_validates_a_post_it_has_not_saved(self):
		channel = self.make_channel()

		results = validate_post(
			json.dumps({"targets": [{"channel": channel}], "parts": [{"text": "A" * 3001}]})
		)

		self.assertEqual(results[0]["counts"], [3001])
		self.assertTrue(results[0]["errors"])

	def test_the_list_holds_the_tabs_apart_and_carries_the_channels(self):
		channel = self.make_channel()
		draft = self.make_post([channel])
		published = self.make_post([channel], status="Published")

		upcoming = [row["name"] for row in get_posts("upcoming")]
		self.assertIn(draft.name, upcoming)
		self.assertNotIn(published.name, upcoming)
		self.assertIn(published.name, [row["name"] for row in get_posts("published")])

		row = next(row for row in get_posts("all") if row["name"] == draft.name)
		self.assertEqual([target["channel"] for target in row["targets"]], [channel])
		self.assertEqual(row["targets"][0]["display_name"], "Hussain Nagaria")


class IntegrationTestSocialPublishing(IntegrationTestSocialPosts):
	"""Putting a post out. The platform is never really called: `Provider.request` is patched
	and `tokens.get_token` hands back a fake, so the tests are about the publisher's own rules."""

	def setUp(self):
		super().setUp()
		self.token_patch = patch("bwh_os.social.publisher.get_token", return_value=MagicMock())
		self.token_patch.start()
		self.addCleanup(self.token_patch.stop)

	def publish(self, post, **patches):
		"""Run the job inline, so a test sees the result without a worker."""
		with patch("frappe.enqueue"), patch.object(LinkedInProvider, "post", **patches) as posted:
			publish_post(post.name)
			Publisher(frappe.get_doc("Social Post", post.name)).run()
		post.reload()
		return posted

	def test_publishing_queues_one_job_and_locks_the_post(self):
		channel = self.make_channel()
		post = self.make_post([channel])

		with patch("frappe.enqueue") as enqueue:
			publish_post(post.name)

		post.reload()
		self.assertEqual(post.status, "Publishing")
		self.assertEqual(post.targets[0].status, "Pending")
		self.assertEqual(enqueue.call_count, 1)
		self.assertEqual(enqueue.call_args.kwargs["job_id"], f"social_post::{post.name}")

	def test_a_post_that_went_out_cannot_change(self):
		channel = self.make_channel()
		post = self.make_post([channel])
		self.publish(post, side_effect=release_parts)

		post.parts[0].text = "A different post"

		self.assertRaises(frappe.ValidationError, post.save)

	def test_a_published_post_keeps_the_link_of_the_platform(self):
		channel = self.make_channel()
		post = self.make_post([channel])

		self.publish(post, side_effect=release_parts)

		target = post.targets[0]
		self.assertEqual(post.status, "Published")
		self.assertEqual(target.status, "Published")
		self.assertEqual(target.release_id, "urn:li:share:1")
		self.assertIn("linkedin.com/feed/update", target.release_url)
		self.assertTrue(post.published_at)

	def test_one_channel_out_of_two_makes_the_post_partial(self):
		good = self.make_channel(account_id="good")
		bad = self.make_channel(account_id="bad")
		post = self.make_post([good, bad])

		def publish(account, parts, settings, released, on_release):
			if account.account_id == "bad":
				raise BadRequest("LinkedIn said no")
			release_parts(account, parts, settings, released, on_release)

		self.publish(post, side_effect=publish)

		self.assertEqual(post.status, "Partial")
		self.assertEqual({target.status for target in post.targets}, {"Published", "Failed"})
		failed = next(target for target in post.targets if target.status == "Failed")
		self.assertEqual(failed.error_kind, "Bad Request")

	def test_every_channel_failing_fails_the_post(self):
		channel = self.make_channel()
		post = self.make_post([channel])

		self.publish(post, side_effect=BadRequest("LinkedIn said no"))

		self.assertEqual(post.status, "Failed")
		self.assertIsNone(post.published_at)

	def test_a_dead_token_asks_for_a_reconnect_instead_of_a_retry(self):
		channel = self.make_channel()
		post = self.make_post([channel])

		self.publish(post, side_effect=ReconnectRequired("LinkedIn wants a new consent"))

		self.assertEqual(post.targets[0].error_kind, "Reconnect")

	def test_an_attempt_that_never_answered_is_not_made_again(self):
		channel = self.make_channel()
		post = self.make_post([channel])
		# A job that died between the call and the answer leaves the flag and nothing else.
		post.targets[0].db_set("publish_attempted_at", frappe.utils.now_datetime())

		posted = self.publish(post, side_effect=release_parts)

		self.assertEqual(posted.call_count, 0)
		self.assertEqual(post.targets[0].error_kind, "Unconfirmed")
		self.assertEqual(post.status, "Failed")

	def test_a_thread_carries_on_from_the_part_that_landed(self):
		channel = self.make_channel()
		post = self.make_post([channel], parts=[{"text": "The post"}, {"text": "The comment"}])

		asked = []

		def publish(account, parts, settings, released, on_release):
			asked.append([row["part_no"] for row in released])
			release_parts(account, parts, settings, released, on_release)

		self.publish(post, side_effect=publish)
		self.assertEqual(asked, [[]])
		self.assertEqual([row["part_no"] for row in json.loads(post.targets[0].released_parts)], [1, 2])

	def test_a_post_cannot_go_out_twice(self):
		channel = self.make_channel()
		post = self.make_post([channel])
		self.publish(post, side_effect=release_parts)

		self.assertRaises(frappe.ValidationError, publish_post, post.name)


class IntegrationTestSocialSchedule(IntegrationTestSocialPosts):
	"""A time on a post, and the minute that acts on it. See `bwh_os.social.publisher`."""

	def in_an_hour(self) -> str:
		return add_to_date(now_datetime(), hours=1).strftime("%Y-%m-%d %H:%M:%S")

	def due_post(self, channels: list[str], **values):
		"""A scheduled post whose time has passed. The clock is set behind the record's back,
		because scheduling into the past is exactly what the API refuses."""
		post = self.make_post(channels, **values)
		post.db_set({"status": "Scheduled", "scheduled_at": add_to_date(now_datetime(), minutes=-1)})
		return post

	def test_a_draft_takes_a_time_and_goes_on_the_clock(self):
		post = self.make_post([self.make_channel()])
		at = self.in_an_hour()

		self.assertEqual(schedule_post(post.name, at), "Scheduled")

		post.reload()
		self.assertEqual(post.status, "Scheduled")
		self.assertEqual(post.scheduled_at, get_datetime(at))

	def test_a_time_that_has_gone_is_refused(self):
		post = self.make_post([self.make_channel()])
		past = add_to_date(now_datetime(), hours=-1).strftime("%Y-%m-%d %H:%M:%S")

		self.assertRaises(frappe.ValidationError, schedule_post, post.name, past)

	def test_a_post_the_platform_would_refuse_is_never_scheduled(self):
		post = self.make_post([self.make_channel()], parts=[{"text": "A" * 3001}])

		self.assertRaises(frappe.ValidationError, schedule_post, post.name, self.in_an_hour())
		self.assertEqual(frappe.db.get_value("Social Post", post.name, "status"), "Draft")

	def test_a_scheduled_post_can_still_be_written(self):
		post = self.make_post([self.make_channel()])
		schedule_post(post.name, self.in_an_hour())

		post.reload()
		post.parts[0].text = "A second thought"
		post.save()

		self.assertEqual(post.status, "Scheduled")

	def test_only_a_post_that_has_not_gone_out_can_move(self):
		channel = self.make_channel()
		draft = self.make_post([channel])
		published = self.make_post([channel], status="Published")

		self.assertEqual(reschedule_post(draft.name, self.in_an_hour()), "Draft")
		self.assertRaises(frappe.ValidationError, reschedule_post, published.name, self.in_an_hour())

	def test_unscheduling_gives_the_draft_back_and_keeps_the_slot(self):
		post = self.make_post([self.make_channel()])
		at = self.in_an_hour()
		schedule_post(post.name, at)

		self.assertEqual(unschedule_post(post.name), "Draft")

		post.reload()
		self.assertEqual(post.scheduled_at, get_datetime(at))
		self.assertRaises(frappe.ValidationError, unschedule_post, post.name)

	def test_the_minute_starts_a_due_post_once(self):
		post = self.due_post([self.make_channel()])

		with patch("frappe.enqueue") as enqueue:
			publish_due_posts()
			publish_due_posts()

		post.reload()
		self.assertEqual(post.status, "Publishing")
		self.assertEqual(post.targets[0].status, "Pending")
		self.assertEqual(enqueue.call_count, 1)

	def test_a_post_that_cannot_go_out_any_more_says_so_instead_of_trying_again(self):
		channel = self.make_channel()
		post = self.due_post([channel])
		frappe.db.set_value("Social Channel", channel, "status", "Expired")

		with patch("frappe.enqueue") as enqueue:
			publish_due_posts()

		post.reload()
		self.assertEqual(post.status, "Failed")
		self.assertEqual(enqueue.call_count, 0)
		self.assertIn("Expired", post.targets[0].error)
		self.assertEqual(post.targets[0].status, "Failed")

	def test_a_post_whose_worker_died_is_queued_again(self):
		post = self.make_post([self.make_channel()], status="Publishing")
		frappe.db.set_value(
			"Social Post",
			post.name,
			"modified",
			add_to_date(now_datetime(), seconds=-JOB_TIMEOUT - 60),
			update_modified=False,
		)

		with patch("bwh_os.social.publisher.has_job", return_value=False), patch("frappe.enqueue") as enqueue:
			resume_stuck_posts()

		self.assertEqual(enqueue.call_count, 1)

	def test_a_post_still_within_its_time_is_left_to_work(self):
		self.make_post([self.make_channel()], status="Publishing")

		with patch("bwh_os.social.publisher.has_job", return_value=False), patch("frappe.enqueue") as enqueue:
			resume_stuck_posts()

		self.assertEqual(enqueue.call_count, 0)


def release_parts(account, parts, settings, released, on_release):
	"""A LinkedIn that always takes the post. Part 1 gets a share urn, the rest comment ids."""
	done = {row["part_no"] for row in released}
	for part_no, _part in enumerate(parts, start=1):
		if part_no in done:
			continue
		if part_no == 1:
			urn = "urn:li:share:1"
			on_release(Release(part_no=1, id=urn, url=f"https://www.linkedin.com/feed/update/{urn}"))
		else:
			on_release(Release(part_no=part_no, id=f"urn:li:comment:{part_no}"))
