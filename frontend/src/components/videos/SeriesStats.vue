<template>
	<div
		class="grid grid-cols-1 divide-y divide-outline-gray-2 rounded-5 border border-outline-gray-1 sm:grid-cols-3 sm:divide-x sm:divide-y-0"
	>
		<div class="p-4">
			<p class="text-sm text-ink-gray-5">Published</p>
			<p class="mt-1.5 text-2xl tabular-nums text-ink-gray-9">{{ published }} / {{ videos.length }}</p>
			<Progress :value="videos.length ? (published / videos.length) * 100 : 0" size="sm" class="mt-3" />
		</div>

		<div class="min-w-0 p-4">
			<p class="text-sm text-ink-gray-5">Up next</p>
			<template v-if="upNext">
				<RouterLink
					:to="videoRoute(upNext)"
					class="mt-1.5 block truncate text-base text-ink-gray-8 hover:underline"
				>
					#{{ upNext.position }} {{ upNext.title }}
				</RouterLink>
				<p class="mt-1.5 text-sm text-ink-gray-5">
					{{ upNext.status }}<template v-if="upNext.publish_on"> · {{ dayjs(upNext.publish_on).format('D MMM') }}</template>
				</p>
			</template>
			<p v-else class="mt-1.5 text-base text-ink-gray-8">{{ videos.length ? 'All published' : 'Nothing yet' }}</p>
		</div>

		<div class="p-4">
			<p class="text-sm text-ink-gray-5">Pipeline</p>
			<div class="mt-2 flex flex-wrap gap-x-3 gap-y-1.5">
				<span v-for="row in pipeline" :key="row.status" class="flex items-center gap-1.5 text-sm text-ink-gray-7">
					<span :class="['size-1.5 rounded-full', statusDot(row.status)]" aria-hidden="true" />
					{{ row.count }} {{ row.status }}
				</span>
				<span v-if="!pipeline.length" class="text-sm text-ink-gray-5">—</span>
			</div>
		</div>
	</div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { Progress, dayjs } from 'frappe-ui'
import type { SeriesVideo } from '@/composables/useSeriesVideos'
import { STATUSES, statusDot, videoRoute } from '@/lib/videos'

const props = defineProps<{ videos: SeriesVideo[]; published: number }>()

/** The first video in series order that is not out yet. */
const upNext = computed(() => props.videos.find((video) => video.status !== 'Published') ?? null)

const pipeline = computed(() =>
	STATUSES.map((status) => ({
		status,
		count: props.videos.filter((video) => video.status === status).length,
	})).filter((row) => row.count),
)
</script>
