<template>
	<Dialog :open="open" :title="title" size="2xl" @update:open="emit('update:open', $event)">
		<div class="mb-5 flex items-center gap-1.5" aria-hidden="true">
			<span
				v-for="index in STEP_COUNT"
				:key="index"
				class="h-1 flex-1 rounded-full transition-colors"
				:class="index - 1 <= step ? 'bg-surface-gray-10' : 'bg-surface-gray-3'"
			/>
		</div>

		<CsvFileStep
			v-if="step === 0"
			:file-name="file.name"
			:loading="previewCall.loading"
			:error="errorMessage(previewCall.error)"
			@picked="onPicked"
		/>
		<ColumnMappingStep
			v-else-if="step === 1 && preview"
			v-model="mapping"
			:file-name="file.name"
			:total="preview.total"
			:columns="preview.columns"
		/>
		<ImportReviewStep v-else-if="step === 2 && preview" v-model:tags="tags" :preview="preview" />
		<ImportProgressStep v-else-if="step === 3 && progress" :progress="progress" />

		<ErrorMessage
			v-if="step === 1 || step === 2"
			class="mt-4"
			:message="errorMessage(previewCall.error || importCall.error)"
		/>

		<template #actions="{ close }">
			<div v-if="step === 3" class="flex w-full justify-end gap-2">
				<Button
					v-if="progress?.status === 'Running'"
					label="Close"
					@click="close"
				/>
				<Button v-else variant="solid" theme="gray" label="Done" @click="close" />
			</div>
			<div v-else class="flex w-full justify-between gap-2">
				<Button v-if="step > 0" label="Back" @click="step -= 1" />
				<span v-else />
				<div class="flex gap-2">
					<Button label="Cancel" @click="close" />
					<Button
						v-if="step === 1"
						variant="solid"
						theme="gray"
						label="Continue"
						:loading="previewCall.loading"
						:disabled="!mapping.email"
						@click="review"
					/>
					<Button
						v-if="step === 2"
						variant="solid"
						theme="gray"
						:label="importLabel"
						:loading="importCall.loading"
						:disabled="!importableCount"
						@click="startImport"
					/>
				</div>
			</div>
		</template>
	</Dialog>
</template>

<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
import { Button, Dialog, ErrorMessage, toast, useCall } from 'frappe-ui'
import ColumnMappingStep from '@/components/subscribers/import/ColumnMappingStep.vue'
import CsvFileStep from '@/components/subscribers/import/CsvFileStep.vue'
import ImportProgressStep from '@/components/subscribers/import/ImportProgressStep.vue'
import ImportReviewStep from '@/components/subscribers/import/ImportReviewStep.vue'
import { errorMessage } from '@/lib/errors'
import { onRealtime } from '@/lib/socket'
import type { ImportMapping, ImportPreview, ImportProgressEvent } from '@/types'

const props = defineProps<{ open: boolean }>()
const emit = defineEmits<{ 'update:open': [open: boolean]; imported: [] }>()

const STEP_COUNT = 4
const STEP_TITLES = ['Import Subscribers', 'Map Columns', 'Review Import']
const PROGRESS_TITLES = { Running: 'Importing…', Done: 'Import Done', Failed: 'Import Failed' }

type ImportParams = { content: string; mapping?: ImportMapping; tags?: string[] }

const step = ref(0)
const file = reactive({ name: '', content: '' })
const preview = ref<ImportPreview | null>(null)
const mapping = ref<ImportMapping>(emptyMapping())
const tags = ref<string[]>([])
const importId = ref<string | null>(null)
const progress = ref<ImportProgressEvent | null>(null)

/** Events can arrive before the enqueue reply, so keep the latest one for each import. */
const earlyEvents = new Map<string, ImportProgressEvent>()

const previewCall = useCall<ImportPreview, ImportParams>({
	url: '/api/v2/method/bwh_os.mailing.api.preview_subscriber_import',
	method: 'POST',
	immediate: false,
})

const importCall = useCall<{ import_id: string; total: number }, ImportParams>({
	url: '/api/v2/method/bwh_os.mailing.api.import_subscribers',
	method: 'POST',
	immediate: false,
})

const title = computed(() =>
	step.value === 3 && progress.value
		? PROGRESS_TITLES[progress.value.status]
		: STEP_TITLES[step.value],
)

const importableCount = computed(() =>
	preview.value ? preview.value.counts.New + preview.value.counts.Existing : 0,
)

const importLabel = computed(() => {
	const count = importableCount.value
	return `Import ${count} ${count === 1 ? 'row' : 'rows'}`
})

const isRunning = computed(() => progress.value?.status === 'Running')

// The listener lives with the page, so the toast still comes after the dialog closes.
onRealtime<ImportProgressEvent>('subscriber_import_progress', (event) => {
	if (event.import_id !== importId.value) {
		earlyEvents.set(event.import_id, event)
		return
	}
	applyProgress(event)
})

// Start each opening at the first step, unless an import is still running.
watch(
	() => props.open,
	(open) => {
		if (!open || isRunning.value) return
		step.value = 0
		file.name = ''
		file.content = ''
		preview.value = null
		mapping.value = emptyMapping()
		tags.value = []
		importId.value = null
		progress.value = null
		previewCall.reset()
		importCall.reset()
	},
)

async function onPicked(picked: { name: string; content: string }) {
	file.name = picked.name
	file.content = picked.content
	// No mapping yet, so the server maps the columns by name.
	const result = await previewCall.submit({ content: picked.content })
	if (!result) return
	preview.value = result
	mapping.value = result.mapping
	step.value = 1
}

async function review() {
	const result = await previewCall.submit({ content: file.content, mapping: mapping.value })
	if (!result) return
	preview.value = result
	step.value = 2
}

async function startImport() {
	const job = await importCall.submit({
		content: file.content,
		mapping: mapping.value,
		tags: tags.value,
	})
	if (!job) return
	importId.value = job.import_id
	progress.value = queuedProgress(job.import_id, job.total)
	step.value = 3
	const early = earlyEvents.get(job.import_id)
	if (early) applyProgress(early)
}

function applyProgress(event: ImportProgressEvent) {
	// socket.io keeps order, but an early event must not undo a later one.
	if (progress.value && event.status === 'Running' && event.done < progress.value.done) return
	progress.value = event
	if (event.status === 'Done') {
		toast.success(summary(event))
		emit('imported')
	} else if (event.status === 'Failed') {
		toast.error('Subscriber import failed')
		emit('imported')
	}
}

function summary({ counts }: ImportProgressEvent) {
	const parts = [`${counts.New} added`]
	if (counts.Existing) parts.push(`${counts.Existing} tagged`)
	const skipped = counts.Invalid + counts.Duplicate
	if (skipped) parts.push(`${skipped} skipped`)
	if (counts.Failed) parts.push(`${counts.Failed} failed`)
	return `Import done: ${parts.join(', ')}`
}

function queuedProgress(id: string, total: number): ImportProgressEvent {
	return {
		import_id: id,
		status: 'Running',
		done: 0,
		total,
		counts: { New: 0, Existing: 0, Invalid: 0, Duplicate: 0, Failed: 0 },
		errors: [],
		message: null,
	}
}

function emptyMapping(): ImportMapping {
	return { email: null, first_name: null, full_name: null, tags: null }
}
</script>
