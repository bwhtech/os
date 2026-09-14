<template>
	<div class="grid grid-cols-[6rem_minmax(0,1fr)] items-center gap-x-3 gap-y-3 text-sm">
		<span class="text-ink-gray-6">Status</span>
		<div>
			<VideoStatusDropdown :model-value="video.status" @update:model-value="save({ status: $event })" />
		</div>

		<span class="text-ink-gray-6">Series</span>
		<Select
			:model-value="video.series ? String(video.series) : ''"
			:options="seriesOptions"
			@update:model-value="save({ series: $event ? String($event) : null })"
		/>

		<span class="text-ink-gray-6">Publish on</span>
		<DatePicker
			:model-value="video.publish_on ?? ''"
			placeholder="Not scheduled"
			@update:model-value="save({ publish_on: $event || null })"
		/>

		<span class="text-ink-gray-6">YouTube</span>
		<TextInput
			v-model="youtubeUrl"
			type="url"
			placeholder="https://youtu.be/…"
			@blur="saveYoutubeUrl"
			@keydown.enter="saveYoutubeUrl"
		/>
	</div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { DatePicker, Select, TextInput } from 'frappe-ui'
import VideoStatusDropdown from '@/components/videos/VideoStatusDropdown.vue'
import { useVideoSeries } from '@/composables/useVideoSeries'
import type { Video } from '@/types'

const props = defineProps<{ video: Video }>()

const emit = defineEmits<{ save: [values: Partial<Video>] }>()

const { series } = useVideoSeries()

const seriesOptions = computed(() => [
	{ label: 'None', value: '' },
	...(series.data ?? []).map((row) => ({ label: `${row.emoji ?? ''} ${row.title}`.trim(), value: String(row.name) })),
])

const youtubeUrl = ref(props.video.youtube_url ?? '')
watch(
	() => props.video.youtube_url,
	(value) => {
		youtubeUrl.value = value ?? ''
	},
)

function saveYoutubeUrl() {
	const value = youtubeUrl.value.trim() || null
	if (value !== (props.video.youtube_url || null)) save({ youtube_url: value })
}

function save(values: Partial<Video>) {
	emit('save', values)
}
</script>
