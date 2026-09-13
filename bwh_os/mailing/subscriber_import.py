import csv
import io
import re
from dataclasses import asdict, dataclass, field

import frappe
from frappe import _
from frappe.utils import validate_email_address

from bwh_os.mailing.doctype.subscriber.subscriber import clean_tag_names, normalize_email

# The CSV text travels to the worker inside the job, so keep it to a sane size.
MAX_ROWS = 50000
PREVIEW_ROWS = 10
# Rows between a commit and a progress event
BATCH_SIZE = 100
PROGRESS_EVENT = "subscriber_import_progress"

ACTIONS = ("New", "Existing", "Invalid", "Duplicate", "Failed")

TARGET_FIELDS = ("email", "first_name", "full_name", "tags")

# Normalized header names (lowercase, letters and digits only) that map to a field on their own.
HEADER_ALIASES = {
	"email": ("email", "emailaddress", "mail", "emailid", "useremail"),
	"first_name": ("firstname", "givenname", "fname"),
	"full_name": ("fullname", "name", "displayname"),
	"tags": ("tags", "tag", "labels", "segments"),
}


@dataclass
class ImportRow:
	email: str
	first_name: str | None
	tags: list[str] = field(default_factory=list)
	# New, Existing, Invalid, Duplicate (an earlier row has the same email), or Failed (on import)
	action: str = "New"


class SubscriberImport:
	"""Import subscribers from CSV text. New emails become Active. Known emails only get the tags."""

	def __init__(self, content: str, mapping: dict | None = None, tags: list[str] | None = None):
		self.content = content
		self.headers, self.records = parse_csv(content)
		self.mapping = self.clean_mapping(mapping) if mapping else self.suggest_mapping()
		self.tags = clean_tag_names(tags or [])

	def preview(self) -> dict:
		rows = self.plan()
		return {
			"columns": [{"name": h, "samples": self.samples(i)} for i, h in enumerate(self.headers)],
			"mapping": self.mapping,
			"total": len(rows),
			"counts": count_actions(rows),
			"rows": [asdict(row) for row in rows[:PREVIEW_ROWS]],
		}

	def enqueue(self) -> dict:
		"""Check the file and mapping now, so the user sees mistakes at once, then import in a worker."""
		self.check_mapping()
		import_id = frappe.generate_hash(length=12)
		frappe.enqueue(
			run_import_job,
			queue="long",
			timeout=60 * 60,
			enqueue_after_commit=True,
			import_id=import_id,
			content=self.content,
			mapping=self.mapping,
			tags=self.tags,
		)
		return {"import_id": import_id, "total": len(self.records)}

	def run(self, progress: "ImportProgress") -> dict:
		"""Commit every batch, so a failed row or a crash keeps the rows before it."""
		self.check_mapping()
		rows = self.plan()
		progress.start(len(rows))
		for index, row in enumerate(rows, start=1):
			if row.action in ("New", "Existing"):
				self.apply(row, progress)
			progress.count(row.action)
			if index % BATCH_SIZE == 0:
				frappe.db.commit()
				progress.publish("Running", done=index)
		frappe.db.commit()
		progress.publish("Done", done=len(rows))
		return progress.counts

	def apply(self, row: ImportRow, progress: "ImportProgress"):
		# One bad row must not undo the other rows in its batch.
		frappe.db.savepoint("import_row")
		try:
			if row.action == "New":
				self.insert(row)
			else:
				self.add_tags(row)
		except Exception as e:
			frappe.db.rollback(save_point="import_row")
			row.action = "Failed"
			progress.fail(row, e)
		else:
			frappe.db.release_savepoint("import_row")

	def check_mapping(self):
		if not self.mapping.get("email"):
			frappe.throw(_("Pick the column that has the email address"))

	def plan(self) -> list[ImportRow]:
		known = set(frappe.get_all("Subscriber", pluck="name"))
		seen = set()
		rows = []
		for record in self.records:
			row = self.to_row(record)
			if not validate_email_address(row.email):
				row.action = "Invalid"
			elif row.email in seen:
				row.action = "Duplicate"
			elif row.email in known:
				row.action = "Existing"
			seen.add(row.email)
			rows.append(row)
		return rows

	def suggest_mapping(self) -> dict:
		mapping = dict.fromkeys(TARGET_FIELDS)
		for header in self.headers:
			key = normalize_header(header)
			for target, aliases in HEADER_ALIASES.items():
				if not mapping[target] and key in aliases:
					mapping[target] = header
		return mapping

	def clean_mapping(self, mapping: dict) -> dict:
		return {target: mapping.get(target) if mapping.get(target) in self.headers else None for target in TARGET_FIELDS}

	def to_row(self, record: list[str]) -> ImportRow:
		first_name = self.value(record, "first_name")
		if not first_name and (full_name := self.value(record, "full_name")):
			first_name = full_name.split()[0]
		return ImportRow(
			email=normalize_email(self.value(record, "email")),
			first_name=first_name or None,
			tags=list(dict.fromkeys(self.tags + clean_tag_names(split_tags(self.value(record, "tags"))))),
		)

	def insert(self, row: ImportRow):
		subscriber = frappe.new_doc("Subscriber")
		subscriber.email = row.email
		subscriber.first_name = row.first_name
		subscriber.status = "Active"
		subscriber.add_tags(row.tags)
		subscriber.insert()

	def add_tags(self, row: ImportRow):
		subscriber = frappe.get_doc("Subscriber", row.email)
		before = len(subscriber.tags)
		subscriber.add_tags(row.tags)
		if len(subscriber.tags) != before:
			subscriber.save()

	def value(self, record: list[str], target: str) -> str:
		header = self.mapping.get(target)
		if not header:
			return ""
		index = self.headers.index(header)
		return record[index].strip() if index < len(record) else ""

	def samples(self, index: int) -> list[str]:
		values = (record[index].strip() for record in self.records if index < len(record))
		return [value for value in values if value][:3]


