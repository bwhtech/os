<template>
	<Dialog
		:open="open"
		:title="STEPS[step].title"
		size="2xl"
		:dismissible="!importCall.loading"
		@update:open="emit('update:open', $event)"
	>
		<div class="mb-5 flex items-center gap-1.5" aria-hidden="true">
			<span
				v-for="(_, index) in STEPS"
				:key="index"
				class="h-1 flex-1 rounded-full transition-colors"
				:class="index <= step ? 'bg-surface-gray-10' : 'bg-surface-gray-3'"
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

		<ErrorMessage
			v-if="step > 0"
			class="mt-4"
			:message="errorMessage(previewCall.error || importCall.error)"
		/>

		<template #actions="{ close }">
			<div class="flex w-full justify-between gap-2">
				<Button v-if="step > 0" label="Back" :disabled="importCall.loading" @click="step -= 1" />
				<span v-else />
				<div class="flex gap-2">
					<Button label="Cancel" :disabled="importCall.loading" @click="close" />
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
						@click="runImport(close)"
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
import ImportReviewStep from '@/components/subscribers/import/ImportReviewStep.vue'
import { errorMessage } from '@/lib/errors'
import type { ImportCounts, ImportMapping, ImportPreview } from '@/types'

const props = defineProps<{ open: boolean }>()
const emit = defineEmits<{ 'update:open': [open: boolean]; imported: [] }>()

const STEPS = [
	{ title: 'Import Subscribers' },
	{ title: 'Map Columns' },
	{ title: 'Review Import' },
]

type ImportParams = { content: string; mapping?: ImportMapping; tags?: string[] }

const step = ref(0)
const file = reactive({ name: '', content: '' })
const preview = ref<ImportPreview | null>(null)
const mapping = ref<ImportMapping>(emptyMapping())
const tags = ref<string[]>([])

const previewCall = useCall<ImportPreview, ImportParams>({
	url: '/api/v2/method/bwh_os.mailing.api.preview_subscriber_import',
	method: 'POST',
	immediate: false,
})

const importCall = useCall<ImportCounts, ImportParams>({
	url: '/api/v2/method/bwh_os.mailing.api.import_subscribers',
	method: 'POST',
	immediate: false,
})

const importableCount = computed(() =>
	preview.value ? preview.value.counts.New + preview.value.counts.Existing : 0,
)

const importLabel = computed(() => {
	const count = importableCount.value
	return `Import ${count} ${count === 1 ? 'row' : 'rows'}`
})

// Start each opening at the first step.
watch(
	() => props.open,
	(open) => {
		if (!open) return
		step.value = 0
		file.name = ''
		file.content = ''
		preview.value = null
		mapping.value = emptyMapping()
		tags.value = []
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

async function runImport(close: () => void) {
	const counts = await importCall.submit({
		content: file.content,
		mapping: mapping.value,
		tags: tags.value,
	})
	if (!counts) return
	toast.success(summary(counts))
	emit('imported')
	close()
}

function summary(counts: ImportCounts) {
	const parts = [`${counts.New} added`]
	if (counts.Existing) parts.push(`${counts.Existing} already on the list`)
	const skipped = counts.Invalid + counts.Duplicate
	if (skipped) parts.push(`${skipped} skipped`)
	return parts.join(', ')
}

function emptyMapping(): ImportMapping {
	return { email: null, first_name: null, full_name: null, tags: null }
}
</script>
