"""Variables like {{ first_name }} in list email subjects and content.

The OS editor puts them in as chips. Keep the keys and fallbacks in step with
frontend/src/lib/emailVariables.ts.
"""

import re
from collections.abc import Iterable
from html import escape

import frappe
from frappe import _

# Used when the value is empty
FALLBACKS = {"first_name": "there"}

SUBSCRIBER = ("first_name", "email")
NEWSLETTER = SUBSCRIBER
WELCOME = SUBSCRIBER  # the form's greeting. The file has its own email; see LEAD_MAGNET.
CONFIRM = (*SUBSCRIBER, "confirm_url")
MAGNET = ("download_url", "lead_magnet")
LEAD_MAGNET = (*SUBSCRIBER, *MAGNET)

# Also matches a link, where the editor URL-encodes the braces and spaces.
VARIABLE = re.compile(r"(?:\{\{|%7B%7B)(?:\s|%20)*([a-z_]+)(?:\s|%20)*(?:\}\}|%7D%7D)", re.IGNORECASE)
# Anything in double braces, to catch old Jinja such as {{ first_name or "there" }}.
BRACES = re.compile(r"\{\{(.*?)\}\}")


def fill(text: str, values: dict[str, str | None], html: bool = True) -> str:
	"""Put the values in the text. A variable with no value gets its fallback."""

	def value_for(match: re.Match) -> str:
		key = match.group(1).lower()
		if key not in values:
			return match.group(0)
		value = values[key] or FALLBACKS.get(key, "")
		return escape(value) if html else value

	return VARIABLE.sub(value_for, text or "")


def with_lead_magnet(allowed: Iterable[str], lead_magnet: str | None) -> tuple[str, ...]:
	"""The magnet variables are fillable only when the email carries a magnet."""
	return (*allowed, *MAGNET) if lead_magnet else tuple(allowed)


def fallback_values(allowed: Iterable[str]) -> dict[str, str | None]:
	"""Every variable empty, for a test send or the web archive."""
	return dict.fromkeys(allowed)


def subscriber_values(subscriber) -> dict[str, str | None]:
	return {"first_name": subscriber.first_name, "email": subscriber.email}


def check(text: str, allowed: Iterable[str], label: str, required: Iterable[str] = ()):
	"""Raise for a variable that this email cannot fill, or a required one that is missing."""
	allowed = set(allowed)
	used = {match.group(1).lower() for match in VARIABLE.finditer(text or "")}
	unknown = sorted(used - allowed)
	unknown += [
		f"{{{{{inner}}}}}"
		for inner in BRACES.findall(text or "")
		if not VARIABLE.fullmatch(f"{{{{{inner}}}}}")
	]
	if unknown:
		frappe.throw(
			_("{0} has a variable that it cannot fill: {1}. Use {2}.").format(
				label, ", ".join(unknown), ", ".join(f"{{{{ {key} }}}}" for key in sorted(allowed))
			)
		)
	for key in required:
		if key not in used:
			frappe.throw(_("{0} needs {1}. Add it as a button link.").format(label, f"{{{{ {key} }}}}"))
