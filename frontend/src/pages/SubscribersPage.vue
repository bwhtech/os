<template>
	<PageHeader>
		<PageHeaderTitle class="min-w-0 flex-1">
			<h1 class="truncate">Subscribers</h1>
		</PageHeaderTitle>
		<!-- PageHeader puts no gap between its children. -->
		<div class="flex shrink-0 gap-2">
			<Button icon-left="lucide-upload" label="Import" @click="importOpen = true" />
			<Button
				variant="solid"
				theme="gray"
				icon-left="lucide-plus"
				label="Add Subscriber"
				@click="addOpen = true"
			/>
		</div>
	</PageHeader>

	<div class="space-y-4 px-3 py-5 pb-10 sm:px-5">
		<SubscriberFilters ref="filtersRef" v-model="filters" />

		<LoadingText v-if="subscribers.loading && !subscribers.data" :lines="4" />
		<ErrorMessage v-else-if="subscribers.error" :message="subscribers.error.message" />
		<SubscriberEmptyState
			v-else-if="!subscribers.data?.length"
			:filtered="isFiltered"
			@add="addOpen = true"
			@import="importOpen = true"
		/>
		<SubscriberList v-else :subscribers="subscribers.data" />
	</div>

	<AddSubscriberDialog v-model:open="addOpen" @created="subscribers.reload()" />
	<ImportSubscribersDialog v-model:open="importOpen" @imported="onImported" />
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import {
	Button,
	ErrorMessage,
	LoadingText,
	PageHeader,
	PageHeaderTitle,
	debounce,
	useList,
} from 'frappe-ui'
import AddSubscriberDialog from '@/components/subscribers/AddSubscriberDialog.vue'
import SubscriberEmptyState from '@/components/subscribers/SubscriberEmptyState.vue'
import SubscriberFilters, {
	type SubscriberFilterValues,
} from '@/components/subscribers/SubscriberFilters.vue'
import SubscriberList from '@/components/subscribers/SubscriberList.vue'
import ImportSubscribersDialog from '@/components/subscribers/import/ImportSubscribersDialog.vue'
import type { Subscriber } from '@/types'

const addOpen = ref(false)
const importOpen = ref(false)
const filtersRef = ref<InstanceType<typeof SubscriberFilters>>()
const filters = ref<SubscriberFilterValues>({ search: '', status: '', tag: '', form: '' })
const debouncedSearch = ref('')

watch(
	() => filters.value.search,
	debounce((value: string) => {
		debouncedSearch.value = value.trim()
	}, 300),
)

const isFiltered = computed(() =>
	Boolean(debouncedSearch.value || filters.value.status || filters.value.tag || filters.value.form),
)

const subscribers = useList<Subscriber>({
	doctype: 'Subscriber',
	fields: ['name', 'email', 'first_name', 'status', 'source_form', 'subscribed_on', { tags: ['tag'] }],
	filters: () => listFilters(),
	orderBy: 'creation desc',
	limit: 500,
	refetch: true,
})

function listFilters() {
	const { status, tag, form } = filters.value
	return {
		// The document name is the email, so one `like` on `name` covers email search.
		...(debouncedSearch.value && { name: ['like', `%${debouncedSearch.value}%`] as [string, string] }),
		...(status && { status }),
		...(tag && { 'tags.tag': tag }),
		...(form && { source_form: form }),
	}
}

function onImported() {
	subscribers.reload()
	filtersRef.value?.reload()
}
</script>
