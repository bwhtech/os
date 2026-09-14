<template>
	<div
		class="rounded-4 border bg-surface-elevation-1 p-3 transition-colors"
		:class="[
			selected
				? 'border-outline-gray-4 ring-2 ring-outline-gray-3'
				: 'border-outline-gray-1 hover:border-outline-gray-2',
			dragging ? 'opacity-40' : '',
			preview ? 'shadow-2xl' : 'cursor-grab active:cursor-grabbing',
		]"
		:role="preview ? undefined : 'button'"
		:tabindex="preview ? undefined : 0"
		draggable="false"
		@keydown.enter.prevent="emit('open', video)"
		@keydown.space.prevent="emit('open', video)"
	>
		<p class="text-sm font-medium leading-snug text-ink-gray-8">{{ video.title }}</p>

		<p v-if="series" class="mt-2 truncate text-xs text-ink-gray-5">
			{{ series.emoji }} {{ series.title }}
			<span class="tabular-nums text-ink-gray-4">#{{ video.position }}</span>
		</p>

		<div
			v-if="video.publish_on || attachments"
			class="mt-2 flex items-center gap-3 text-xs text-ink-gray-5"
		>
			<span v-if="video.publish_on" class="flex items-center gap-1">
				<span class="lucide-calendar size-3 shrink-0" aria-hidden="true" />
				{{ dayjs(video.publish_on).format('D MMM') }}
			</span>
			<span v-if="attachments" class="flex items-center gap-1">
				<span class="lucide-paperclip size-3 shrink-0" aria-hidden="true" />
				{{ attachments }}
			</span>
		</div>
	</div>
</template>

<script setup lang="ts">
import { dayjs } from 'frappe-ui'
import type { Video, VideoSeriesSummary } from '@/types'

withDefaults(
	defineProps<{
		video: Video
		series?: VideoSeriesSummary | null
		attachments?: number
		/** Part of a Cmd/Ctrl-click multi-selection. */
		selected?: boolean
		/** Being dragged right now, so the card left behind is dimmed. */
		dragging?: boolean
		/** Rendered inside the drag preview: no cursor, no focus. */
		preview?: boolean
	}>(),
	{ series: null, attachments: 0, selected: false, dragging: false, preview: false },
)

const emit = defineEmits<{ open: [video: Video] }>()
</script>
