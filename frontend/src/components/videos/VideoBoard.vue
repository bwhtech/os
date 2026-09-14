<template>
	<div ref="root" class="relative flex min-h-0 flex-col" :style="{ height }">
		<ScrollArea
			ref="scroller"
			orientation="horizontal"
			class="min-h-0 flex-1"
			viewport-class="h-full pb-3 [&>div]:!block [&>div]:h-full"
			:style="{ maskImage: mask, WebkitMaskImage: mask }"
		>
			<div class="flex h-full items-stretch gap-3">
				<section
					v-for="status in statuses"
					:key="status"
					:ref="(el) => setColumn(status, el)"
					class="flex h-full min-h-0 min-w-56 flex-1 basis-64 flex-col rounded-4 border p-2 transition-colors"
					:class="
						over === status
							? 'border-outline-gray-3 bg-surface-gray-2'
							: 'border-transparent bg-surface-gray-1'
					"
				>
					<header class="flex shrink-0 items-center justify-between px-1 pb-2">
						<span class="flex items-center gap-2 text-sm font-medium text-ink-gray-7">
							<span :class="['size-1.5 rounded-full', statusDot(status)]" aria-hidden="true" />
							{{ status }}
						</span>
						<Badge variant="subtle" theme="gray" :label="String(columns[status].length)" />
					</header>

					<!-- Each column scrolls on its own, so the board never grows taller than the screen. -->
					<div class="-mx-1 min-h-0 flex-1 overflow-y-auto px-1">
						<div class="flex flex-col gap-2 pb-1">
							<VideoBoardCard
								v-for="video in columns[status]"
								:key="video.name"
								:video="video"
								:series="seriesOf(video)"
								:attachments="attachmentCounts[video.name] ?? 0"
								:selected="isSelected(video.name)"
								:dragging="isDragging(video.name)"
								@pointerdown="press($event, video)"
								@click="open($event, video)"
								@open="router.push(videoRoute(video))"
							/>
						</div>
						<p v-if="!columns[status].length" class="px-1 py-6 text-center text-xs text-ink-gray-5">
							No videos
						</p>
					</div>
				</section>
			</div>
		</ScrollArea>

		<p
			v-if="selection.size > 1 && !dragging"
			class="pointer-events-none absolute bottom-4 left-1/2 -translate-x-1/2 rounded-full bg-surface-gray-7 px-3 py-1 text-xs text-ink-white shadow-lg"
		>
			{{ selection.size }} selected. Drag them together, or press Esc.
		</p>

		<VideoBoardDragPreview
			v-if="dragging"
			:videos="dragging"
			:series="seriesOf(dragging[0])"
			:point="point"
			:offset="offset"
			:width="cardWidth"
		/>
	</div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, type ComponentPublicInstance } from 'vue'
import { useRouter } from 'vue-router'
import { Badge, ScrollArea } from 'frappe-ui'
import VideoBoardCard from '@/components/videos/VideoBoardCard.vue'
import VideoBoardDragPreview from '@/components/videos/VideoBoardDragPreview.vue'
import { useBoardDrag } from '@/composables/useBoardDrag'
import { useFillViewport } from '@/composables/useFillViewport'
import { useScrollFade } from '@/composables/useScrollFade'
import { statusDot, videoRoute } from '@/lib/videos'
import type { Video, VideoSeriesSummary, VideoStatus } from '@/types'

const props = defineProps<{
	videos: Video[]
	/** One column each, in this order. */
	statuses: VideoStatus[]
	seriesByName: Record<string, VideoSeriesSummary>
	attachmentCounts: Record<string, number>
}>()

const emit = defineEmits<{ move: [videos: Video[], status: VideoStatus] }>()

const router = useRouter()

const root = ref<HTMLElement | null>(null)
const { height } = useFillViewport(root)

/** `ScrollArea` hands out its viewport through a plain getter, so read it once mounted. */
const scroller = ref<{ viewportElement: HTMLElement | null } | null>(null)
const viewport = ref<HTMLElement | null>(null)
const { mask } = useScrollFade(viewport, 'horizontal')
onMounted(() => {
	viewport.value = scroller.value?.viewportElement ?? null
})

const columns = computed(() => {
	const byStatus = Object.fromEntries(props.statuses.map((status) => [status, [] as Video[]]))
	for (const video of props.videos) byStatus[video.status]?.push(video)
	return byStatus as Record<VideoStatus, Video[]>
})

const columnEls = ref<Record<string, HTMLElement | null>>({})

function setColumn(status: VideoStatus, el: Element | ComponentPublicInstance | null) {
	columnEls.value[status] = (el as HTMLElement | null) ?? null
}

/** Board order, so a multi-card drag stacks in the order the columns read. */
const ordered = computed(() => props.statuses.flatMap((status) => columns.value[status]))

const {
	selection,
	dragging,
	over,
	point,
	offset,
	width: cardWidth,
	isSelected,
	isDragging,
	press,
	click,
} = useBoardDrag<Video>({
	columns: () => columnEls.value,
	scroller: () => viewport.value,
	cards: () => ordered.value,
	onDrop: (picked, status) => emit('move', picked, status as VideoStatus),
})

function seriesOf(video: Video) {
	return video.series ? (props.seriesByName[video.series] ?? null) : null
}

/** A plain click opens the card; a modifier-click only changes the selection. */
function open(event: MouseEvent, video: Video) {
	if (click(event, video)) router.push(videoRoute(video))
}
</script>
