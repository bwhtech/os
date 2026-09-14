<template>
	<AppPageHeader title="Series">
		<template #actions>
			<Button variant="solid" theme="gray" icon-left="lucide-plus" label="New Series" @click="dialogOpen = true" />
		</template>
		<template #mobile-actions>
			<Button variant="ghost" size="md" icon="lucide-plus" aria-label="New Series" @click="dialogOpen = true" />
		</template>
	</AppPageHeader>

	<div class="mx-auto max-w-[940px] px-3 pb-10 pt-6 sm:px-5">
		<ListSkeleton v-if="series.loading && !series.data" />
		<ErrorMessage v-else-if="series.error" :message="errorMessage(series.error)" />

		<div v-else-if="!series.data?.length" class="flex flex-col items-center justify-center gap-3 py-16 text-center">
			<div class="rounded-full bg-surface-gray-2 p-3 text-ink-gray-5">
				<span class="lucide-library size-6" aria-hidden="true" />
			</div>
			<p class="text-base text-ink-gray-7">No series yet</p>
			<p class="text-sm text-ink-gray-5">Group videos that belong together, like a course or a monthly show.</p>
			<Button variant="solid" theme="gray" icon-left="lucide-plus" label="New Series" class="mt-2" @click="dialogOpen = true" />
		</div>

		<div v-else class="grid gap-3 sm:grid-cols-2">
			<RouterLink
				v-for="row in series.data"
				:key="row.name"
				:to="`/series/${row.name}`"
				class="block rounded-5 border border-outline-gray-1 p-4 hover:border-outline-gray-3"
			>
				<div class="flex items-center gap-3">
					<div class="grid size-9 shrink-0 place-content-center rounded-4 bg-surface-gray-2 text-lg">
						{{ row.emoji || '🎬' }}
					</div>
					<div class="min-w-0">
						<p class="truncate text-lg-semibold text-ink-gray-8">{{ row.title }}</p>
						<p class="mt-1 text-sm text-ink-gray-5">
							{{ row.video_count }} {{ row.video_count === 1 ? 'video' : 'videos' }}
						</p>
					</div>
				</div>
				<p v-if="row.summary" class="mt-3 line-clamp-2 text-p-sm text-ink-gray-7">{{ row.summary }}</p>
				<div class="mt-4 flex items-center gap-3">
					<Progress
						:value="row.video_count ? (row.published_count / row.video_count) * 100 : 0"
						size="sm"
						class="flex-1"
					/>
					<span class="text-xs tabular-nums text-ink-gray-5">
						{{ row.published_count }}/{{ row.video_count }} published
					</span>
				</div>
			</RouterLink>
		</div>
	</div>

	<SeriesDialog v-model:open="dialogOpen" :save="create" />
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { Button, ErrorMessage, Progress, useCall } from 'frappe-ui'
import AppPageHeader from '@/components/shell/AppPageHeader.vue'
import ListSkeleton from '@/components/list/ListSkeleton.vue'
import SeriesDialog from '@/components/videos/SeriesDialog.vue'
import { useVideoSeries } from '@/composables/useVideoSeries'
import { errorMessage } from '@/lib/errors'
import type { VideoSeries } from '@/types'

const router = useRouter()
const { series } = useVideoSeries()
const dialogOpen = ref(false)

const insert = useCall<VideoSeries, Partial<VideoSeries>>({
	url: '/api/v2/document/BWH Video Series',
	method: 'POST',
	immediate: false,
})

async function create(values: Partial<VideoSeries>) {
	const created = await insert.submit(values)
	if (created) router.push(`/series/${created.name}`)
}
</script>
