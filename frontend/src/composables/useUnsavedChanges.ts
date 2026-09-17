import { onBeforeUnmount, watch, type Ref } from 'vue'
import { onBeforeRouteLeave } from 'vue-router'

/**
 * Keeps work that has not been saved from leaving with the page. A page that saves on a
 * button, rather than as you type, has one way to lose an hour: a reload, a back button,
 * or a link in the sidebar. This asks first, both ways out.
 *
 * The browser writes its own words in the reload dialog and ignores ours; a route inside
 * the app gets the message below.
 */
export function useUnsavedChanges(dirty: Ref<boolean>, message = 'Leave without saving your changes?') {
	watch(dirty, (unsaved) => (unsaved ? window.addEventListener('beforeunload', warn) : stop()), {
		immediate: true,
	})

	onBeforeRouteLeave(() => {
		if (!dirty.value) return true
		const leaving = window.confirm(message)
		if (leaving) stop()
		return leaving
	})

	onBeforeUnmount(stop)
}

function stop() {
	window.removeEventListener('beforeunload', warn)
}

function warn(event: BeforeUnloadEvent) {
	event.preventDefault()
}
