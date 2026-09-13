<template>
	<div class="space-y-3">
		<div
			class="flex flex-col items-center justify-center gap-2 rounded-lg border border-dashed px-4 py-10 text-center transition-colors"
			:class="dragging ? 'border-outline-gray-4 bg-surface-gray-2' : 'border-outline-gray-2'"
			@dragover.prevent="dragging = true"
			@dragleave.prevent="dragging = false"
			@drop.prevent="onDrop"
		>
			<div class="rounded-full bg-surface-gray-2 p-3 text-ink-gray-5">
				<span class="lucide-file-spreadsheet size-6" aria-hidden="true" />
			</div>
			<p class="text-base text-ink-gray-8">
				{{ fileName || 'Drop a CSV file here' }}
			</p>
			<p class="text-p-sm text-ink-gray-5">
				The first row must have the column names. Up to 50,000 rows.
			</p>
			<Button
				class="mt-2"
				:label="fileName ? 'Pick another file' : 'Pick a file'"
				:loading="loading"
				@click="input?.click()"
			/>
			<input
				ref="input"
				type="file"
				accept=".csv,text/csv"
				class="hidden"
				@change="onPick"
			/>
		</div>
		<ErrorMessage :message="error" />
	</div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { Button, ErrorMessage } from 'frappe-ui'

defineProps<{ fileName: string; loading: boolean; error: string }>()
const emit = defineEmits<{ picked: [file: { name: string; content: string }] }>()

const input = ref<HTMLInputElement>()
const dragging = ref(false)

function onPick(event: Event) {
	const target = event.target as HTMLInputElement
	const file = target.files?.[0]
	// Clear the input, so picking the same file again still fires change.
	target.value = ''
	if (file) read(file)
}

function onDrop(event: DragEvent) {
	dragging.value = false
	const file = event.dataTransfer?.files[0]
	if (file) read(file)
}

async function read(file: File) {
	emit('picked', { name: file.name, content: await file.text() })
}
</script>
