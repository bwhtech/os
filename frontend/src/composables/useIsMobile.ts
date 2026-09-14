import { ref } from 'vue'

/** Below Tailwind's `sm` breakpoint the app renders the mobile shell. */
const query = window.matchMedia('(max-width: 639px)')
const isMobile = ref(query.matches)
query.addEventListener('change', (event) => {
	isMobile.value = event.matches
})

/** Whether the viewport is phone-sized. A module singleton, so every caller shares one listener. */
export function useIsMobile() {
	return isMobile
}
