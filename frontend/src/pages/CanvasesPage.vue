<template>
	<AppPageHeader title="Canvas">
		<template #actions>
			<Button variant="solid" theme="gray" icon-left="lucide-plus" label="New Canvas" :loading="creating" @click="create" />
		</template>
		<template #mobile-actions>
			<Button variant="ghost" size="md" icon="lucide-plus" aria-label="New Canvas" :loading="creating" @click="create" />
		</template>
	</AppPageHeader>

	<div class="mx-auto max-w-[940px] px-3 pb-10 pt-5 sm:px-5">
		<div class="flex flex-wrap items-center gap-2">
			<TextInput v-model="query" placeholder="Search canvases" class="w-full sm:w-60">
				<template #prefix>
					<span class="lucide-search size-4 text-ink-gray-5" aria-hidden="true" />
				</template>
			</TextInput>
			<TabButtons v-model="filter" :options="FILTERS" />
		</div>

		<ListSkeleton v-if="canvases.loading && !canvases.data" class="mt-5" />
		<ErrorMessage v-else-if="canvases.error" class="mt-5" :message="errorMessage(canvases.error)" />

		<div v-else-if="!rows.length" class="flex flex-col items-center justify-center gap-3 py-16 text-center">
			<div class="rounded-full bg-surface-gray-2 p-3 text-ink-gray-5">
				<span class="lucide-pen-tool size-6" aria-hidden="true" />
			</div>
			<p class="text-base text-ink-gray-7">No canvases here</p>
			<p class="text-sm text-ink-gray-5">Sketch an idea, a diagram, or the board for a video.</p>
			<Button variant="solid" theme="gray" icon-left="lucide-plus" label="New Canvas" class="mt-2" @click="create" />
		</div>

		<div v-else class="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
			<RouterLink
				v-for="row in rows"
				:key="row.name"
				:to="`/canvas/${row.name}`"
				class="block overflow-hidden rounded-5 border border-outline-gray-1 hover:border-outline-gray-3"
			>
				<div class="canvas-thumbnail grid aspect-video place-items-center border-b border-outline-gray-1 bg-white">
					<img v-if="row.thumbnail" :src="row.thumbnail" alt="" class="size-full object-contain p-3" />
					<span v-else class="lucide-pen-tool size-5 text-gray-400" aria-hidden="true" />
				</div>
				<div class="p-4">
					<p class="truncate text-lg-semibold text-ink-gray-8">{{ row.title }}</p>
					<p class="mt-1 flex items-center gap-1.5 truncate text-sm text-ink-gray-5">
						<span :class="row.video ? 'lucide-clapperboard' : 'lucide-pen-tool'" class="size-3.5 shrink-0" aria-hidden="true" />
						<span class="truncate">{{ row.video ? row.video_title : 'Scratch' }}</span>
					</p>
					<p class="mt-3 text-xs text-ink-gray-5">Edited {{ dayjs(row.modified).fromNow() }}</p>
				</div>
			</RouterLink>
		</div>
	</div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import { Button, ErrorMessage, TabButtons, TextInput, dayjs, debounce, toast, useList } from 'frappe-ui'
import AppPageHeader from '@/components/shell/AppPageHeader.vue'
import ListSkeleton from '@/components/list/ListSkeleton.vue'
import { errorMessage } from '@/lib/errors'
import { onListUpdate } from '@/lib/socket'
import type { Canvas } from '@/types'

type Filter = 'all' | 'scratch' | 'videos'

const FILTERS = [
	{ label: 'All', value: 'all' },
	{ label: 'Scratch', value: 'scratch' },
	{ label: 'Videos', value: 'videos' },
]

type CanvasRow = Omit<Canvas, 'scene'> & { video_title: string | null }

const router = useRouter()
const filter = ref<Filter>('all')
const query = ref('')
const creating = ref(false)

const canvases = useList<CanvasRow>({
	doctype: 'BWH Canvas',
	// Not the scene: it can be large, and the cards do not draw it.
	fields: ['name', 'title', 'video', 'video.title as video_title', 'thumbnail', 'modified'],
	orderBy: 'modified desc',
	// Filtering on the client keeps the tabs and the search instant.
	limit: 1000,
})

onListUpdate(['BWH Canvas'], debounce(() => canvases.reload(), 300))

const rows = computed(() => {
	const text = query.value.trim().toLowerCase()
	return (canvases.data ?? []).filter((row) => {
		if (filter.value === 'scratch' && row.video) return false
		if (filter.value === 'videos' && !row.video) return false
		return row.title.toLowerCase().includes(text)
	})
})

/** A new canvas opens at once. Name it later from its menu. */
async function create() {
	creating.value = true
	try {
		const created = await canvases.insert.submit({ title: 'Untitled canvas' })
		if (created) router.push(`/canvas/${created.name}`)
	} catch (error) {
		toast.error(errorMessage(error as Error))
	} finally {
		creating.value = false
	}
}
</script>

<style scoped>
/* Thumbnails are drawn light. Dark mode inverts them the way Excalidraw draws its own dark mode. */
:root[data-theme='dark'] .canvas-thumbnail {
	filter: invert(93%) hue-rotate(180deg);
}
</style>
