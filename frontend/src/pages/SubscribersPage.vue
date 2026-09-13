<template>
	<PageHeader>
		<PageHeaderTitle class="min-w-0 flex-1">
			<h1 class="truncate">Subscribers</h1>
		</PageHeaderTitle>
		<Button
			variant="solid"
			theme="gray"
			icon-left="lucide-plus"
			label="Add Subscriber"
			@click="addOpen = true"
		/>
	</PageHeader>

	<div class="space-y-4 px-3 py-5 pb-10 sm:px-5">
		<TextInput
			v-model="search"
			class="w-full sm:max-w-xs"
			placeholder="Search by email…"
			aria-label="Search subscribers"
		>
			<template #prefix>
				<span class="lucide-search size-4 text-ink-gray-5" aria-hidden="true" />
			</template>
		</TextInput>

		<LoadingText v-if="subscribers.loading && !subscribers.data" :lines="4" />
		<ErrorMessage v-else-if="subscribers.error" :message="subscribers.error.message" />
		<SubscriberEmptyState
			v-else-if="!subscribers.data?.length"
			:searching="Boolean(debouncedSearch)"
			@add="addOpen = true"
		/>
		<SubscriberList v-else :subscribers="subscribers.data" />
	</div>

	<AddSubscriberDialog v-model:open="addOpen" @created="subscribers.reload()" />
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import {
	Button,
	ErrorMessage,
	LoadingText,
	PageHeader,
	PageHeaderTitle,
	TextInput,
	debounce,
	useList,
} from 'frappe-ui'
import AddSubscriberDialog from '@/components/subscribers/AddSubscriberDialog.vue'
import SubscriberEmptyState from '@/components/subscribers/SubscriberEmptyState.vue'
import SubscriberList from '@/components/subscribers/SubscriberList.vue'
import type { Subscriber } from '@/types'

const addOpen = ref(false)
const search = ref('')
const debouncedSearch = ref('')

watch(
	search,
	debounce((value: string) => {
		debouncedSearch.value = value.trim()
	}, 300),
)

const subscribers = useList<Subscriber>({
	doctype: 'Subscriber',
	fields: ['name', 'email', 'first_name', 'status', 'subscribed_on', { tags: ['tag'] }],
	filters: () => searchFilters(debouncedSearch.value),
	orderBy: 'creation desc',
	limit: 500,
	refetch: true,
})

// The document name is the email, so one `like` on `name` covers email search.
function searchFilters(query: string) {
	return query ? { name: ['like', `%${query}%`] as [string, string] } : {}
}
</script>
