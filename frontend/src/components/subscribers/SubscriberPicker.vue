<template>
	<MultiSelect
		v-model="model"
		v-model:query="query"
		:options="options"
		:loading="subscribers.loading"
		:filterable="false"
		:label="label"
		:description="description"
		placeholder="Search by email or name"
	/>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { MultiSelect, debounce, useList } from 'frappe-ui'
import type { Subscriber } from '@/types'

withDefaults(defineProps<{ label?: string; description?: string }>(), {
	label: 'Subscribers',
	description: undefined,
})

const model = defineModel<string[]>({ required: true })

const query = ref('')
const debouncedQuery = ref('')
watch(
	query,
	debounce((value: string) => {
		debouncedQuery.value = value.trim()
	}, 300),
)

const subscribers = useList<Subscriber>({
	doctype: 'Subscriber',
	fields: ['name', 'email', 'first_name'],
	filters: () => ({
		status: 'Active',
		...(debouncedQuery.value && { name: ['like', `%${debouncedQuery.value}%`] }),
	}),
	orderBy: 'email asc',
	limit: 50,
})

/**
 * Emails for chips that are picked but no longer in the search results — the server only
 * sends back rows for the current query, and a chip needs its label even after the query
 * moves on. Grows for the life of the picker; a dialog is cheap to throw away.
 */
const knownEmails = ref(new Map<string, string>())
watch(
	() => subscribers.data,
	(rows) => {
		for (const row of rows ?? []) knownEmails.value.set(row.name, row.email)
	},
	{ immediate: true },
)

const options = computed(() => {
	const rows = subscribers.data ?? []
	const names = new Set([...rows.map((row) => row.name), ...model.value])
	return [...names].map((name) => ({
		label: rows.find((row) => row.name === name)?.email ?? knownEmails.value.get(name) ?? name,
		value: name,
	}))
})
</script>
