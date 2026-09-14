<template>
	<AppPageHeader :breadcrumbs="[{ label: 'Series', route: '/series' }, { label: series.doc?.title ?? '…' }]">
		<template #actions>
			<Dropdown :options="menu">
				<Button variant="ghost" icon="lucide-ellipsis" aria-label="More actions" />
			</Dropdown>
			<Button variant="solid" theme="gray" icon-left="lucide-plus" label="Add Video" @click="newVideo.open(seriesId)" />
		</template>
		<template #mobile-actions>
			<Button variant="ghost" size="md" icon="lucide-plus" aria-label="Add Video" @click="newVideo.open(seriesId)" />
		</template>
	</AppPageHeader>

	<div class="mx-auto max-w-[940px] px-3 pb-16 pt-6 sm:px-5">
		<DetailSkeleton v-if="!series.doc && !series.error" />
		<ErrorMessage v-else-if="series.error" :message="errorMessage(series.error)" />

		<div v-else-if="series.doc" class="space-y-8">
			<section>
				<div class="flex items-center gap-2">
					<EmojiPicker :model-value="series.doc.emoji ?? ''" @update:model-value="series.setValue.submit({ emoji: $event })">
						<template #trigger>
							<button
								type="button"
								class="grid size-10 place-content-center rounded-4 text-3xl leading-none hover:bg-surface-gray-2"
								aria-label="Change emoji"
							>
								{{ series.doc.emoji || '🎬' }}
							</button>
						</template>
					</EmojiPicker>
					<h1 class="text-3xl text-ink-gray-9">{{ series.doc.title }}</h1>
				</div>
				<p v-if="series.doc.summary" class="mt-2 text-p-base text-ink-gray-7">{{ series.doc.summary }}</p>
				<SeriesStats class="mt-5" :videos="videos" :published="published" />
			</section>

			<section>
				<h2 class="text-lg-semibold text-ink-gray-8">Videos</h2>
				<SeriesVideoList v-if="videos.length" class="mt-2" :videos="videos" />
				<div v-else class="flex flex-col items-center gap-3 py-12 text-center">
					<div class="rounded-full bg-surface-gray-2 p-3 text-ink-gray-5">
						<span class="lucide-clapperboard size-6" aria-hidden="true" />
					</div>
					<p class="text-base text-ink-gray-7">No videos in this series yet</p>
					<Button label="Add Video" icon-left="lucide-plus" @click="newVideo.open(seriesId)" />
				</div>
			</section>

			<section>
				<h2 class="text-lg-semibold text-ink-gray-8">Series notes</h2>
				<p class="mt-1 text-sm text-ink-gray-5">Format, cadence, repo, and anything else that every video shares.</p>
				<Editor
					:key="series.doc.name"
					:model-value="notes"
					:extensions="[RichTextKit]"
					placeholder="Write series notes…"
					@update:model-value="editNotes"
				>
					<template #default="{ editor }">
						<div class="mt-3 rounded-4 border border-outline-gray-2 px-4 py-3 focus-within:border-outline-gray-3">
							<EditorContent :editor="editor" class="min-h-24" />
						</div>
					</template>
				</Editor>
			</section>
		</div>
	</div>

	<SeriesDialog v-model:open="editOpen" :series="series.doc" :save="(values) => series.setValue.submit(values)" />
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { Button, Dropdown, ErrorMessage, dialog, toast, useDoc } from 'frappe-ui'
import { Editor, EditorContent, RichTextKit } from 'frappe-ui/editor'
import AppPageHeader from '@/components/shell/AppPageHeader.vue'
import DetailSkeleton from '@/components/stats/DetailSkeleton.vue'
import EmojiPicker from '@/components/EmojiPicker.vue'
import SeriesDialog from '@/components/videos/SeriesDialog.vue'
import SeriesStats from '@/components/videos/SeriesStats.vue'
import SeriesVideoList from '@/components/videos/SeriesVideoList.vue'
import { useAutosave } from '@/composables/useAutosave'
import { useNewVideo } from '@/composables/useNewVideo'
import { useSeriesVideos } from '@/composables/useSeriesVideos'
import { errorMessage } from '@/lib/errors'
import type { VideoSeries } from '@/types'

const props = defineProps<{ seriesId: string }>()

const router = useRouter()
const newVideo = useNewVideo()

const series = useDoc<VideoSeries>({ doctype: 'BWH Video Series', name: computed(() => props.seriesId) })
const { videos, published } = useSeriesVideos(() => props.seriesId)

const notes = ref('')
// Load the notes once. Our own saves come back and must not move the cursor.
watch(
	() => series.doc?.name,
	() => {
		notes.value = series.doc?.notes ?? ''
	},
	{ immediate: true },
)

const notesSave = useAutosave<VideoSeries>((values) => series.setValue.submit(values))

function editNotes(value: unknown) {
	notes.value = String(value ?? '')
	notesSave.queue({ notes: notes.value })
}

const editOpen = ref(false)

const menu = [
	{ label: 'Edit', icon: 'lucide-pencil', onClick: () => (editOpen.value = true) },
	{ label: 'Delete', icon: 'lucide-trash-2', theme: 'red' as const, onClick: remove },
]

function remove() {
	dialog.danger({
		title: 'Delete this series?',
		message: videos.value.length
			? 'Move or delete its videos first. A series with videos cannot be deleted.'
			: 'The series notes are deleted too.',
		confirmLabel: 'Delete',
		onConfirm: async () => {
			await series.delete.submit()
			toast.success('Series deleted')
			router.push('/series')
		},
	})
}
</script>
