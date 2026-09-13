import { createRoot } from 'react-dom/client'
import type { JSONContent } from '@tiptap/core'
import { EmailEditor, type EmailEditorRef } from '@react-email/editor'
import { composeReactEmail } from '@react-email/editor/core'
import { StarterKit } from '@react-email/editor/extensions'
import { EmailTheming } from '@react-email/editor/plugins'
import { Inspector } from '@react-email/editor/ui'
import { Placeholder } from '@tiptap/extension-placeholder'
import themeCss from '@react-email/editor/themes/default.css?inline'
import inspectorCss from './inspector.css?inline'
import type { NewsletterTheme } from '@/types'
import { extraStylesCss, extraThemeStyles } from './extraStyles'
import { EMAIL_THEMES } from './themes'
import { variableExtension } from './variables'
import type { EmailVariable } from '@/lib/emailVariables'

export interface EmailEditorApi {
	/** Email-safe HTML for the current document, as a full HTML document. */
	getHtml: (previewText: string) => Promise<string>
}

interface MountOptions {
	content: JSONContent | null
	theme: NewsletterTheme
	/** The `{{` menu offers these. With none, the editor has no variables. */
	variables: EmailVariable[]
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
	--re-bg: var(--surface-elevation-2);
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
.email-variable-menu {
	position: fixed;
	z-index: 1000;
	width: 20rem;
	max-height: 18rem;
	overflow-y: auto;
	padding: 4px;
	border-radius: 12px;
	border: 1px solid var(--outline-gray-2);
	background: var(--surface-elevation-2);
	box-shadow: 0 8px 24px rgba(0, 0, 0, 0.12);
	font-size: 13px;
}
.email-variable-menu-item {
	display: flex;
	flex-direction: column;
	gap: 2px;
	width: 100%;
	padding: 6px 8px;
	border-radius: 8px;
	text-align: left;
	color: var(--ink-gray-8);
}
.email-variable-menu-item[aria-selected="true"], .email-variable-menu-item:hover { background: var(--surface-gray-3); }
.email-variable-menu-label { display: flex; justify-content: space-between; gap: 8px; font-weight: 500; }
.email-variable-menu-label code { font-size: 11px; color: var(--ink-gray-5); }
.email-variable-menu-description { color: var(--ink-gray-5); line-height: 1.4; }
.email-variable-menu-empty { padding: 6px 8px; color: var(--ink-gray-5); }
`

// The email is white in both themes. CSS variables and color inherit into the shadow root, so the
// canvas sets them. The inspector uses the page tokens, so it follows the OS theme. See inspector.css.
// ProseMirror also needs its base styles, which the shadow root does not get from the page.
const EDITOR_CSS = `
.editor-layout { display: flex; flex-wrap: wrap; align-items: stretch; }
.email-canvas {
	flex: 1 1 36rem;
	min-width: 0;
	color-scheme: light;
	color: #1c1c1c;
	background: #fff;
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
.email-variable {
	display: inline-block;
	padding: 0 6px;
	border-radius: 6px;
	background: #e6f1fe;
	color: #0b5ecf;
	font-weight: 500;
	line-height: 1.45;
	white-space: nowrap;
	cursor: default;
}
.email-variable::before { content: "{ }"; margin-right: 4px; font-size: 0.8em; opacity: 0.6; }
.ProseMirror-selectednode .email-variable, .email-variable.ProseMirror-selectednode { outline: 2px solid #0b5ecf; }
.ProseMirror p.is-empty::before { content: attr(data-placeholder); float: left; height: 0; pointer-events: none; color: #a3a3a3; }
`

/**
 * Mount the React Email editor in a shadow root, so its styles and the frappe-ui styles stay apart.
 * The slash menu and link forms render into document.body, so the theme also goes on the page once.
 */
export function mountEmailEditor(shadow: ShadowRoot, options: MountOptions) {
	addPageTheme()
	const style = document.createElement('style')
	style.textContent = themeCss + inspectorCss + EDITOR_CSS
	const container = document.createElement('div')
	// EmailEditor renders its children as siblings of the editor content, so the inspector sits beside it.
	container.className = 'editor-layout'
	shadow.append(style, container)
	const stopMirror = mirrorThemeStyles(shadow)

	const extraCss = document.createElement('style')
	shadow.append(extraCss)

	const root = createRoot(container)
	let editorRef: EmailEditorRef | null = null
	const render = (themeName: NewsletterTheme, content: JSONContent | null) => {
		const theme = EMAIL_THEMES[themeName]
		extraCss.textContent = extraStylesCss(theme.extra)
		root.render(
			<EmailEditor
				content={content ?? undefined}
				// A new theme object gives a new editor, so the theme applies to the whole document.
				theme={theme.config}
				extensions={editorExtensions(theme, options.variables)}
				onUpdate={(ref) => options.onChange(ref.getJSON())}
				onReady={(ref) => {
					editorRef = ref
					options.onReady(toApi(ref))
				}}
				onUploadImage={options.uploadImage}
				className="email-canvas"
			>
				<Inspector.Root className="email-inspector">
					<Inspector.Breadcrumb />
					<Inspector.Document />
					<Inspector.Node />
					<Inspector.Text />
				</Inspector.Root>
			</EmailEditor>,
		)
	}
	render(options.theme, options.content)

	return {
		/** Restyle the current content. The undo history starts again. */
		setTheme(theme: NewsletterTheme) {
			const content = editorRef ? withoutThemeStyles(editorRef.getJSON()) : options.content
			render(theme, content)
		},
		unmount() {
			stopMirror()
			root.unmount()
		},
	}
}

/** The extensions that EmailEditor uses by default, and the extra theme styles after EmailTheming. */
function editorExtensions(theme: (typeof EMAIL_THEMES)[NewsletterTheme], variables: EmailVariable[]) {
	return [
		...(variables.length ? [variableExtension(variables)] : []),
		StarterKit.configure(),
		Placeholder.configure({
			placeholder: ({ node }) =>
				node.type.name === 'heading'
					? `Heading ${node.attrs.level}`
					: variables.length
						? "Press '/' for commands, or '{{' for a variable"
						: "Press '/' for commands",
			includeChildren: true,
		}),
		EmailTheming.configure({ theme: theme.config }),
		extraThemeStyles(theme.extra),
	]
}

/**
 * The editor saves the document styles in a globalContent node: the theme, with the changes made in
 * the inspector. It uses the theme only when that node is missing, so a new theme removes the node.
 */
function withoutThemeStyles(json: JSONContent): JSONContent {
	return { ...json, content: json.content?.filter((node) => node.type !== 'globalContent') }
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
