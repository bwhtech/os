/**
 * The browser count against the fixtures `bwh_os/social/test_social.py` reads too, so the
 * composer and the server always say the same number. Run it with `yarn test`.
 */

import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import assert from 'node:assert/strict'
import test from 'node:test'
import { splitAtLimit, weightedLength } from './xText.ts'

interface Fixture {
	text: string
	length: number
	why: string
}

const fixtures: Fixture[] = JSON.parse(
	readFileSync(fileURLToPath(new URL('./xText.fixtures.json', import.meta.url)), 'utf8'),
)

test('the weighted count matches the fixtures', () => {
	for (const fixture of fixtures) {
		assert.equal(weightedLength(fixture.text), fixture.length, fixture.why)
	}
})

test('a text within the limit is kept whole', () => {
	assert.deepEqual(splitAtLimit('hello', 280), { kept: 'hello', over: '' })
})

test('what falls past the limit is handed back on its own', () => {
	assert.deepEqual(splitAtLimit('abcdef', 3), { kept: 'abc', over: 'def' })
})

test('a heavy character counts double against the limit', () => {
	assert.deepEqual(splitAtLimit('日本語', 4), { kept: '日本', over: '語' })
})

test('the cut goes before a link, never through it', () => {
	assert.deepEqual(splitAtLimit('ab https://example.com', 10), {
		kept: 'ab ',
		over: 'https://example.com',
	})
})
