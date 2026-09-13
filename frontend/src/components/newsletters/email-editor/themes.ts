import { extendTheme, type ThemeConfig } from '@react-email/editor/plugins'
import type { NewsletterTheme } from '@/types'

/**
 * frappe-ui light mode tokens as hex. Email clients do not support CSS variables or oklch(),
 * so the values are copied here.
 */
const TOKENS = {
	surfaceBase: '#ffffff', // surface-base
	surfaceGray2: '#f3f3f3', // surface-gray-2
	surfaceGray10: '#171717', // surface-gray-10, the solid gray Button
	outlineGray2: '#e2e2e2', // outline-gray-2
	inkBase: '#ffffff', // ink-base
	inkGray9: '#0f0f0f', // ink-gray-9
	inkGray8: '#171717', // ink-gray-8
	inkBlueLink: '#0c8ef8', // ink-blue-link
}

// InterVar is a web font in OS. Inbox apps use it only if it is installed.
const FONT_FAMILY =
	"Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', sans-serif"

const FRAPPE_UI = extendTheme('basic', {
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
		color: TOKENS.inkGray8,
		backgroundColor: TOKENS.surfaceBase,
		borderColor: TOKENS.outlineGray2,
		borderWidth: '1px',
		borderStyle: 'solid',
		borderRadius: '12px',
		paddingTop: '32px',
		paddingBottom: '32px',
		paddingLeft: '32px',
		paddingRight: '32px',
	},
	h1: { color: TOKENS.inkGray9 },
	h2: { color: TOKENS.inkGray9 },
	h3: { color: TOKENS.inkGray9 },
	link: { color: TOKENS.inkBlueLink, textDecoration: 'underline' },
	button: {
		backgroundColor: TOKENS.surfaceGray10,
		color: TOKENS.inkBase,
		borderRadius: '8px',
		paddingTop: '10px',
		paddingBottom: '10px',
		paddingLeft: '18px',
		paddingRight: '18px',
	},
	codeBlock: { backgroundColor: TOKENS.surfaceGray2, borderRadius: '8px' },
	inlineCode: { backgroundColor: TOKENS.surfaceGray2, color: TOKENS.inkGray8, borderRadius: '4px' },
})

export const EMAIL_THEMES: Record<NewsletterTheme, ThemeConfig> = {
	'Frappe UI': FRAPPE_UI,
	Basic: extendTheme('basic', {}),
	Minimal: extendTheme('minimal', {}),
}
