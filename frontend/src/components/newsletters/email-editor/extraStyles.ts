import type { CSSProperties, ReactNode } from 'react'
import { Extension, type Editor, type JSONContent } from '@tiptap/core'
import { getThemeComponentKey } from '@react-email/editor/plugins'
import { EXTRA_STYLE_SELECTORS, type ExtraStyles } from './themes'

type BaseTemplateProps = { editor: Editor; previewText?: string; previewMode?: boolean; children: ReactNode }

type SerializerPlugin = {
	getNodeStyles: (node: JSONContent, depth: number, editor: Editor) => CSSProperties
	BaseTemplate: (props: BaseTemplateProps) => ReactNode
}

/**
 * Adds the extra theme styles to the exported email. composeReactEmail uses the serializer plugin of
 * the last extension that has one, so this extension must come after EmailTheming. It asks
 * EmailTheming first and puts the extra styles on top.
 */
export function extraThemeStyles(extra: ExtraStyles) {
	// composeReactEmail asks for styles in document order, so the call after the container is its first child.
	let nextIsFirstChild = false
	return Extension.create({
		name: 'extraThemeStyles',
		addOptions() {
			return {
				serializerPlugin: {
					getNodeStyles(node: JSONContent, depth: number, editor: Editor) {
						const base = themingPlugin(editor)?.getNodeStyles(node, depth, editor) ?? {}
						const key = getThemeComponentKey(node.type ?? '', depth, node.attrs ?? {})
						const isFirstChild = nextIsFirstChild
						nextIsFirstChild = node.type === 'container'
						return {
							...base,
							...(key ? extra[key] : undefined),
							...(node.type && node.type !== key ? extra[node.type] : undefined),
							...(isFirstChild ? extra.firstChild : undefined),
						}
					},
					// The document template of EmailTheming. It uses no hooks, so a plain call is fine.
					BaseTemplate(props: BaseTemplateProps) {
						return themingPlugin(props.editor)?.BaseTemplate(props)
					},
				},
			}
		},
	})
}

function themingPlugin(editor: Editor): SerializerPlugin | undefined {
	return editor.extensionManager.extensions.find((extension) => extension.name === 'theming')?.options
		?.serializerPlugin
}

/** CSS that shows the extra styles in the editor. Important, because some node views set inline styles. */
export function extraStylesCss(extra: ExtraStyles): string {
	return Object.entries(extra)
		.filter(([key]) => EXTRA_STYLE_SELECTORS[key])
		.map(([key, styles]) => {
			const selector = EXTRA_STYLE_SELECTORS[key]
				.split(', ')
				.map((part) => `:host .tiptap.ProseMirror[data-editor-theme-scope] ${part}`)
				.join(', ')
			const declarations = Object.entries(styles)
				.map(([prop, value]) => `${prop.replace(/[A-Z]/g, (c) => `-${c.toLowerCase()}`)}: ${value} !important;`)
				.join(' ')
			return `${selector} { ${declarations} }`
		})
		.join('\n')
}
