import type { JSONContent } from '@tiptap/core'
import type { EmailDocument } from '@/types'

// The Frappe UI theme has no paragraph margin. An empty paragraph makes the space.
const BLANK: JSONContent = { type: 'paragraph' }

/** First drafts for list emails that have no content yet. They show how variables work. */
export function confirmStarter(): EmailDocument {
	return email([
		paragraph([text('Hi '), variable('first_name', 'First name'), text(',')]),
		BLANK,
		paragraph([text('Click the button below to confirm your subscription.')]),
		BLANK,
		button('Confirm subscription', '{{ confirm_url }}'),
	])
}

export function welcomeStarter(withLeadMagnet: boolean): EmailDocument {
	const intro = paragraph([text('Hi '), variable('first_name', 'First name'), text(', thanks for joining.')])
	if (!withLeadMagnet) return email([intro])
	return email([
		intro,
		BLANK,
		paragraph([text('Here is your copy of '), variable('lead_magnet', 'Lead magnet'), text('.')]),
		BLANK,
		button('Download', '{{ download_url }}'),
	])
}

/** The button a welcome email needs when the form gives a lead magnet away. */
export function downloadButton(): JSONContent {
	return button('Download', '{{ download_url }}')
}

export function parseEmailDocument(value: string | EmailDocument | null): EmailDocument | null {
	if (!value) return null
	return typeof value === 'string' ? JSON.parse(value) : value
}

function email(content: JSONContent[]): EmailDocument {
	return { type: 'doc', content: [{ type: 'container', content }] }
}

function paragraph(content: JSONContent[]): JSONContent {
	return { type: 'paragraph', content }
}

function text(value: string): JSONContent {
	return { type: 'text', text: value }
}

function variable(id: string, label: string): JSONContent {
	return { type: 'variable', attrs: { id, label } }
}

function button(label: string, href: string): JSONContent {
	return { type: 'button', attrs: { href, alignment: 'left' }, content: [text(label)] }
}
