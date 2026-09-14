<template>
	<AppPageHeader :breadcrumbs="breadcrumbs">
		<template #actions>
			<template v-if="seriesVideos.length">
				<Button
					variant="ghost"
					icon="lucide-chevron-left"
					aria-label="Previous video"
					tooltip="Previous"
					:disabled="!previous"
					:route="previous ? videoRoute(previous) : undefined"
				/>
				<Button
					variant="ghost"
					icon="lucide-chevron-right"
					aria-label="Next video"
					tooltip="Next"
					:disabled="!next"
					:route="next ? videoRoute(next) : undefined"
				/>
			</template>
			<Dropdown :options="menu">
				<Button variant="ghost" icon="lucide-ellipsis" aria-label="More actions" />
			</Dropdown>
		</template>
	</AppPageHeader>

	<div v-if="!video.doc" class="px-3 py-6 sm:px-5">
		<ErrorMessage v-if="video.error" :message="errorMessage(video.error)" />
		<DetailSkeleton v-else class="mx-auto max-w-[770px]" />
	</div>

	<!-- Fills the space below the header, so the border of the details panel runs top to bottom. -->
	<div v-else class="flex min-h-[calc(100dvh-3rem)]">
		<div class="min-w-0 flex-1 px-3 sm:px-5">
			<div class="mx-auto w-full max-w-[770px] pb-40 pt-6">
				<p v-if="series" class="text-sm text-ink-gray-5">
					{{ series.emoji }} {{ series.title }} · #{{ video.doc.position }}
				</p>
				<textarea
					ref="titleInput"
					v-model="title"
					rows="1"
					class="mt-1.5 block w-full resize-none overflow-hidden border-0 bg-transparent p-0 text-3xl font-semibold text-ink-gray-9 placeholder:text-ink-gray-4 focus:ring-0"
					placeholder="Untitled video"
					aria-label="Title"
					@input="saveTitle"
					@keydown.enter.prevent
				/>

				<!-- On narrow screens the details sit above the writing instead of beside it. -->
				<div class="mt-5 space-y-6 border-b border-outline-gray-1 pb-6 xl:hidden">
					<VideoDetails :video="video.doc" @save="save" />
				</div>

				<VideoWriting :key="video.doc.name" class="mt-6" :video="video.doc" :save="save" />

				<VideoAttachments class="mt-8 xl:hidden" :video-name="videoId" />
			</div>
		</div>

		<aside class="hidden w-[20rem] shrink-0 border-l border-outline-gray-1 xl:block">
			<!-- Stays in view while the notes scroll. -->
			<div class="sticky top-0 space-y-6 px-5 py-6">
				<VideoDetails :video="video.doc" @save="save" />
				<VideoAttachments class="border-t border-outline-gray-1 pt-6" :video-name="videoId" />
				<p class="border-t border-outline-gray-1 pt-6 text-xs text-ink-gray-5">
					Edited {{ dayjs(video.doc.modified).fromNow() }}
				</p>
			</div>
		</aside>
	</div>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { Button, Dropdown, ErrorMessage, dayjs, debounce, dialog, toast, useDoc, useList } from 'frappe-ui'
import AppPageHeader from '@/components/shell/AppPageHeader.vue'
import DetailSkeleton from '@/components/stats/DetailSkeleton.vue'
import VideoAttachments from '@/components/videos/VideoAttachments.vue'
import VideoDetails from '@/components/videos/VideoDetails.vue'
import VideoWriting from '@/components/videos/VideoWriting.vue'
import { useAutosave } from '@/composables/useAutosave'
import { useVideoSeries } from '@/composables/useVideoSeries'
import { errorMessage } from '@/lib/errors'
import { onListUpdate } from '@/lib/socket'
import { videoRoute } from '@/lib/videos'
import type { Video } from '@/types'

const props = defineProps<{ videoId: string; seriesId?: string }>()

const router = useRouter()
const { byName } = useVideoSeries()

const video = useDoc<Video>({ doctype: 'BWH Video', name: computed(() => props.videoId) })

const series = computed(() => (video.doc?.series ? byName.value[video.doc.series] : null))

const seriesVideos = useSeriesVideos()
const index = computed(() => seriesVideos.value.findIndex((row) => String(row.name) === props.videoId))
const previous = computed(() => (index.value > 0 ? seriesVideos.value[index.value - 1] : null))
const next = computed(() => (index.value >= 0 ? (seriesVideos.value[index.value + 1] ?? null) : null))

const breadcrumbs = computed(() => {
	const current = { label: video.doc?.title || 'Untitled video' }
	if (!series.value) return [{ label: 'Videos', route: '/videos' }, current]
	return [{ label: series.value.title, route: `/series/${series.value.name}` }, current]
})

const menu = [{ label: 'Delete', icon: 'lucide-trash-2', theme: 'red' as const, onClick: remove }]

async function save(values: Partial<Video>) {
	try {
		await video.setValue.submit(values)
	} catch (error) {
		toast.error(errorMessage(error as Error))
		throw error
	}
}

const title = ref('')
const titleInput = ref<HTMLTextAreaElement | null>(null)
const titleSave = useAutosave<Video>(save)

function saveTitle() {
	titleSave.queue({ title: title.value.trim() || 'Untitled video' })
}

// Load the title once. Our own saves come back and must not reset what is being typed.
watch(
	() => video.doc?.name,
	() => {
		title.value = video.doc?.title ?? ''
	},
	{ immediate: true },
)

// A textarea, so a long title wraps. It grows to fit, because CSS `field-sizing` is not in every browser.
watch([title, titleInput], () => nextTick(fitTitle))
onMounted(() => window.addEventListener('resize', fitTitle))
onBeforeUnmount(() => window.removeEventListener('resize', fitTitle))

function fitTitle() {
	const el = titleInput.value
	if (!el) return
	el.style.height = 'auto'
	el.style.height = `${el.scrollHeight}px`
}

// A video that joins or leaves a series moves between the two URLs, so the sidebar follows it.
watch(
	() => video.doc && videoRoute(video.doc),
	(route) => {
		if (route && route !== router.currentRoute.value.path) router.replace(route)
	},
)

function remove() {
	dialog.danger({
		title: 'Delete this video?',
		message: 'Its research, script, description and attachments are deleted too.',
		confirmLabel: 'Delete',
		onConfirm: async () => {
			const back = series.value ? `/series/${series.value.name}` : '/videos'
			await video.delete.submit()
			toast.success('Video deleted')
			router.push(back)
		},
	})
}

/** The other videos of the series, for the previous and next buttons. */
function useSeriesVideos() {
	const list = useList<Pick<Video, 'name' | 'title' | 'series' | 'position'>>({
		doctype: 'BWH Video',
		fields: ['name', 'title', 'series', 'position'],
		filters: () => ({ series: props.seriesId ?? '' }),
		orderBy: 'position asc',
		limit: 500,
		immediate: Boolean(props.seriesId),
	})
	onListUpdate(['BWH Video'], debounce(() => props.seriesId && list.reload(), 300))
	return computed(() => (props.seriesId ? (list.data ?? []) : []))
}
</script>
