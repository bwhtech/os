<template>
	<!-- No padding: the theme sets the email background and spacing. -->
	<div class="relative overflow-hidden rounded-6 border border-outline-gray-2">
		<div v-if="!ready" class="space-y-3 p-4" aria-busy="true" aria-label="Loading editor">
			<Skeleton class="h-6 w-1/2 rounded-4" />
			<Skeleton class="h-4 w-full rounded-4" />
			<Skeleton class="h-4 w-4/5 rounded-4" />
			<Skeleton class="h-40 w-full rounded-6" />
		</div>
		<div ref="host" />
	</div>
</template>

<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { Skeleton } from 'frappe-ui'
import type { EmailEditorApi, MountedEmailEditor } from '@/components/email/email-editor/api'
import type { EmailVariable } from '@/lib/emailVariables'
import type { EmailDocument, NewsletterTheme } from '@/types'

const props = withDefaults(
	defineProps<{
		theme: NewsletterTheme
		/** Read once, on mount */
		variables?: EmailVariable[]
	}>(),
	{ variables: () => [] },
)

/** The editor keeps its own state after mount. The model only reports changes out. */
const document_ = defineModel<EmailDocument | null>({ required: true })

const host = ref<HTMLElement>()
const ready = ref(false)
let api: EmailEditorApi | null = null
let mounted: MountedEmailEditor | null = null

onMounted(async () => {
	// React and the editor are large, so they load only on this page.
	// Keep the alias. tsconfig.json points it at `api.ts`, so the app typecheck never loads React Email.
	const { mountEmailEditor } = await import('@/components/email/email-editor/mount')
	if (!host.value) return
	mounted = mountEmailEditor(host.value.attachShadow({ mode: 'open' }), {
		content: document_.value,
		theme: props.theme,
		variables: props.variables,
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

watch(
	() => props.theme,
	(theme) => mounted?.setTheme(theme),
)

onBeforeUnmount(() => mounted?.unmount())

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
