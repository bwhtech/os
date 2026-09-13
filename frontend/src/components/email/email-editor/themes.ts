import type { CSSProperties } from 'react'
import { extendTheme, type ThemeComponentStyles, type ThemeConfig } from '@react-email/editor/plugins'
import type { NewsletterTheme } from '@/types'

/**
 * Styles for the parts of an email that `extendTheme` ignores. Its panel map has no entry for
 * these keys, so it drops them with no error, although the docs list some of them.
 *
 * Keys are theme component keys (`blockquote`, `hr`), node and mark types (`bold`, `orderedList`), or
 * `firstChild` for the first element in the email.
 */
export type ExtraStyles = Record<string, CSSProperties>

export interface EmailTheme {
	config: ThemeConfig
	extra: ExtraStyles
}

/** The editor element for each extra key, to show the extra styles while editing. */
export const EXTRA_STYLE_SELECTORS: Record<string, string> = {
	container: '.node-container',
	firstChild: '.node-container > :first-child, .node-container > :first-child > [data-node-view-wrapper] > *',
	blockquote: 'blockquote',
	hr: 'hr',
	bold: 'strong',
	orderedList: 'ol',
	listParagraph: 'li > p',
	codeTag: 'pre code',
}

/**
 * frappe-ui light mode tokens as hex. Email clients do not support CSS variables or oklch(),
 * so the values are copied here.
 */
const TOKENS = {
	surfaceBase: '#ffffff', // surface-base
	surfaceGray2: '#f3f3f3', // surface-gray-2
	surfaceGray10: '#171717', // surface-gray-10, the solid gray Button
	outlineGray1: '#ededed', // outline-gray-1
	outlineGray2: '#e2e2e2', // outline-gray-2
	inkBase: '#ffffff', // ink-base
	inkGray1: '#ededed', // ink-gray-1
	inkGray3: '#c7c7c7', // ink-gray-3
	inkGray4: '#999999', // ink-gray-4
	inkGray6: '#525252', // ink-gray-6
	inkGray7: '#383838', // ink-gray-7
	inkGray8: '#171717', // ink-gray-8
	inkGray9: '#0f0f0f', // ink-gray-9
}

// InterVar is a web font in OS. Inbox apps use it only if it is installed.
const FONT_FAMILY =
	"Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', sans-serif"
const MONO_FONT_FAMILY =
	"ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, 'Liberation Mono', 'Courier New', monospace"

/**
 * The `prose prose-v3` styles of the frappe-ui editor, read from the computed styles in light mode.
 * Paragraphs have no margin, as in frappe-ui: an empty paragraph makes the space.
 */
