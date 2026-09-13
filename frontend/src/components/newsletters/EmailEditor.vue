<template>
	<div class="relative rounded-6 border border-outline-gray-2 bg-white px-6 py-4">
		<LoadingText v-if="!ready" :lines="4" />
		<div ref="host" />
	</div>
</template>

<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from 'vue'
import { LoadingText } from 'frappe-ui'
import type { EmailEditorApi } from './email-editor/mount'
import type { EmailDocument } from '@/types'

/** The editor keeps its own state after mount. The model only reports changes out. */
const document_ = defineModel<EmailDocument | null>({ required: true })

const host = ref<HTMLElement>()
const ready = ref(false)
let api: EmailEditorApi | null = null
let unmount: (() => void) | null = null

onMounted(async () => {
	// React and the editor are large, so they load only on this page.
	const { mountEmailEditor } = await import('./email-editor/mount')
	if (!host.value) return
	unmount = mountEmailEditor(host.value.attachShadow({ mode: 'open' }), {
		content: document_.value,
		onChange: (json) => {
			document_.value = json
		},
		onReady: (editorApi) => {
			api = editorApi
			ready.value = true
		},
		uploadImage,
	})
})

onBeforeUnmount(() => unmount?.())

/** Email clients need a public image, so uploads are public files. */
async function uploadImage(file: File): Promise<{ url: string }> {
	const body = new FormData()
	body.append('file', file, file.name)
	body.append('is_private', '0')
	const response = await fetch('/api/method/upload_file', {
		method: 'POST',
		body,
		headers: { 'X-Frappe-CSRF-Token': window.csrf_token ?? '' },
	})
	if (!response.ok) throw new Error('Image upload failed')
	const { message } = await response.json()
	return { url: message.file_url }
}

defineExpose({
	/** Email HTML for the current content. Empty until the editor is ready. */
	getHtml: (previewText: string) => api?.getHtml(previewText) ?? Promise.resolve(''),
})
</script>
