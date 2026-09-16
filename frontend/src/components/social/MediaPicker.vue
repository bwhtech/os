<template>
	<div v-if="media.length || !disabled" class="flex flex-wrap items-center gap-2">
		<figure v-for="(item, index) in media" :key="item.file_url" class="group relative">
			<!-- Private files, so the tile is the same URL the platform will be handed. -->
			<img
				:src="item.file_url"
				alt=""
				class="size-16 rounded-4 border border-outline-gray-2 object-cover"
			/>
			<Button
				v-if="!disabled"
				class="absolute -right-2 -top-2 opacity-0 transition group-hover:opacity-100 focus:opacity-100"
				variant="subtle"
				size="sm"
				icon="lucide-x"
				:aria-label="`Remove image ${index + 1}`"
				@click="remove(index)"
			/>
		</figure>

		<FileUploader
			v-if="!disabled && media.length < max"
			private
			:file-types="IMAGE_TYPES"
			doctype="Social Post"
			:docname="postName"
			:validate-file="onlyImages"
			@success="add"
			@failure="fail"
		>
			<template #default="{ uploading, progress, openFileSelector }">
				<Button
					variant="ghost"
					size="sm"
					icon-left="lucide-image-plus"
					:label="uploading ? `Uploading ${progress}%` : label"
					:loading="uploading"
					@click="openFileSelector"
				/>
			</template>
		</FileUploader>
	</div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { Button, FileUploader, toast } from 'frappe-ui'
import { errorMessage } from '@/lib/errors'
import type { SocialMedia } from '@/types'

/**
 * The images of one part. A file is uploaded against the post, so it has an owner from
 * the start and goes when the post goes; the part keeps only the URL and what it is.
 */
const props = withDefaults(
	defineProps<{
		/** The post the files attach to */
		postName: string
		/** What the strictest platform picked takes in one part */
		max?: number
		disabled?: boolean
	}>(),
	{ max: 4 },
)

const media = defineModel<SocialMedia[]>({ required: true })

const IMAGE_TYPES = ['image/png', 'image/jpeg', 'image/gif', 'image/webp']

const label = computed(() => (media.value.length ? 'Add another' : 'Add an image'))

function add(file: { file_url: string }) {
	media.value = [...media.value, { file_url: file.file_url, kind: 'image' }]
}

function remove(index: number) {
	// The `File` stays on the post: it costs a row, and a post that is deleted takes it.
	media.value = media.value.filter((_, at) => at !== index)
}

function onlyImages(file: File): string | null {
	return IMAGE_TYPES.includes(file.type) ? null : 'Pick a PNG, JPEG, GIF or WebP image'
}

function fail(error: unknown) {
	toast.error(error instanceof Error ? errorMessage(error) : 'Upload failed')
}
</script>
