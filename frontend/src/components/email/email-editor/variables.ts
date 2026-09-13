import { InputRule, PasteRule } from '@tiptap/core'
import { Mention } from '@tiptap/extension-mention'
import type { SuggestionKeyDownProps, SuggestionProps } from '@tiptap/suggestion'
import { EmailNode } from '@react-email/editor/core'
import type { EmailVariable } from '@/lib/emailVariables'

/** `{{ first_name }}` typed or pasted as text */
const TYPED_VARIABLE = /\{\{\s*([a-z_]+)\s*\}\}$/
const PASTED_VARIABLE = /\{\{\s*([a-z_]+)\s*\}\}/g

/**
 * A variable chip. Type `{{` to pick one. The email gets `{{ key }}`, and the server puts the
 * subscriber's value in its place when it sends.
 */
export function variableExtension(variables: EmailVariable[]) {
	const byKey = new Map(variables.map((variable) => [variable.key, variable]))
	const attrsFor = (key: string) => (byKey.has(key) ? { id: key, label: byKey.get(key)!.label } : null)

	const node = Mention.extend({
		name: 'variable',

		renderHTML({ node }) {
			const variable = byKey.get(node.attrs.id)
			return [
				'span',
				{ class: 'email-variable', 'data-variable': node.attrs.id, title: variable ? describe(variable) : '' },
				variable?.label ?? node.attrs.id,
			]
		},

		renderText({ node }) {
			return `{{ ${node.attrs.id} }}`
		},

		// Not nodeInputRule: with a capture group, it replaces only the group and leaves the braces.
		addInputRules() {
			const type = this.type
			return [
				new InputRule({
					find: TYPED_VARIABLE,
					handler: ({ state, range, match }) => {
						const attrs = attrsFor(match[1])
						if (attrs) state.tr.replaceWith(range.from, range.to, type.create(attrs))
					},
				}),
			]
		},

		addPasteRules() {
			const type = this.type
			return [
				new PasteRule({
					find: PASTED_VARIABLE,
					handler: ({ state, range, match }) => {
						const attrs = attrsFor(match[1])
						if (attrs) state.tr.replaceWith(range.from, range.to, type.create(attrs))
					},
				}),
			]
		},
	}).configure({
		suggestion: {
			char: '{{',
			// A variable can follow any text, for example "Hi,{{".
			allowedPrefixes: null,
			items: ({ query }) => filterVariables(variables, query),
			// Mention adds a space after the chip. Punctuation often follows a variable, so it adds none.
			command: ({ editor, range, props }) => {
				editor.chain().focus().insertContentAt(range, { type: 'variable', attrs: props }).run()
			},
			render: variableMenu,
		},
	})

	return EmailNode.from(node, ({ node }) => `{{ ${node.attrs?.id} }}`)
}

export function describe(variable: EmailVariable): string {
	const fallback = variable.fallback ? ` When empty: “${variable.fallback}”.` : ''
	return `${variable.description}${fallback}`
}

function filterVariables(variables: EmailVariable[], query: string) {
	const text = query.trim().toLowerCase()
	return variables.filter(
		(variable) => variable.key.includes(text) || variable.label.toLowerCase().includes(text),
	)
}

type MenuProps = SuggestionProps<EmailVariable, { id: string; label: string }>

/** The `{{` menu. It renders on the page, like the editor's slash menu. See PAGE_CSS in mount.tsx. */
function variableMenu() {
	let element: HTMLDivElement | null = null
	let props: MenuProps | null = null
	let active = 0

	const pick = (index: number) => {
		const variable = props?.items[index]
		if (variable) props?.command({ id: variable.key, label: variable.label })
	}

	const draw = () => {
		if (!element || !props) return
		element.replaceChildren(
			...(props.items.length
				? props.items.map((variable, index) => menuItem(variable, index === active, () => pick(index)))
				: [emptyItem()]),
		)
		const rect = props.clientRect?.()
		if (rect) {
			element.style.left = `${rect.left}px`
			element.style.top = `${rect.bottom + 6}px`
		}
	}

	return {
		onStart(next: MenuProps) {
			props = next
			active = 0
			element = document.createElement('div')
			element.className = 'email-variable-menu'
			element.setAttribute('role', 'listbox')
			document.body.append(element)
			draw()
		},
		onUpdate(next: MenuProps) {
			props = next
			active = Math.min(active, Math.max(next.items.length - 1, 0))
			draw()
		},
		onKeyDown({ event }: SuggestionKeyDownProps) {
			const count = props?.items.length ?? 0
			if (event.key === 'Escape') {
				element?.remove()
				return true
			}
			if (!count) return false
			if (event.key === 'ArrowDown' || event.key === 'ArrowUp') {
				active = (active + (event.key === 'ArrowDown' ? 1 : count - 1)) % count
				draw()
				return true
			}
			if (event.key === 'Enter' || event.key === 'Tab') {
				pick(active)
				return true
			}
			return false
		},
		onExit() {
			element?.remove()
			element = null
			props = null
		},
	}
}

function menuItem(variable: EmailVariable, isActive: boolean, onPick: () => void) {
	const item = document.createElement('button')
	item.type = 'button'
	item.className = 'email-variable-menu-item'
	item.setAttribute('role', 'option')
	item.setAttribute('aria-selected', String(isActive))
	// mousedown, so the editor keeps focus and the suggestion range.
	item.addEventListener('mousedown', (event) => {
		event.preventDefault()
		onPick()
	})

	const label = document.createElement('span')
	label.className = 'email-variable-menu-label'
	label.textContent = variable.label
	const key = document.createElement('code')
	key.textContent = `{{ ${variable.key} }}`
	label.append(key)

	const description = document.createElement('span')
	description.className = 'email-variable-menu-description'
	description.textContent = `${describe(variable)} Example: ${variable.sample}`

	item.append(label, description)
	return item
}

function emptyItem() {
	const item = document.createElement('div')
	item.className = 'email-variable-menu-empty'
	item.textContent = 'No variable matches'
	return item
}
