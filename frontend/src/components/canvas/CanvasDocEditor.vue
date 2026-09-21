<template>
	<div v-if="!canvas.doc || !fresh" class="px-3 py-6 sm:px-5">
		<ErrorMessage v-if="canvas.error" :message="errorMessage(canvas.error)" />
		<DetailSkeleton v-else class="mx-auto max-w-[770px]" />
	</div>

	<!-- Full screen shows this element alone, so it carries the page background. -->
	<div v-else ref="frame" class="bg-surface-white">
		<!-- A new key for each canvas, because the editor reads the scene only when it mounts. -->
		<CanvasEditor
			ref="editor"
			:key="canvas.doc.name"
			class="size-full"
			:scene="canvas.doc.scene"
			:upload-file="uploadFile"
			@change="change"
			@thumbnail="(thumbnail) => queue({ thumbnail })"
		/>
	</div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { ErrorMessage, upload, useDoc } from 'frappe-ui'
import CanvasEditor from '@/components/canvas/CanvasEditor.vue'
import DetailSkeleton from '@/components/stats/DetailSkeleton.vue'
import { type SaveState, useAutosave } from '@/composables/useAutosave'
import { errorMessage } from '@/lib/errors'
import type { Canvas } from '@/types'

/**
 * A saved canvas: loads it, draws it, and saves it as it changes. The parent keys it by
 * `canvasId`, because the pending save and the window channel belong to one canvas.
 */
const props = defineProps<{ canvasId: string }>()

/** For the page to show next to its header. */
const saveState = defineModel<SaveState>('saveState', { default: 'idle' })

const canvas = useDoc<Canvas>({ doctype: 'BWH Canvas', name: computed(() => props.canvasId) })

// frappe-ui shows a cached copy of the doc first, and the editor reads the scene only once.
// A stale copy would be drawn on and saved over the newer one, so wait for the server's.
const fresh = ref(false)
canvas.onSuccess(() => (fresh.value = true))

// A drawing changes many times a second, so wait for a longer pause than the text editors do.
const { state, queue, flush } = useAutosave<Canvas>((values) => canvas.setValue.submit(values), 1500)

watch(state, (value) => (saveState.value = value), { immediate: true })

// The same canvas open in another window, such as the pop-out used for recording, draws
// what this one draws. Only the window that drew it saves it.
const channel = new BroadcastChannel(`bwh-os-canvas:${props.canvasId}`)
const editor = ref<InstanceType<typeof CanvasEditor> | null>(null)
channel.onmessage = ({ data }: MessageEvent<string>) => editor.value?.setScene(data)
onBeforeUnmount(() => channel.close())

function change(scene: string) {
	queue({ scene })
	channel.postMessage(scene)
}

/** Images pasted into the canvas are private files attached to it, and go when it goes. */
async function uploadFile(file: File) {
	const uploaded = await upload(file, { private: true, doctype: 'BWH Canvas', docname: props.canvasId })
	return uploaded.file_url
}

const frame = ref<HTMLElement | null>(null)

defineExpose({
	flush,
	/** Show the canvas alone on the whole screen. Esc leaves. */
	enterFullscreen: () => frame.value?.requestFullscreen(),
})
</script>
