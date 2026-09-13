<template>
	<div class="flex flex-wrap gap-2">
		<TextInput
			v-model="model.search"
			class="w-full sm:w-64"
			placeholder="Search by email…"
			aria-label="Search subscribers"
		>
			<template #prefix>
				<span class="lucide-search size-4 text-ink-gray-5" aria-hidden="true" />
			</template>
		</TextInput>
		<Select
			v-model="model.status"
			class="w-[calc(50%-0.25rem)] sm:w-36"
			aria-label="Filter by status"
			:options="statusOptions"
		/>
		<Select
			v-model="model.tag"
			class="w-[calc(50%-0.25rem)] sm:w-44"
			aria-label="Filter by tag"
			:options="tagOptions"
		/>
		<Select
			v-model="model.form"
			class="w-full sm:w-44"
			aria-label="Filter by form"
			:options="formOptions"
		/>
	</div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { Select, TextInput, useList } from 'frappe-ui'
import type { SignupForm, SubscriberStatus, SubscriberTag } from '@/types'

export interface SubscriberFilterValues {
	search: string
	/** Empty means any value. */
	status: SubscriberStatus | ''
	tag: string
	form: string
}

const model = defineModel<SubscriberFilterValues>({ required: true })

const STATUSES: SubscriberStatus[] = ['Active', 'Pending', 'Unsubscribed', 'Bounced']

const statusOptions = [
	{ label: 'Any status', value: '' },
	...STATUSES.map((status) => ({ label: status, value: status })),
]

const tags = useList<SubscriberTag>({
	doctype: 'Subscriber Tag',
	fields: ['name'],
	orderBy: 'tag_name asc',
	limit: 1000,
})

const forms = useList<SignupForm>({
	doctype: 'Signup Form',
	fields: ['name', 'title'],
	orderBy: 'title asc',
	limit: 1000,
})

const tagOptions = computed(() => [
	{ label: 'Any tag', value: '' },
	...(tags.data ?? []).map((tag) => ({ label: tag.name, value: tag.name })),
])

const formOptions = computed(() => [
	{ label: 'Any form', value: '' },
	...(forms.data ?? []).map((form) => ({ label: form.title, value: form.name })),
])

// An import can create tags, so the page reloads the options after it.
defineExpose({ reload: () => tags.reload() })
</script>
