<template>
	<AppPageHeader title="Subscribers">
		<template v-if="selection.length" #title-suffix>
			<span class="whitespace-nowrap text-sm text-ink-gray-5">{{ selection.length }} selected</span>
		</template>
		<template #actions>
			<SubscriberBulkActions
				v-if="selection.length"
				:names="selection"
				@done="onBulkDone"
				@clear="selection = []"
			/>
			<template v-else>
				<Button icon-left="lucide-upload" label="Import" @click="importOpen = true" />
				<Button
					variant="solid"
					theme="gray"
					icon-left="lucide-plus"
					label="Add Subscriber"
					@click="addOpen = true"
				/>
			</template>
		</template>
		<template #mobile-actions>
			<SubscriberBulkActions
				v-if="selection.length"
				compact
				:names="selection"
				@done="onBulkDone"
				@clear="selection = []"
			/>
			<Dropdown v-else :options="addMenu" align="end">
				<Button variant="ghost" size="md" icon="lucide-plus" aria-label="Add subscribers" />
			</Dropdown>
		</template>
	</AppPageHeader>

	<div class="space-y-4 px-3 py-5 pb-10 sm:px-5">
		<SubscriberFilters ref="filtersRef" v-model="filters" />

		<ListSkeleton v-if="rows.loading && !rows.data" />
		<ErrorMessage v-else-if="rows.error" :message="rows.error.message" />
		<SubscriberEmptyState
			v-else-if="!rows.data?.length && page === 1"
			:filtered="isFiltered"
			@add="addOpen = true"
			@import="importOpen = true"
		/>
		<template v-else>
			<!-- Dim the old page while the next one loads, so the pager does not jump. -->
			<SubscriberList
				v-model:selection="selection"
				:subscribers="rows.data ?? []"
				:class="{ 'opacity-60 transition-opacity': rows.loading }"
			/>
			<ListPagination v-model:page="page" v-model:page-length="pageLength" :total="total" />
		</template>
	</div>

	<AddSubscriberDialog v-model:open="addOpen" @created="reload()" />
	<ImportSubscribersDialog v-model:open="importOpen" @imported="onImported" />
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import {
	Button,
	Dropdown,
	ErrorMessage,
	debounce,
	type DropdownOptions,
} from 'frappe-ui'
import AppPageHeader from '@/components/shell/AppPageHeader.vue'
import ListSkeleton from '@/components/list/ListSkeleton.vue'
import ListPagination from '@/components/list/ListPagination.vue'
import SubscriberBulkActions from '@/components/subscribers/SubscriberBulkActions.vue'
import AddSubscriberDialog from '@/components/subscribers/AddSubscriberDialog.vue'
import SubscriberEmptyState from '@/components/subscribers/SubscriberEmptyState.vue'
import SubscriberFilters, {
	type SubscriberFilterValues,
} from '@/components/subscribers/SubscriberFilters.vue'
import SubscriberList from '@/components/subscribers/SubscriberList.vue'
import ImportSubscribersDialog from '@/components/subscribers/import/ImportSubscribersDialog.vue'
import { usePagedList } from '@/composables/usePagedList'
import type { Subscriber } from '@/types'

const addOpen = ref(false)
const importOpen = ref(false)

const addMenu: DropdownOptions = [
	{ label: 'Add Subscriber', icon: 'lucide-user-plus', onClick: () => (addOpen.value = true) },
	{ label: 'Import', icon: 'lucide-upload', onClick: () => (importOpen.value = true) },
]
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

const { rows, page, pageLength, total, reload } = usePagedList<Subscriber>({
	doctype: 'Subscriber',
	fields: ['name', 'email', 'first_name', 'status', 'source_form', 'subscribed_on', { tags: ['tag'] }],
	filters: () => listFilters(),
	orderBy: 'creation desc',
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

// Selection belongs to the rows on screen, so a new page or filter clears it.
const selection = ref<string[]>([])
watch([page, pageLength, listFilters], () => {
	selection.value = []
})

function onBulkDone() {
	selection.value = []
	onImported()
}

function onImported() {
	reload()
	filtersRef.value?.reload()
}
</script>
