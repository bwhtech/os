<template>
	<div class="flex items-center gap-2">
		<Combobox
			:model-value="modelValue ?? ''"
			:options="options"
			:disabled="disabled"
			placeholder="No video"
			empty-text="No video by that name"
			class="min-w-0 flex-1"
			@update:model-value="pick"
		/>
		<!-- The video is the reason the post exists, so it stays one click away. -->
		<Button
			v-if="picked"
			icon="lucide-external-link"
			aria-label="Open the video"
			:route="videoRoute(picked)"
		/>
	</div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { Button, Combobox, dayjs, useList } from 'frappe-ui'
import type { ComboboxOptionValue } from 'frappe-ui'
import { videoRoute } from '@/lib/videos'
import type { Video } from '@/types'

/** The video this post promotes. Both land on the same calendar, so the post finds its video. */
const props = defineProps<{ modelValue: string | null; disabled?: boolean }>()

const emit = defineEmits<{ 'update:modelValue': [video: string | null] }>()

const videos = useList<Video>({
	doctype: 'BWH Video',
	fields: ['name', 'title', 'status', 'series', 'publish_on'],
	orderBy: 'modified desc',
	limit: 200,
})

const picked = computed(() => (videos.data ?? []).find((video) => String(video.name) === props.modelValue))

const options = computed(() => [
	{ label: 'No video', value: '' },
	...(videos.data ?? []).map((video) => ({
		label: video.title,
		value: String(video.name),
		description: video.publish_on
			? `${video.status} · ${dayjs(video.publish_on).format('D MMM')}`
			: video.status,
	})),
])

function pick(value?: ComboboxOptionValue | null) {
	emit('update:modelValue', value ? String(value) : null)
}
</script>
