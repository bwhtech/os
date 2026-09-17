"""How X measures a post. See specs/04-social-posts.md.

X counts weight, not characters: the alphabets most posts are written in cost one each,
and everything else costs two, so 280 is 280 latin letters or 140 emoji. A link costs a
flat 23 whatever its length, because X rewrites every link to a t.co of that size.

`frontend/src/lib/xText.ts` is the same count in the browser, so the composer and the
server never disagree about whether a post fits. The fixtures in
`frontend/src/lib/xText.fixtures.json` are what keeps the two honest.
"""

import re
import unicodedata

# The code point ranges that cost one. Latin, Cyrillic, Greek, Hebrew, Arabic and the
# punctuation around them; CJK, emoji and the rest cost two. twitter-text calls this
# configuration v3, and X has shipped it since 2018.
LIGHT_RANGES = ((0, 4351), (8192, 8205), (8208, 8223), (8242, 8247))
LIGHT_WEIGHT = 1
HEAVY_WEIGHT = 2

# Every link is rewritten to a t.co of this length, however long it was written.
URL_WEIGHT = 23

URL = re.compile(r"\b(?:https?://|www\.)[^\s<>\"]+", re.IGNORECASE)
# A link at the end of a sentence carries the full stop. The link ends before it.
TRAILING = re.compile(r"[.,!?;:'\"\)\]}]+$")


def weighted_length(text: str) -> int:
	"""What X counts this text as, links included."""
	text = unicodedata.normalize("NFC", text or "")
	total = 0
	at = 0
	for match in URL.finditer(text):
		url = TRAILING.sub("", match.group())
		total += plain_length(text[at : match.start()]) + URL_WEIGHT
		# Whatever the link left behind is ordinary text again.
		at = match.start() + len(url)
	return total + plain_length(text[at:])


def plain_length(text: str) -> int:
	"""The weight of a stretch with no links in it.

	Each code point is weighed on its own, so an emoji written as a sequence of them costs
	more here than on X. The composer asks for a shorter post than it had to, never a
	longer one, which is the side to be wrong on.
	"""
	return sum(LIGHT_WEIGHT if is_light(character) else HEAVY_WEIGHT for character in text)


def is_light(character: str) -> bool:
	point = ord(character)
	return any(first <= point <= last for first, last in LIGHT_RANGES)
