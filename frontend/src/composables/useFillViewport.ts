import { onBeforeUnmount, onMounted, ref, type Ref } from 'vue'

/**
 * The height that makes `target` reach the bottom of the viewport.
 *
 * A kanban board wants columns of one fixed height that scroll internally, but
 * it is rendered inside pages that scroll vertically themselves. Rather than
 * threading `min-h-0` through every ancestor, the board measures where its own
 * top edge landed and claims the rest of the screen. Copied from bwh_hive.
 */
export function useFillViewport(
	target: Ref<HTMLElement | null>,
	options: { min?: number; gap?: number } = {},
) {
	const { min = 320, gap = 20 } = options
	const height = ref('')

	function measure() {
		const el = target.value
		if (!el) return
		const available = window.innerHeight - el.getBoundingClientRect().top - gap
		const next = `${Math.max(Math.round(available), min)}px`
		// Assigning unconditionally would feed the parent observer its own output.
		if (next !== height.value) height.value = next
	}

	let observer: ResizeObserver | null = null

	onMounted(() => {
		measure()
		window.addEventListener('resize', measure)
		// Anything above the board changing size, such as filters wrapping,
		// moves its top edge, so watch the stack it sits in.
		const parent = target.value?.parentElement
		if (parent) {
			observer = new ResizeObserver(measure)
			observer.observe(parent)
		}
	})

	onBeforeUnmount(() => {
		window.removeEventListener('resize', measure)
		observer?.disconnect()
	})

	return { height, measure }
}
