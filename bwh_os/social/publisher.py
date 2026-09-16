"""Putting a post on the platforms. See specs/04-social-posts.md.

The hard part is not the call, it is the call whose answer never came back. No platform
here takes an idempotency key, so a job that dies between the request and the response
leaves no way to ask "did that go out?". The arm flag answers it: a target writes down
that it is about to call, commits, and only then calls. A second run that finds the flag
set and nothing released stops and says Unconfirmed, because posting twice is worse than
posting late. Postiz solves the same problem the same way in its LinkedIn provider.

Each part is written down as it lands, so a thread that broke in the middle carries on
from the part after the last one that made it.
"""

import frappe
from frappe import _
from frappe.utils import now_datetime
from frappe.utils.background_jobs import is_job_enqueued

from bwh_os.social.providers import BadRequest, ReconnectRequired, Release, get_provider
from bwh_os.social.providers.base import Account
from bwh_os.social.tokens import get_token

SAVEPOINT = "social_target"
# A video upload is slow, so the job gets half an hour before the queue gives up on it.
JOB_TIMEOUT = 30 * 60


class Publisher:
	"""One post, every target. Each target stands alone: one failing never stops the rest."""

	def __init__(self, post):
		self.post = post

	@property
	def job_id(self) -> str:
		return f"social_post::{self.post.name}"

	def check(self):
		"""Raise if this post cannot go out now. Schedule runs the same check up front."""
		self.post.check()

	def start(self):
		"""Lock the content, set every target waiting, and hand the post to a worker."""
		if self.post.status not in ("Draft", "Scheduled"):
			frappe.throw(_("This post is already {0}").format(_(self.post.status).lower()))
		self.check()

		self.post.status = "Publishing"
		for target in self.post.targets:
			target.status = "Pending"
			target.error = None
			target.error_kind = None
		self.post.save()
		self.enqueue()

	def enqueue(self):
		frappe.enqueue(
			run_publish_job,
			queue="long",
			timeout=JOB_TIMEOUT,
			enqueue_after_commit=True,
			job_id=self.job_id,
			deduplicate=True,
			post=self.post.name,
		)

	def run(self):
		"""The job. A target that throws is caught and written down, and the next one goes."""
		for target in self.post.targets:
			if target.status in ("Published", "Failed"):
				continue
			self.commit()
			try:
				self.publish_target(target)
			except Exception as error:
				frappe.db.rollback(save_point=SAVEPOINT)
				self.fail(target, error)
			self.commit()
		self.finish()

	def publish_target(self, target):
		"""One channel. Arms first, then calls, then keeps what came back."""
		if self.is_unconfirmed(target):
			self.set_target(
				target,
				status="Failed",
				error_kind="Unconfirmed",
				error=_("A publish started and never finished. Check {0} before trying again.").format(
					target.provider
				),
			)
			return

		channel = frappe.get_doc("Social Channel", target.channel)
		provider = get_provider(target.provider)
		self.set_target(target, status="Publishing", publish_attempted_at=now_datetime())
		# The flag has to be on the record before the call, or a crash loses the fact of it.
		self.commit()

		account = Account(
			token_cache=get_token(channel), account_id=channel.account_id, post_name=str(self.post.name)
		)
		provider.post(
			account,
			self.post.parts_for(target),
			self.post.settings_of(target),
			self.released(target),
			lambda release: self.keep(target, release),
		)
		first = next((row for row in self.released(target) if row["part_no"] == 1), {})
		self.set_target(
			target,
			status="Published",
			published_at=now_datetime(),
			release_id=first.get("id"),
			release_url=first.get("url"),
			error=None,
			error_kind=None,
		)

	def is_unconfirmed(self, target) -> bool:
		"""A target that armed and released nothing may already be on the platform."""
		return bool(target.publish_attempted_at) and not self.released(target)

	def keep(self, target, release: Release):
		"""Write a part down the moment it lands, so nothing posts twice."""
		released = [*self.released(target), release.as_dict()]
		self.set_target(target, released_parts=frappe.as_json(released))
		self.commit()

	def released(self, target) -> list[dict]:
		return frappe.parse_json(target.released_parts) or []

	def fail(self, target, error: Exception):
		"""Name the failure, so the UI knows whether to offer Retry or Reconnect."""
		if isinstance(error, ReconnectRequired):
			kind = "Reconnect"
		elif isinstance(error, BadRequest):
			kind = "Bad Request"
		else:
			kind = "Retryable"
			frappe.log_error(
				title=_("Social post failed"),
				reference_doctype=self.post.doctype,
				reference_name=self.post.name,
			)
		self.set_target(target, status="Failed", error_kind=kind, error=str(error)[:500])

	def finish(self):
		"""The post says what came of it as a whole, and the list picks it up live."""
		statuses = [target.status for target in self.post.targets]
		published = statuses.count("Published")
		if published == len(statuses):
			status = "Published"
		elif published:
			status = "Partial"
		else:
			status = "Failed"

		self.post.db_set(
			{
				"status": status,
				"published_at": now_datetime() if published else None,
			},
			notify=True,
		)
		self.post.add_comment("Comment", self.summary(status, published, len(statuses)))
		self.commit()

	def summary(self, status: str, published: int, total: int) -> str:
		if status == "Published":
			return _("Published to {0} channels").format(total) if total > 1 else _("Published")
		if status == "Partial":
			return _("Published to {0} of {1} channels").format(published, total)
		return _("Nothing went out")

	def commit(self):
		"""Keep what is done and open a new savepoint. A commit drops the old one, so the
		next failure would have nothing to roll back to."""
		frappe.db.commit()
		frappe.db.savepoint(SAVEPOINT)

	def set_target(self, target, **values):
		"""Write on the child row. `db_set` on a child updates the row in place."""
		target.db_set(values, commit=False)


def run_publish_job(post: str):
	"""The background job. Loads the post fresh, because the queue holds only its name."""
	Publisher(frappe.get_doc("Social Post", post)).run()


def has_job(post: str) -> bool:
	return is_job_enqueued(f"social_post::{post}")
