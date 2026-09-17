import { onBeforeUnmount, onMounted } from 'vue'

/**
 * Cmd+S, or Ctrl+S, saves the page. Anyone who writes for a living presses it out of
 * habit, and a browser answers with its own Save Page dialog, which is never what was
 * meant. The page takes the chord back even when there is nothing to save, because the
 * dialog is the wrong answer either way.
 *
 * The listener sits on the window: the key event comes out of the email editor's shadow
 * root, and out of whatever else on the page holds focus.
 */
export function useSaveShortcut(save: () => void) {
	function onKeydown(event: KeyboardEvent) {
		if (event.key.toLowerCase() !== 's') return
		if (!(event.metaKey || event.ctrlKey) || event.altKey || event.shiftKey) return
		event.preventDefault()
		save()
	}

	onMounted(() => window.addEventListener('keydown', onKeydown))
	onBeforeUnmount(() => window.removeEventListener('keydown', onKeydown))
}
