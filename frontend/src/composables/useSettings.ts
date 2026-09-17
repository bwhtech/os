import { ref } from 'vue'

/**
 * The settings dialog lives in the shell, so a page that wants it open says so here.
 * A channel whose token died is the reason: the fix is in Settings, one click away.
 */
const open = ref(false)
const tab = ref('sending')

export function useSettings() {
	function show(at?: string) {
		if (at) tab.value = at
		open.value = true
	}

	return { open, tab, show }
}
