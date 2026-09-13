import csv
import io
import re
from dataclasses import asdict, dataclass, field

import frappe
from frappe import _
from frappe.utils import validate_email_address

from bwh_os.mailing.doctype.subscriber.subscriber import clean_tag_names, normalize_email

# The import runs in the web request, so a big file must not hit the request timeout.
MAX_ROWS = 5000
PREVIEW_ROWS = 10

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
	# New, Existing, Invalid, or Duplicate (an earlier row has the same email)
	action: str = "New"


class SubscriberImport:
	"""Import subscribers from CSV text. New emails become Active. Known emails only get the tags."""

	def __init__(self, content: str, mapping: dict | None = None, tags: list[str] | None = None):
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

	def run(self) -> dict:
		if not self.mapping.get("email"):
			frappe.throw(_("Pick the column that has the email address"))

		rows = self.plan()
		for row in rows:
			if row.action == "New":
				self.insert(row)
			elif row.action == "Existing":
				self.add_tags(row)
		return count_actions(rows)

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
	counts = dict.fromkeys(("New", "Existing", "Invalid", "Duplicate"), 0)
	for row in rows:
		counts[row.action] += 1
	return counts


def normalize_header(header: str) -> str:
	return re.sub(r"[^a-z0-9]", "", header.lower())


def split_tags(value: str) -> list[str]:
	return re.split(r"[,;|]", value) if value else []
