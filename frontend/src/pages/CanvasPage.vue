<template>
	<AppPageHeader :breadcrumbs="breadcrumbs">
		<template #actions>
			<span class="self-center text-xs text-ink-gray-5" aria-live="polite">{{ SAVE_LABELS[saveState] }}</span>
			<Dropdown v-if="canvas.doc" :options="menu">
				<Button variant="ghost" icon="lucide-ellipsis" aria-label="More actions" />
			</Dropdown>
		</template>
	</AppPageHeader>

	<CanvasDocEditor ref="editor" v-model:save-state="saveState" class="h-[calc(100dvh-3rem)]" :canvas-id="canvasId" />
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import { Button, Dropdown, dialog, toast, useDoc } from 'frappe-ui'
import AppPageHeader from '@/components/shell/AppPageHeader.vue'
import CanvasDocEditor from '@/components/canvas/CanvasDocEditor.vue'
import { SAVE_LABELS, type SaveState } from '@/composables/useAutosave'
import type { Canvas } from '@/types'

const props = defineProps<{ canvasId: string }>()

const router = useRouter()

// The same document as the editor's. frappe-ui keeps one copy, so a rename shows in both.
const canvas = useDoc<Canvas>({ doctype: 'BWH Canvas', name: computed(() => props.canvasId) })

const editor = ref<InstanceType<typeof CanvasDocEditor> | null>(null)
const saveState = ref<SaveState>('idle')

const breadcrumbs = computed(() => {
	const current = { label: canvas.doc?.title || 'Untitled canvas' }
	return [{ label: 'Canvas', route: '/canvas' }, current]
})

const menu = [
	{ label: 'Rename', icon: 'lucide-pencil', onClick: rename },
	{ label: 'Delete', icon: 'lucide-trash-2', theme: 'red' as const, onClick: remove },
]

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
			await editor.value?.flush()
			await canvas.delete.submit()
			toast.success('Canvas deleted')
			router.push('/canvas')
		},
	})
}
</script>
