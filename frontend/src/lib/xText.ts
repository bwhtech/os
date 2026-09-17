/**
 * How X measures a post, in the browser. The mirror of `bwh_os/social/x_text.py`: read
 * that one for why the weights are what they are, and change the two together.
 *
 * The server owns the rules and answers the counter, but it answers a beat behind the
 * typing. The preview marks what falls past 280 on every keystroke, so it counts here.
 */

const LIGHT_RANGES: [number, number][] = [
	[0, 4351],
	[8192, 8205],
	[8208, 8223],
	[8242, 8247],
]
const LIGHT_WEIGHT = 1
const HEAVY_WEIGHT = 2

/** Every link is rewritten to a t.co of this length, however long it was written. */
const URL_WEIGHT = 23

const URL = /\b(?:https?:\/\/|www\.)[^\s<>"]+/gi
/** A link at the end of a sentence carries the full stop. The link ends before it. */
const TRAILING = /[.,!?;:'")\]}]+$/

/** What X counts this text as, links included. */
export function weightedLength(text: string): number {
	return weigh(text).length
}

/**
 * Where X would cut this text. `kept` is what fits in `limit`, `over` is what does not,
 * so the preview can show the rest in red instead of hiding it.
 */
export function splitAtLimit(text: string, limit: number): { kept: string; over: string } {
	const { length, weights } = weigh(text)
	if (!limit || length <= limit) return { kept: text, over: '' }

	let total = 0
	for (const [index, weight] of weights.entries()) {
		total += weight
		// A link is one unit: the cut goes before it rather than through it.
		if (total > limit) return { kept: text.slice(0, index), over: text.slice(index) }
	}
	return { kept: text, over: '' }
}

/**
 * The weight of the text, and the weight each character of it added. The two are counted
 * in one pass: `splitAtLimit` needs the running total, and the rest needs the sum.
 */
function weigh(text: string): { length: number; weights: number[] } {
	const normalized = (text ?? '').normalize('NFC')
	const weights = new Array(normalized.length).fill(0)

	let at = 0
	for (const match of normalized.matchAll(URL)) {
		const url = match[0].replace(TRAILING, '')
		weighPlain(normalized.slice(at, match.index), at, weights)
		weights[match.index] = URL_WEIGHT
		// Whatever the link left behind is ordinary text again.
		at = match.index + url.length
	}
	weighPlain(normalized.slice(at), at, weights)

	return { length: weights.reduce((total, weight) => total + weight, 0), weights }
}

/** A stretch with no links in it, weighed by code point and written down where it sits. */
function weighPlain(text: string, offset: number, weights: number[]): void {
	let at = offset
	for (const character of text) {
		weights[at] = isLight(character.codePointAt(0) ?? 0) ? LIGHT_WEIGHT : HEAVY_WEIGHT
		at += character.length
	}
}

function isLight(point: number): boolean {
	return LIGHT_RANGES.some(([first, last]) => point >= first && point <= last)
}
