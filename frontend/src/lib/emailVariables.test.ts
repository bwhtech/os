/**
 * Keep the keys in step with `bwh_os/mailing/email_variables.py`. Run with `yarn test`.
 */

import assert from 'node:assert/strict'
import test from 'node:test'
import { NEWSLETTER_VARIABLES, fillSamples, withLeadMagnet } from './emailVariables.ts'

test('with no lead magnet, the newsletter set is unchanged', () => {
	assert.deepEqual(withLeadMagnet(NEWSLETTER_VARIABLES, null), NEWSLETTER_VARIABLES)
	assert.deepEqual(withLeadMagnet(NEWSLETTER_VARIABLES, undefined), NEWSLETTER_VARIABLES)
	assert.deepEqual(withLeadMagnet(NEWSLETTER_VARIABLES, ''), NEWSLETTER_VARIABLES)
})

test('a lead magnet adds the download link and its title', () => {
	const widened = withLeadMagnet(NEWSLETTER_VARIABLES, 'some-magnet')

	assert.deepEqual(
		widened.map((variable) => variable.key),
		['first_name', 'email', 'download_url', 'lead_magnet'],
	)
})

test('fillSamples leaves the magnet variables alone when they are not offered', () => {
	const html = '<a href="{{ download_url }}">{{ lead_magnet }}</a>'

	assert.equal(fillSamples(html, NEWSLETTER_VARIABLES), html)
})

test('fillSamples fills the magnet variables once a magnet is picked', () => {
	const html = '<a href="{{ download_url }}">{{ lead_magnet }}</a>'
	const variables = withLeadMagnet(NEWSLETTER_VARIABLES, 'some-magnet')

	const filled = fillSamples(html, variables)

	assert.equal(filled, '<a href="https://bwh.tech/download">The Missing Frappe Manual</a>')
})
