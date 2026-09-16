"""Social channels and posts for the OS. See specs/04-social-posts.md."""

import json

import frappe
from frappe import _
from frappe.query_builder import Order
from frappe.query_builder.functions import Coalesce
from frappe.utils import date_diff, now_datetime

from bwh_os.social.oauth import LINKEDIN_SUCCESS_URI
from bwh_os.social.oauth_apps import PROVIDERS, get_app, redirect_uri
from bwh_os.social.publisher import Publisher
from bwh_os.social.validation import PostValidator

CHANNEL_FIELDS = [
	"name",
	"provider",
	"display_name",
	"handle",
	"avatar_url",
	"profile_url",
	"status",
	"connected_on",
	"expires_on",
	"last_error",
]


@frappe.whitelist(methods=["GET"])
def get_channels() -> list[dict]:
	"""Every channel with the days left on its token, for the Settings panel."""
	frappe.only_for("System Manager")
	channels = frappe.get_all("Social Channel", fields=CHANNEL_FIELDS, order_by="provider asc")
	today = now_datetime()
	for channel in channels:
		channel["days_left"] = date_diff(channel.expires_on, today) if channel.expires_on else None
	return channels


@frappe.whitelist(methods=["GET"])
def get_provider_apps() -> list[dict]:
	"""The OAuth app of each platform, with the URI to register and whether it can connect yet."""
	frappe.only_for("System Manager")
	apps = []
	for provider in PROVIDERS:
		app = get_app(provider)
		apps.append(
			{
				"provider": provider,
				"app": app.name,
				"redirect_uri": redirect_uri(provider, app),
				"scopes": [row.scope for row in app.scopes],
				"client_id": app.client_id,
				"has_credentials": bool(app.client_id and app.get_password("client_secret", False)),
			}
		)
	return apps


@frappe.whitelist(methods=["POST"])
def set_credentials(provider: str, client_id: str, client_secret: str = "") -> None:
	"""Save the client id and secret of a platform. An empty secret keeps the saved one."""
	frappe.only_for("System Manager")
	app = get_app(provider)
	app.client_id = client_id.strip()
	if client_secret:
		app.client_secret = client_secret
	app.save(ignore_permissions=True)


@frappe.whitelist(methods=["POST"])
def connect_channel(provider: str) -> str:
	"""Start the connect. Returns the URL of the platform to send the browser to."""
	frappe.only_for("System Manager")
	app = get_app(provider)
	if not (app.client_id and app.get_password("client_secret", False)):
		frappe.throw(_("Add the client id and secret of {0} first").format(provider))
	if provider != "LinkedIn":
		frappe.throw(_("The OS cannot connect {0} yet").format(provider))

	return app.initiate_web_application_flow(user=frappe.session.user, success_uri=LINKEDIN_SUCCESS_URI)


@frappe.whitelist(methods=["POST"])
def disconnect_channel(channel: str) -> None:
	"""Drop the token of a channel. The channel stays, so its posts keep their history."""
	frappe.only_for("System Manager")
	doc = frappe.get_doc("Social Channel", channel)
	frappe.delete_doc("Token Cache", f"{doc.connected_app}-{doc.user}", force=True, ignore_missing=True)
	doc.db_set(
		{"status": "Disconnected", "token_cache": None, "expires_on": None, "last_error": None},
		notify=True,
	)


@frappe.whitelist(methods=["POST"])
def validate_post(post: str | int | dict) -> list[dict]:
	"""What each target would say about this content, without saving anything.

	`post` is the name of a saved post, or the document the composer holds right now.
	The composer sends the document, so the counter answers while you type.
	"""
	frappe.only_for("System Manager")
	return PostValidator(load_post(post)).results()


def load_post(post: str | int | dict) -> "frappe.Document":
	"""A `Social Post` from a name, or a document made from what the browser sent."""
	if isinstance(post, str) and post.strip().startswith("{"):
		post = json.loads(post)
	if isinstance(post, dict):
		post = {**post, "doctype": "Social Post"}
		doc = frappe.get_doc(post)
		# The rows come from the browser, so the numbers and the orphans need a pass first.
		PostValidator(doc).structure()
		return doc
	return frappe.get_doc("Social Post", post)


@frappe.whitelist(methods=["POST"])
def publish_post(post: str | int) -> str:
	"""Put the post out now. Returns the status the post is in once the job is queued."""
	frappe.only_for("System Manager")
	doc = frappe.get_doc("Social Post", post)
	Publisher(doc).start()
	return doc.status


# What each tab of the list page holds. Everything that has not gone out yet is Upcoming,
# including the posts that tried and failed, because those are the ones needing a hand.
VIEWS = {
	"upcoming": ["Draft", "Scheduled", "Publishing", "Partial", "Failed"],
	"published": ["Published"],
	"all": [],
}

POST_FIELDS = ["name", "title", "status", "scheduled_at", "published_at", "video", "modified"]


@frappe.whitelist(methods=["GET"])
def get_posts(view: str = "upcoming", limit: int = 100) -> list[dict]:
	"""The posts of one tab, each with the channels it goes to.

	The channels come from a child table, which no list call reads, so they arrive in a
	second query and go back onto their post here.
	"""
	frappe.only_for("System Manager")
	statuses = VIEWS.get(view, [])
	post = frappe.qb.DocType("Social Post")
	query = (
		frappe.qb.from_(post)
		.select(*[post[field] for field in POST_FIELDS])
		# A time beats a save: the next post out is the one to look at first. `get_all` takes
		# no expression in `order_by`, so the query is built here.
		.orderby(Coalesce(post.scheduled_at, post.published_at, post.modified), order=Order.desc)
		.limit(frappe.utils.cint(limit))
	)
	if statuses:
		query = query.where(post.status.isin(statuses))
	posts = query.run(as_dict=True)
	targets = targets_of([post.name for post in posts])
	for post in posts:
		post["targets"] = targets.get(str(post.name), [])
	return posts


def targets_of(posts: list) -> dict[str, list[dict]]:
	"""The targets of each post, with the look of the channel, keyed by the post."""
	if not posts:
		return {}

	target = frappe.qb.DocType("Social Post Target")
	rows = (
		frappe.qb.from_(target)
		.select(target.parent, target.channel, target.provider, target.status, target.release_url)
		.where(target.parenttype == "Social Post")
		.where(target.parent.isin([str(post) for post in posts]))
		.orderby(target.parent)
		.orderby(target.idx)
		.run(as_dict=True)
	)
	channels = {
		channel.name: channel
		for channel in frappe.get_all(
			"Social Channel", fields=["name", "display_name", "handle", "avatar_url", "status"]
		)
	}
	by_post: dict[str, list[dict]] = {}
	for row in rows:
		channel = channels.get(row.channel, {})
		row["display_name"] = channel.get("display_name")
		row["avatar_url"] = channel.get("avatar_url")
		row["channel_status"] = channel.get("status")
		by_post.setdefault(row.parent, []).append(row)
	return by_post
