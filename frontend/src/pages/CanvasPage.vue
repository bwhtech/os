<template>
	<AppPageHeader :breadcrumbs="breadcrumbs">
		<template #actions>
			<span class="self-center text-xs text-ink-gray-5" aria-live="polite">{{ SAVE_LABELS[state] }}</span>
			<Dropdown v-if="canvas.doc" :options="menu">
				<Button variant="ghost" icon="lucide-ellipsis" aria-label="More actions" />
			</Dropdown>
		</template>
	</AppPageHeader>

	<div v-if="!canvas.doc" class="px-3 py-6 sm:px-5">
		<ErrorMessage v-if="canvas.error" :message="errorMessage(canvas.error)" />
		<DetailSkeleton v-else class="mx-auto max-w-[770px]" />
	</div>

	<!-- A new key for each canvas, because the editor reads the scene only when it mounts. -->
	<CanvasEditor
		v-else
		:key="canvas.doc.name"
		class="h-[calc(100dvh-3rem)]"
		:scene="canvas.doc.scene"
		@change="(scene) => queue({ scene })"
	/>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { Button, Dropdown, ErrorMessage, dialog, toast, useDoc } from 'frappe-ui'
import AppPageHeader from '@/components/shell/AppPageHeader.vue'
import CanvasEditor from '@/components/canvas/CanvasEditor.vue'
import DetailSkeleton from '@/components/stats/DetailSkeleton.vue'
import { useAutosave } from '@/composables/useAutosave'
import { errorMessage } from '@/lib/errors'
import type { Canvas } from '@/types'

const props = defineProps<{ canvasId: string }>()

const SAVE_LABELS = { idle: '', saving: 'Saving…', saved: 'Saved', error: 'Not saved' }

const router = useRouter()

const canvas = useDoc<Canvas>({ doctype: 'BWH Canvas', name: computed(() => props.canvasId) })

const breadcrumbs = computed(() => [
	{ label: 'Canvas', route: '/canvas' },
	{ label: canvas.doc?.title || 'Untitled canvas' },
])

const menu = [
	{ label: 'Rename', icon: 'lucide-pencil', onClick: rename },
	{ label: 'Delete', icon: 'lucide-trash-2', theme: 'red' as const, onClick: remove },
]

// A drawing changes many times a second, so wait for a longer pause than the text editors do.
const { state, queue, flush } = useAutosave<Canvas>((values) => canvas.setValue.submit(values), 1500)

function rename() {
	dialog.prompt({
		title: 'Rename Canvas',
		confirmLabel: 'Rename',
		fields: [{ name: 'title', label: 'Title', required: true, defaultValue: canvas.doc?.title ?? '' }],
		onConfirm: async ({ values }) => {
			await canvas.setValue.submit({ title: values.title.trim() })
		},
	})
}

function remove() {
	dialog.danger({
		title: 'Delete this canvas?',
		message: 'The drawing is deleted for good.',
		confirmLabel: 'Delete',
		onConfirm: async () => {
			// A save that lands after the delete would fail, so send it first.
			await flush()
			await canvas.delete.submit()
			toast.success('Canvas deleted')
			router.push('/canvas')
		},
	})
}
</script>
