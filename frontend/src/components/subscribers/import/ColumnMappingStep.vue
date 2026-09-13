<template>
	<div class="space-y-4">
		<p class="text-p-base text-ink-gray-7">
			{{ fileName }} has {{ total }} {{ total === 1 ? 'row' : 'rows' }}. Pick the column for each
			field. Columns with a known name are already picked.
		</p>

		<div class="divide-y divide-outline-gray-1">
			<div
				v-for="field in FIELDS"
				:key="field.key"
				class="grid gap-x-4 gap-y-1.5 py-3 first:pt-0 sm:grid-cols-[minmax(0,1fr)_minmax(0,1fr)] sm:items-center"
			>
				<div class="min-w-0">
					<FormLabel :label="field.label" size="md" :required="field.key === 'email'" />
					<p class="text-p-sm text-ink-gray-5">{{ field.description }}</p>
				</div>
				<div class="min-w-0 space-y-1">
					<Select
						class="w-full"
						:model-value="model[field.key] ?? ''"
						:options="options(field.key)"
						:aria-label="field.label"
						@update:model-value="model[field.key] = ($event as string) || null"
					/>
					<p class="truncate text-p-sm text-ink-gray-5">
						{{ sampleText(model[field.key]) }}
					</p>
				</div>
			</div>
		</div>
	</div>
</template>

<script setup lang="ts">
import { FormLabel, Select } from 'frappe-ui'
import type { ImportField, ImportMapping, ImportPreview } from '@/types'

const props = defineProps<{ fileName: string; total: number; columns: ImportPreview['columns'] }>()
const model = defineModel<ImportMapping>({ required: true })

const FIELDS: { key: ImportField; label: string; description: string }[] = [
	{ key: 'email', label: 'Email', description: 'Rows without a valid email are skipped.' },
	{ key: 'first_name', label: 'First Name', description: 'Optional.' },
	{
		key: 'full_name',
		label: 'Full Name',
		description: 'Used when First Name is empty. The first word becomes the first name.',
	},
	{
		key: 'tags',
		label: 'Tags',
		description: 'Separate tags with commas. You can also add tags to every row in the next step.',
	},
]

function options(field: ImportField) {
	const columns = props.columns.map((column) => ({ label: column.name, value: column.name }))
	return field === 'email' ? columns : [{ label: 'Do not import', value: '' }, ...columns]
}

function sampleText(columnName: string | null) {
	if (!columnName) return 'Not imported'
	const samples = props.columns.find((column) => column.name === columnName)?.samples ?? []
	return samples.length ? `For example: ${samples.join(', ')}` : 'This column is empty'
}
</script>