const FRAPPE_UI_STYLES: ThemeComponentStyles = {
	body: {
		backgroundColor: TOKENS.surfaceGray2,
		margin: '0',
		fontFamily: FONT_FAMILY,
		fontSize: '15px',
		paddingTop: '32px',
		paddingBottom: '32px',
		paddingLeft: '16px',
		paddingRight: '16px',
	},
	container: {
		color: TOKENS.inkGray7,
		backgroundColor: TOKENS.surfaceBase,
		lineHeight: '1.7',
		letterSpacing: '0.02em',
		borderColor: TOKENS.outlineGray2,
		borderWidth: '1px',
		borderStyle: 'solid',
		borderRadius: '12px',
		paddingTop: '32px',
		paddingBottom: '32px',
		paddingLeft: '32px',
		paddingRight: '32px',
	},
	h1: {
		color: TOKENS.inkGray9,
		fontSize: '1.4286em',
		fontWeight: 600,
		lineHeight: '1.3',
		paddingTop: '32px',
		paddingBottom: '8px',
	},
	h2: {
		color: TOKENS.inkGray9,
		fontSize: '1.2857em',
		fontWeight: 600,
		lineHeight: '1.35',
		paddingTop: '32px',
		paddingBottom: '8px',
	},
	h3: {
		color: TOKENS.inkGray9,
		fontSize: '1.1429em',
		fontWeight: 600,
		lineHeight: '1.4',
		paddingTop: '24px',
		paddingBottom: '8px',
	},
	paragraph: { paddingTop: '0', paddingBottom: '0' },
	link: {
		color: TOKENS.inkGray9,
		fontWeight: 500,
		textDecoration: 'none',
		borderBottom: `1px solid ${TOKENS.inkGray4}`,
	},
	list: { paddingLeft: '1.5em', paddingTop: '4px', paddingBottom: '4px' },
	nestedList: { paddingLeft: '1.5em', paddingTop: '4px', paddingBottom: '4px' },
	// Prose margins collapse to a 4px gap between items. Email padding does not collapse, so 2px each side.
	listItem: { marginLeft: '0', paddingLeft: '0.375em', paddingTop: '2px', paddingBottom: '2px' },
	image: { marginTop: '16px', marginBottom: '16px' },
	button: {
		backgroundColor: TOKENS.surfaceGray10,
		color: TOKENS.inkBase,
		borderRadius: '8px',
		paddingTop: '10px',
		paddingBottom: '10px',
		paddingLeft: '18px',
		paddingRight: '18px',
	},
	codeBlock: {
		backgroundColor: TOKENS.surfaceGray10,
		color: TOKENS.inkGray1,
		fontFamily: MONO_FONT_FAMILY,
		fontSize: '0.857em',
		fontWeight: 400,
		lineHeight: '1.6',
		borderRadius: '6px',
		marginTop: '16px',
		marginBottom: '16px',
		paddingTop: '0.75em',
		paddingBottom: '0.75em',
		paddingLeft: '1em',
		paddingRight: '1em',
	},
	inlineCode: {
		backgroundColor: TOKENS.surfaceGray2,
		color: TOKENS.inkGray8,
		fontFamily: MONO_FONT_FAMILY,
		fontSize: '0.857em',
		borderRadius: '4px',
		paddingTop: '1px',
		paddingBottom: '1px',
		paddingLeft: '5px',
		paddingRight: '5px',
	},
}

const FRAPPE_UI_EXTRA: ExtraStyles = {
	// Not in the container panel: the editor converts panel px sizes against a 14px base.
	container: { fontSize: '15px' },
	// Prose removes the top space of the first element, so a heading does not add to the card padding.
	firstChild: { marginTop: '0', paddingTop: '0' },
	blockquote: {
		color: TOKENS.inkGray6,
		fontFamily: 'inherit',
		fontSize: '1em',
		fontStyle: 'normal',
		fontWeight: 500,
		borderLeft: `2px solid ${TOKENS.inkGray3}`,
		marginTop: '16px',
		marginBottom: '16px',
		marginLeft: '0',
		paddingLeft: '1em',
	},
	hr: {
		width: '20%',
		marginTop: '24px',
		marginBottom: '24px',
		marginLeft: 'auto',
		marginRight: 'auto',
		paddingBottom: '0',
		// Frappe's CSS inliner reorders border properties. These give the same line in any order.
		borderStyle: 'solid',
		borderColor: TOKENS.outlineGray1,
		borderWidth: '1px 0 0 0',
		borderTopWidth: '1px',
	},
	bold: { color: TOKENS.inkGray8, fontWeight: 600 },
	orderedList: { paddingLeft: '1.7em' },
	listParagraph: { marginTop: '0', marginBottom: '0' },
	codeTag: { fontFamily: MONO_FONT_FAMILY, fontSize: '1em', lineHeight: '1.6', color: TOKENS.inkGray1 },
}

export const EMAIL_THEMES: Record<NewsletterTheme, EmailTheme> = {
	'Frappe UI': { config: extendTheme('basic', FRAPPE_UI_STYLES), extra: FRAPPE_UI_EXTRA },
	Basic: { config: extendTheme('basic', {}), extra: {} },
	Minimal: { config: extendTheme('minimal', {}), extra: {} },
}
