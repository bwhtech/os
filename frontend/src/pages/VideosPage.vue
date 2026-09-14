<template>
	<AppPageHeader title="Videos">
		<template #actions>
			<Button variant="solid" theme="gray" icon-left="lucide-plus" label="New Video" @click="newVideo.open()" />
		</template>
		<template #mobile-actions>
			<Button variant="ghost" size="md" icon="lucide-plus" aria-label="New Video" @click="newVideo.open()" />
		</template>
	</AppPageHeader>

	<div class="px-3 pt-5 sm:px-5" :class="{ 'pb-10': view === 'list' }">
		<div class="flex flex-wrap items-center gap-2">
			<TextInput v-model="query" placeholder="Search videos" class="w-full sm:w-60">
				<template #prefix>
					<span class="lucide-search size-4 text-ink-gray-5" aria-hidden="true" />
				</template>
			</TextInput>
			<TabButtons v-model="filter" :options="FILTERS" />
			<TabButtons v-model="view" class="ml-auto" :options="VIEWS" />
		</div>

		<ListSkeleton v-if="videos.loading && !videos.data" class="mt-5" />
		<ErrorMessage v-else-if="videos.error" class="mt-5" :message="errorMessage(videos.error)" />

		<VideoBoard
			v-else-if="view === 'board'"
			class="mt-4"
			:videos="rows"
			:statuses="statuses"
			:series-by-name="byName"
			:attachment-counts="attachmentCounts.data ?? {}"
			@move="move"
		/>

		<template v-else>
			<VideoTable v-if="rows.length" class="mt-4" :videos="rows" :series-by-name="byName" />
			<div v-else class="flex flex-col items-center justify-center gap-3 py-16 text-center">
				<div class="rounded-full bg-surface-gray-2 p-3 text-ink-gray-5">
					<span class="lucide-clapperboard size-6" aria-hidden="true" />
				</div>
				<p class="text-base text-ink-gray-7">No videos here</p>
				<p class="text-sm text-ink-gray-5">Write down an idea before you forget it.</p>
				<Button
					variant="solid"
					theme="gray"
					icon-left="lucide-plus"
					label="New Video"
					class="mt-2"
					@click="newVideo.open()"
				/>
			</div>
		</template>
	</div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { Button, ErrorMessage, TabButtons, TextInput, debounce, toast, useCall, useList } from 'frappe-ui'
import AppPageHeader from '@/components/shell/AppPageHeader.vue'
import ListSkeleton from '@/components/list/ListSkeleton.vue'
import VideoBoard from '@/components/videos/VideoBoard.vue'
import VideoTable from '@/components/videos/VideoTable.vue'
import { useNewVideo } from '@/composables/useNewVideo'
import { useVideoSeries } from '@/composables/useVideoSeries'
import { errorMessage } from '@/lib/errors'
import { onListUpdate } from '@/lib/socket'
import { IN_PROGRESS, STATUSES } from '@/lib/videos'
import type { Video, VideoStatus } from '@/types'

type Filter = 'in-progress' | 'published' | 'all'

const FILTERS = [
	{ label: 'In Progress', value: 'in-progress' },
	{ label: 'Published', value: 'published' },
	{ label: 'All', value: 'all' },
]

const VIEWS = [
	{ label: 'Board', value: 'board', icon: 'lucide-columns-3' },
	{ label: 'List', value: 'list', icon: 'lucide-list' },
]

const filter = ref<Filter>('in-progress')
const view = ref<'board' | 'list'>('board')
const query = ref('')

const newVideo = useNewVideo()
const { byName } = useVideoSeries()

const videos = useList<Video>({
	doctype: 'BWH Video',
	fields: ['name', 'title', 'status', 'series', 'position', 'publish_on', 'modified'],
	orderBy: 'modified desc',
	// One person's pipeline. Filtering on the client keeps the board and the tabs instant.
	limit: 1000,
})

const attachmentCounts = useCall<Record<string, number>>({
	url: '/api/v2/method/bwh_os.videos.api.get_attachment_counts',
})

onListUpdate(['BWH Video', 'File'], debounce(() => {
	videos.reload()
	attachmentCounts.reload()
}, 300))

/** The board shows only the columns the filter keeps, so In Progress has no empty Published column. */
const statuses = computed<VideoStatus[]>(() => {
	if (filter.value === 'published') return ['Published']
	if (filter.value === 'in-progress') return IN_PROGRESS
	return STATUSES
})

const rows = computed(() => {
	const text = query.value.trim().toLowerCase()
	return (videos.data ?? []).filter(
		(video) => statuses.value.includes(video.status) && video.title.toLowerCase().includes(text),
	)
})

async function move(picked: Video[], status: VideoStatus) {
	const moving = picked.filter((video) => video.status !== status)
	if (!moving.length) return
	// Move the cards at once. The saves confirm it, or the reload puts them back.
	moving.forEach((video) => videos.updateRow({ ...video, status }))
	try {
		await Promise.all(moving.map((video) => videos.setValue.submit({ name: video.name, status })))
		toast.success(moving.length > 1 ? `${moving.length} videos moved to ${status}` : `Moved to ${status}`)
	} catch (error) {
		toast.error(errorMessage(error as Error))
		videos.reload()
	}
}
</script>