class ImportProgress:
	"""Counts rows as they import and tells the user's open tabs over socket.io."""

	MAX_ERRORS = 20

	def __init__(self, import_id: str, user: str):
		self.import_id = import_id
		self.user = user
		self.total = 0
		self.counts = dict.fromkeys(ACTIONS, 0)
		self.errors: list[dict] = []

	def start(self, total: int):
		self.total = total
		self.publish("Running", done=0)

	def count(self, action: str):
		self.counts[action] += 1

	def fail(self, row: ImportRow, error: Exception):
		if len(self.errors) < self.MAX_ERRORS:
			self.errors.append({"email": row.email, "error": frappe.utils.strip_html(str(error))})

	def publish(self, status: str, done: int, message: str | None = None):
		frappe.publish_realtime(
			PROGRESS_EVENT,
			{
				"import_id": self.import_id,
				# Running, Done, or Failed
				"status": status,
				"done": done,
				"total": self.total,
				"counts": self.counts,
				"errors": self.errors,
				"message": message,
			},
			user=self.user,
		)


def run_import_job(import_id: str, content: str, mapping: dict, tags: list[str]):
	progress = ImportProgress(import_id, frappe.session.user)
	try:
		SubscriberImport(content, mapping, tags).run(progress)
	except Exception as e:
		frappe.db.rollback()
		progress.publish("Failed", done=sum(progress.counts.values()), message=str(e))
		raise


def parse_csv(content: str) -> tuple[list[str], list[list[str]]]:
	content = (content or "").lstrip("\ufeff")
	try:
		dialect = csv.Sniffer().sniff(content[:4096], delimiters=",;\t")
	except csv.Error:
		dialect = csv.excel

	rows = [row for row in csv.reader(io.StringIO(content), dialect) if any(cell.strip() for cell in row)]
	if not rows:
		frappe.throw(_("The file is empty"))

	headers = [header.strip() or _("Column {0}").format(i + 1) for i, header in enumerate(rows[0])]
	if len(set(headers)) != len(headers):
		frappe.throw(_("Each column in the header row needs a different name"))
	if len(rows) - 1 > MAX_ROWS:
		frappe.throw(_("The file has more than {0} rows. Split it into smaller files.").format(MAX_ROWS))
	return headers, rows[1:]


def count_actions(rows: list[ImportRow]) -> dict[str, int]:
	counts = dict.fromkeys(ACTIONS[:-1], 0)
	for row in rows:
		counts[row.action] += 1
	return counts


def normalize_header(header: str) -> str:
	return re.sub(r"[^a-z0-9]", "", header.lower())


def split_tags(value: str) -> list[str]:
	return re.split(r"[,;|]", value) if value else []
