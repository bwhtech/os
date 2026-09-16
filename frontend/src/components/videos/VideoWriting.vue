<template>
	<div>
		<div class="flex items-center gap-3">
			<TabButtons v-model="tab" :options="TABS" />
			<span class="ml-auto text-xs text-ink-gray-5" aria-live="polite">{{ SAVE_LABELS[state] }}</span>
		</div>

		<Editor
			:key="tab"
			:model-value="drafts[tab]"
			:extensions="extensions"
			:placeholder="PLACEHOLDERS[tab]"
			:upload-function="uploadImage"
			@update:model-value="edit"
		>
			<template #default="{ editor }">
				<div class="mt-4 rounded-4 border border-outline-gray-2 focus-within:border-outline-gray-3">
					<!-- Scrolls sideways on phones, without the native scrollbar. -->
					<div class="overflow-x-auto border-b border-outline-gray-2 px-2 py-1 [scrollbar-width:none]">
						<EditorFixedMenu :editor="editor" :items="articleToolbar" size="xs" />
					</div>
					<EditorContent :editor="editor" class="min-h-[24rem] px-5 py-4" />
				</div>
			</template>
		</Editor>
	</div>
</template>

<script setup lang="ts">
import { reactive, ref } from 'vue'
import { TabButtons, upload } from 'frappe-ui'
import {
	Editor,
	EditorContent,
	EditorFixedMenu,
	RichTextKit,
	articleToolbar,
	type UploadedFile,
} from 'frappe-ui/editor'
import { useAutosave } from '@/composables/useAutosave'
import type { Video } from '@/types'

type Field = 'research' | 'script' | 'description'

const props = defineProps<{
	video: Video
	save: (values: Partial<Video>) => Promise<unknown>
}>()

const TABS = [
	{ label: 'Research', value: 'research' },
	{ label: 'Script', value: 'script' },
	{ label: 'Description', value: 'description' },
]

const PLACEHOLDERS: Record<Field, string> = {
	research: 'Links, notes, outlines, screenshots…',
	script: 'Write the hook, then the beats…',
	description: 'The YouTube description, with chapters and links…',
}

const SAVE_LABELS = { idle: '', saving: 'Saving…', saved: 'Saved', error: 'Not saved' }

const extensions = [RichTextKit]

const tab = ref<Field>('research')

// Loaded once. Later copies of the doc come from our own saves, and taking them
// back while typing would move the cursor.
const drafts = reactive<Record<Field, string>>({
	research: props.video.research ?? '',
	script: props.video.script ?? '',
	description: props.video.description ?? '',
})

const { state, queue } = useAutosave<Video>(props.save)

function edit(value: unknown) {
	drafts[tab.value] = String(value ?? '')
	queue({ [tab.value]: drafts[tab.value] })
}

/** Images pasted into the notes are attached to the video, so they show under Attachments too. */
async function uploadImage(file: File): Promise<UploadedFile> {
	const uploaded = await upload(file, { private: true, doctype: 'BWH Video', docname: String(props.video.name) })
	return { ...uploaded }
}
</script>
