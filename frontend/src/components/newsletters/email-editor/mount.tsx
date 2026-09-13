import { createRoot } from 'react-dom/client'
import type { JSONContent } from '@tiptap/core'
import { EmailEditor, type EmailEditorRef } from '@react-email/editor'
import { composeReactEmail } from '@react-email/editor/core'
import themeCss from '@react-email/editor/themes/default.css?inline'

export interface EmailEditorApi {
	/** Email-safe HTML for the current document, as a full HTML document. */
	getHtml: (previewText: string) => Promise<string>
}

interface MountOptions {
	content: JSONContent | null
	onChange: (json: JSONContent) => void
	onReady: (api: EmailEditorApi) => void
	uploadImage: (file: File) => Promise<{ url: string }>
}

/**
 * The editor theme follows prefers-color-scheme, not the OS theme switch. The menus on the page use
 * frappe-ui tokens instead, so they match the rest of OS in light and dark.
 */
const PAGE_CSS = `
:root:root {
	--re-bg: var(--surface-elevated, var(--surface-base));
	--re-bg-active: var(--surface-gray-3);
	--re-border: var(--outline-gray-2);
	--re-separator: var(--outline-gray-2);
	--re-text: var(--ink-gray-8);
	--re-text-muted: var(--ink-gray-5);
	--re-hover: var(--surface-gray-2);
	--re-active: var(--surface-gray-3);
	--re-pressed: var(--surface-gray-3);
	--re-danger: var(--ink-red-4);
}
`

// The email is white in both themes. CSS variables and color inherit into the shadow root, so set them.
// ProseMirror also needs its base styles, which the shadow root does not get from the page.
const EDITOR_CSS = `
:host {
	color-scheme: light;
	color: #1c1c1c;
	--re-bg: #fff;
	--re-bg-active: #f5f5f5;
	--re-border: #e5e5e5;
	--re-separator: #e5e5e5;
	--re-text: #1c1c1c;
	--re-text-muted: #6b6b6b;
	--re-hover: rgba(0, 0, 0, 0.04);
	--re-active: rgba(0, 0, 0, 0.06);
	--re-pressed: rgba(0, 0, 0, 0.06);
	--re-danger: #dc2626;
}
.ProseMirror { white-space: pre-wrap; word-wrap: break-word; outline: none; min-height: 24rem; }
.ProseMirror p.is-empty::before { content: attr(data-placeholder); float: left; height: 0; pointer-events: none; color: #a3a3a3; }
`

/**
 * Mount the React Email editor in a shadow root, so its styles and the frappe-ui styles stay apart.
 * The slash menu and link forms render into document.body, so the theme also goes on the page once.
 */
export function mountEmailEditor(shadow: ShadowRoot, options: MountOptions) {
	addPageTheme()
	const style = document.createElement('style')
	style.textContent = themeCss + EDITOR_CSS
	const container = document.createElement('div')
	shadow.append(style, container)
	const stopMirror = mirrorThemeStyles(shadow)

	const root = createRoot(container)
	root.render(
		<EmailEditor
			content={options.content ?? undefined}
			onUpdate={(ref) => options.onChange(ref.getJSON())}
			onReady={(ref) => options.onReady(toApi(ref))}
			onUploadImage={options.uploadImage}
		/>,
	)
	return () => {
		stopMirror()
		root.unmount()
	}
}

/** The editor writes the styles for headings, buttons, and other nodes to document.head. */
const THEME_STYLE_SELECTOR = 'style[id^="tiptap-theme-"]'

/** Copy the editor's node styles into the shadow root and keep them in sync. */
function mirrorThemeStyles(shadow: ShadowRoot) {
	const mirror = document.createElement('style')
	shadow.append(mirror)
	const sync = () => {
		const css = Array.from(document.head.querySelectorAll(THEME_STYLE_SELECTOR), (s) => s.textContent).join('\n')
		if (mirror.textContent !== css) mirror.textContent = css
	}
	const observer = new MutationObserver(sync)
	observer.observe(document.head, { childList: true, subtree: true, characterData: true })
	sync()
	return () => {
		observer.disconnect()
		// Each editor has its own scope id, so its styles are not needed after unmount.
		const scope = shadow.querySelector('[data-editor-theme-scope]')?.getAttribute('data-editor-theme-scope')
		if (scope) document.head.querySelectorAll(`style[id^="${scope}-"]`).forEach((s) => s.remove())
	}
}

function toApi(ref: EmailEditorRef): EmailEditorApi {
	return {
		async getHtml(previewText) {
			if (!ref.editor) return ''
			const email = await composeReactEmail({ editor: ref.editor, preview: previewText || undefined })
			return email.unformattedHtml
		},
	}
}

const PAGE_THEME_ID = 'react-email-editor-theme'

function addPageTheme() {
	if (document.getElementById(PAGE_THEME_ID)) return
	const style = document.createElement('style')
	style.id = PAGE_THEME_ID
	style.textContent = themeCss + PAGE_CSS
	document.head.append(style)
}
