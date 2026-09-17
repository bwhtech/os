<template>
	<div v-if="media.length || !disabled" class="space-y-2">
		<div class="flex flex-wrap items-center gap-2">
			<figure v-for="(item, index) in media" :key="item.file_url" class="group relative">
				<!-- Private files, so the tile is the same URL the platform will be handed. -->
				<video
					v-if="item.kind === 'video'"
					:src="item.file_url"
					class="size-16 rounded-4 border border-outline-gray-2 bg-surface-gray-2 object-cover"
					preload="metadata"
					muted
				/>
				<img
					v-else
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
					:aria-label="`Remove ${item.kind} ${index + 1}`"
					@click="remove(index)"
				/>
			</figure>

			<Button
				v-if="!disabled && room"
				variant="ghost"
				size="sm"
				icon-left="lucide-image-plus"
				:label="uploading ? `Uploading ${percent}%` : label"
				:loading="uploading"
				@click="pick"
			/>

			<input ref="input" type="file" class="hidden" :accept="ACCEPT" @change="add" />
		</div>

		<!-- A video takes long enough that a share of the file is worth showing. -->
		<Progress v-if="uploading" :value="percent" size="sm" />
	</div>
</template>

<script setup lang="ts">
import { computed, ref, useTemplateRef } from 'vue'
import { Button, Progress, toast } from 'frappe-ui'
import { chunkedUpload } from '@/lib/chunkedUpload'
import { errorMessage } from '@/lib/errors'
import type { SocialMedia } from '@/types'

/**
 * The media of one part. A file is uploaded against the post, so it has an owner from
 * the start and goes when the post goes; the part keeps the URL and what it is.
 *
 * Every file goes up in chunks, video included: one road, and a progress bar that is
 * telling the truth about a 200 MB upload.
 */
const props = withDefaults(
	defineProps<{
		/** The post the files attach to */
		postName: string
		/** How many images the strictest platform picked takes in one part */
		max?: number
		disabled?: boolean
	}>(),
	{ max: 4 },
)

const media = defineModel<SocialMedia[]>({ required: true })

const IMAGE_TYPES = ['image/png', 'image/jpeg', 'image/gif', 'image/webp']
const VIDEO_TYPES = ['video/mp4', 'video/quicktime', 'video/webm']
const ACCEPT = [...IMAGE_TYPES, ...VIDEO_TYPES].join(',')

const input = useTemplateRef<HTMLInputElement>('input')
const uploading = ref(false)
const done = ref(0)

const percent = computed(() => Math.round(done.value * 100))
const video = computed(() => media.value.find((item) => item.kind === 'video'))

/** A video goes on its own, whatever the platform allows for images. */
const room = computed(() => !video.value && media.value.length < props.max)

const label = computed(() => (media.value.length ? 'Add another' : 'Add an image or video'))

function pick() {
	input.value?.click()
}

async function add(event: Event) {
	const field = event.target as HTMLInputElement
	const file = field.files?.[0]
	// The same file picked twice has to fire `change` again, so the field is cleared.
	field.value = ''
	if (!file) return

	const kind = VIDEO_TYPES.includes(file.type) ? 'video' : 'image'
	const problem = refuse(file, kind)
	if (problem) {
		toast.error(problem)
		return
	}

	uploading.value = true
	done.value = 0
	try {
		const uploaded = await chunkedUpload(file, {
			doctype: 'Social Post',
			docname: props.postName,
			onProgress: (fraction) => (done.value = fraction),
		})
		media.value = [...media.value, { file_url: uploaded.file_url, kind }]
	} catch (error) {
		toast.error(errorMessage(error as Error))
	} finally {
		uploading.value = false
	}
}

function remove(index: number) {
	// The `File` stays on the post: it costs a row, and a post that is deleted takes it.
	media.value = media.value.filter((_, at) => at !== index)
}

/** Why this file cannot join this part. The server checks the same things again. */
function refuse(file: File, kind: SocialMedia['kind']): string | null {
	if (kind === 'image' && !IMAGE_TYPES.includes(file.type)) {
		return 'Pick a PNG, JPEG, GIF or WebP image, or an MP4, MOV or WebM video'
	}
	if (kind === 'video' && media.value.length) return 'A video goes on its own, without images'
	return null
}
</script>
