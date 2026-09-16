<template>
	<Sidebar width="14rem">
		<div class="shrink-0 px-2 pt-2">
			<Button variant="ghost" size="sm" icon-left="lucide-arrow-left" label="BWH OS" route="/series" />
			<div class="flex items-start gap-2 px-1.5 pb-2 pt-3">
				<div class="grid size-8 shrink-0 place-content-center rounded-4 bg-surface-gray-2 text-base">
					{{ series.doc?.emoji || '🎬' }}
				</div>
				<div class="min-w-0">
					<p class="truncate text-base-semibold text-ink-gray-8">{{ series.doc?.title ?? '…' }}</p>
					<p class="mt-1 text-xs text-ink-gray-5">{{ published }}/{{ videos.length }} published</p>
				</div>
			</div>
		</div>

		<ScrollArea class="min-h-0 flex-1 px-1">
			<SidebarSection>
				<SidebarItem
					icon="lucide-layout-list"
					label="Overview"
					:route="`/series/${seriesId}`"
					:active="route.path === `/series/${seriesId}`"
				/>
			</SidebarSection>

			<SidebarSection label="Videos">
				<div
					v-for="video in videos"
					:key="video.name"
					draggable="true"
					class="rounded-4"
					:class="{ 'ring-1 ring-outline-gray-4': overName === video.name && dragName !== video.name }"
					@dragstart="startDrag($event, video)"
					@dragover.prevent="overName = video.name"
					@dragleave="overName = null"
					@drop.prevent="drop(video)"
					@dragend="dragName = overName = null"
				>
					<SidebarItem
						:label="video.title"
						:route="`/series/${seriesId}/videos/${video.name}`"
						:active="String(route.params.videoId) === String(video.name)"
					>
						<template #prefix>
							<span class="w-4 text-right text-xs tabular-nums text-ink-gray-4">{{ video.position }}</span>
						</template>
						<template #suffix>
							<Tooltip :text="video.status">
								<span :class="['mr-1 size-1.5 shrink-0 rounded-full', statusDot(video.status)]" />
							</Tooltip>
						</template>
					</SidebarItem>
				</div>
				<SidebarItem icon="lucide-plus" label="Add Video" @click="newVideo.open(seriesId)" />
			</SidebarSection>
		</ScrollArea>

		<p v-if="videos.length > 1" class="shrink-0 px-3 pb-3 text-xs text-ink-gray-4">Drag to reorder</p>
	</Sidebar>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRoute } from 'vue-router'
import { Button, ScrollArea, Sidebar, SidebarItem, SidebarSection, Tooltip, useDoc } from 'frappe-ui'
import { useNewVideo } from '@/composables/useNewVideo'
import { useSeriesVideos, type SeriesVideo } from '@/composables/useSeriesVideos'
import { statusDot } from '@/lib/videos'
import type { VideoSeries } from '@/types'

const props = defineProps<{ seriesId: string }>()

const route = useRoute()
const newVideo = useNewVideo()

const series = useDoc<VideoSeries>({ doctype: 'BWH Video Series', name: () => props.seriesId })
const { videos, published, move } = useSeriesVideos(() => props.seriesId)

const dragName = ref<string | null>(null)
const overName = ref<string | null>(null)

function startDrag(event: DragEvent, video: SeriesVideo) {
	dragName.value = video.name
	// Firefox starts a drag only when the transfer carries data.
	event.dataTransfer?.setData('text/plain', video.title)
}

function drop(target: SeriesVideo) {
	const video = videos.value.find((row) => row.name === dragName.value)
	dragName.value = overName.value = null
	if (video) move(video, target)
}
</script>
