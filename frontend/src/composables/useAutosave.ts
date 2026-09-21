import { onBeforeUnmount, ref } from 'vue'
import { toast } from 'frappe-ui'
import { useSaveShortcut } from '@/composables/useSaveShortcut'
import { errorMessage } from '@/lib/errors'

export type SaveState = 'idle' | 'saving' | 'saved' | 'error'

/** What a page shows next to its content for each state. */
export const SAVE_LABELS: Record<SaveState, string> = { idle: '', saving: 'Saving…', saved: 'Saved', error: 'Not saved' }

/**
 * Collects edits and saves them together after a pause in typing.
 * Edits that arrive during a save wait for the next one, so a slow response
 * never sends an old value after a newer one.
 */
export function useAutosave<T extends object>(save: (values: Partial<T>) => Promise<unknown>, delay = 800) {
	const state = ref<SaveState>('idle')
	let pending: Partial<T> = {}
	let timer: ReturnType<typeof setTimeout> | undefined
	let inFlight: Promise<void> | null = null

	function queue(values: Partial<T>) {
		Object.assign(pending, values)
		clearTimeout(timer)
		timer = setTimeout(flush, delay)
	}

	async function flush() {
		clearTimeout(timer)
		if (inFlight) await inFlight
		if (!Object.keys(pending).length) return
		const values = pending
		pending = {}
		inFlight = send(values)
		await inFlight
		inFlight = null
	}

	async function send(values: Partial<T>) {
		state.value = 'saving'
		try {
			await save(values)
			state.value = 'saved'
		} catch (error) {
			state.value = 'error'
			toast.error(errorMessage(error as Error))
		}
	}

	// Leaving the page must not drop the last few keystrokes.
	onBeforeUnmount(flush)

	// A page that saves itself still gets Cmd+S: it sends what is waiting right now, so
	// the habit means the same thing here as on a page with a Save button.
	useSaveShortcut(flush)

	return { state, queue, flush }
}
