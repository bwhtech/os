<template>
	<section>
		<div class="flex items-center gap-2">
			<h3 class="text-base-semibold text-ink-gray-8">Attachments</h3>
			<span class="text-xs tabular-nums text-ink-gray-5">{{ rows.length }}</span>
			<div class="ml-auto flex gap-1">
				<Button variant="ghost" size="sm" icon="lucide-link" tooltip="Add link" aria-label="Add link" @click="addLink" />
				<FileUploader private doctype="BWH Video" :docname="videoName" @success="files.reload()" @failure="onFailure">
					<template #default="{ uploading, openFileSelector }">
						<Button
							variant="ghost"
							size="sm"
							icon="lucide-upload"
							tooltip="Upload file"
							aria-label="Upload file"
							:loading="uploading"
							@click="openFileSelector"
						/>
					</template>
				</FileUploader>
			</div>
		</div>

		<div v-if="rows.length" class="-mx-2 mt-2 space-y-0.5">
			<div
				v-for="file in rows"
				:key="file.name"
				class="group flex h-9 items-center gap-2 rounded-4 px-2 hover:bg-surface-gray-2"
			>
				<span :class="[fileIcon(file), 'size-4 shrink-0 text-ink-gray-5']" aria-hidden="true" />
				<a
					:href="file.file_url"
					target="_blank"
					rel="noopener noreferrer"
					class="min-w-0 flex-1 truncate text-sm text-ink-gray-8 hover:underline"
				>
					{{ label(file) }}
				</a>
				<span class="text-xs tabular-nums text-ink-gray-5 group-hover:hidden">{{ size(file) }}</span>
				<Button
					class="hidden group-hover:flex"
					variant="ghost"
					size="sm"
					icon="lucide-x"
					aria-label="Remove"
					@click="remove(file)"
				/>
			</div>
		</div>

		<FileUploader v-else private doctype="BWH Video" :docname="videoName" @success="files.reload()" @failure="onFailure">
			<template #default="{ uploading, progress, openFileSelector }">
				<button
					type="button"
					class="mt-3 flex w-full flex-col items-center gap-1 rounded-4 border border-dashed border-outline-gray-2 py-6 text-center hover:bg-surface-gray-1"
					@click="openFileSelector"
				>
					<span class="lucide-paperclip size-4 text-ink-gray-5" aria-hidden="true" />
					<span class="text-sm text-ink-gray-7">{{ uploading ? `Uploading ${progress}%` : 'Attach files' }}</span>
					<span class="text-xs text-ink-gray-5">PDFs, images, code, B-roll</span>
				</button>
			</template>
		</FileUploader>
	</section>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { Button, FileUploader, dialog, toast, useList } from 'frappe-ui'
import { errorMessage } from '@/lib/errors'
import type { VideoFile } from '@/types'

const props = defineProps<{ videoName: string }>()

const files = useList<VideoFile>({
	doctype: 'File',
	fields: ['name', 'file_name', 'file_url', 'file_size', 'is_private'],
	filters: () => ({ attached_to_doctype: 'BWH Video', attached_to_name: props.videoName }),
	orderBy: 'creation desc',
	limit: 100,
})

const rows = computed(() => files.data ?? [])

function addLink() {
	dialog.prompt({
		title: 'Add Link',
		confirmLabel: 'Add',
		fields: [{ name: 'url', label: 'URL', placeholder: 'https://', required: true, validate: validateUrl }],
		onConfirm: async ({ values }) => {
			await files.insert.submit({
				file_url: values.url.trim(),
				attached_to_doctype: 'BWH Video',
				attached_to_name: props.videoName,
			} as Partial<VideoFile>)
			files.reload()
		},
	})
}

function remove(file: VideoFile) {
	dialog.danger({
		title: 'Remove attachment?',
		message: `"${label(file)}" will be deleted.`,
		confirmLabel: 'Remove',
		onConfirm: async () => {
			await files.delete.submit({ name: file.name })
			files.reload()
		},
	})
}

function onFailure(error: unknown) {
	toast.error(error instanceof Error ? errorMessage(error) : 'Upload failed')
}

function validateUrl(value: string) {
	return /^https?:\/\/\S+$/.test(value.trim()) ? null : 'Enter a link that starts with http:// or https://'
}

function isLink(file: VideoFile) {
	return /^https?:\/\//.test(file.file_url)
}

function label(file: VideoFile) {
	if (!isLink(file)) return file.file_name ?? file.file_url
	const url = new URL(file.file_url)
	return `${url.hostname}${url.pathname === '/' ? '' : url.pathname}`
}

function size(file: VideoFile) {
	if (isLink(file)) return 'Link'
	const kb = file.file_size / 1024
	return kb < 1024 ? `${Math.max(1, Math.round(kb))} KB` : `${(kb / 1024).toFixed(1)} MB`
}

function fileIcon(file: VideoFile) {
	if (isLink(file)) return 'lucide-link'
	const extension = (file.file_name ?? '').split('.').pop()?.toLowerCase() ?? ''
	return ICONS[extension] ?? 'lucide-file'
}

const ICONS: Record<string, string> = {
	pdf: 'lucide-file-text',
	md: 'lucide-file-text',
	txt: 'lucide-file-text',
	png: 'lucide-image',
	jpg: 'lucide-image',
	jpeg: 'lucide-image',
	gif: 'lucide-image',
	webp: 'lucide-image',
	svg: 'lucide-image',
	mp4: 'lucide-film',
	mov: 'lucide-film',
	webm: 'lucide-film',
	mp3: 'lucide-file-audio',
	wav: 'lucide-file-audio',
	py: 'lucide-file-code',
	js: 'lucide-file-code',
	ts: 'lucide-file-code',
	vue: 'lucide-file-code',
	json: 'lucide-file-code',
	zip: 'lucide-file-archive',
}
</script>
