import { ref } from 'vue'

/** The Settings dialog is shared, so a page can open it at its own panel. */
const open = ref(false)
const tab = ref('sending')

export function useSettingsDialog() {
	function openSettings(panel?: string) {
		if (panel) tab.value = panel
		open.value = true
	}
	return { open, tab, openSettings }
}
