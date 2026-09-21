<template>
	<Button variant="ghost" icon="lucide-maximize" aria-label="Full screen" tooltip="Full screen" @click="emit('fullscreen')" />
	<Button
		variant="ghost"
		icon="lucide-picture-in-picture-2"
		aria-label="Open in new window"
		tooltip="Open in new window"
		@click="popOut"
	/>
</template>

<script setup lang="ts">
import { Button } from 'frappe-ui'
import { useRouter } from 'vue-router'

/** Ways to show a canvas while recording: full screen, or a window of its own to capture. */
const props = defineProps<{ canvasId: string }>()
const emit = defineEmits<{ fullscreen: [] }>()

const router = useRouter()

function popOut() {
	const url = router.resolve({ name: 'Canvas Window', params: { canvasId: props.canvasId } }).href
	// A name per canvas, so a second click brings the same window back instead of a new one.
	window.open(url, `bwh-os-canvas-${props.canvasId}`, 'popup,width=1280,height=800')?.focus()
}
</script>
