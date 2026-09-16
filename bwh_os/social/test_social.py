import frappe
from frappe.tests import IntegrationTestCase

from bwh_os.social.api import get_channels, get_provider_apps, set_credentials
from bwh_os.social.oauth_apps import PROVIDERS, ensure_connected_apps, get_app


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
