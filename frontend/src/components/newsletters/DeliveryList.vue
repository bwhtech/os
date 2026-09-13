<template>
	<section class="space-y-3">
		<div class="flex flex-wrap items-center justify-between gap-2">
			<h2 class="text-lg-semibold text-ink-gray-8">Recipients</h2>
			<TabButtons v-model="status" :options="FILTERS" />
		</div>

		<LoadingText v-if="deliveries.loading && !deliveries.data" :lines="3" />
		<ErrorMessage v-else-if="deliveries.error" :message="deliveries.error.message" />
		<p v-else-if="!deliveries.data?.length" class="py-6 text-center text-p-base text-ink-gray-5">
			{{ status ? `No ${status.toLowerCase()} emails` : 'No recipients yet. The send job is starting.' }}
		</p>
		<div v-else class="overflow-x-auto">
			<List
				class="min-w-[36rem] list-row-px-0"
				:columns="['minmax(14rem,1fr)', '6rem', 'minmax(10rem,16rem)']"
				:row-height="40"
			>
				<ListHeader>
					<ListHeaderCell>Email</ListHeaderCell>
					<ListHeaderCell>Status</ListHeaderCell>
					<ListHeaderCell>Note</ListHeaderCell>
				</ListHeader>
				<ListRows :items="deliveries.data" row-key="name">
					<template #default="{ item, value }">
						<ListRow :value="value">
							<ListCell>
								<span class="truncate text-base text-ink-gray-8">{{ item.email }}</span>
							</ListCell>
							<ListCell>
								<Badge :label="item.status" :theme="STATUS_THEMES[item.status]" variant="subtle" />
							</ListCell>
							<ListCell>
								<span class="truncate text-sm text-ink-gray-5" :title="item.error ?? ''">
									{{ item.error || `Batch ${item.batch + 1}` }}
								</span>
							</ListCell>
						</ListRow>
					</template>
				</ListRows>
			</List>
			<p v-if="deliveries.data.length === LIMIT" class="pt-2 text-p-sm text-ink-gray-5">
				Showing the first {{ LIMIT }}.
			</p>
		</div>
	</section>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { Badge, ErrorMessage, LoadingText, TabButtons, useList } from 'frappe-ui'
import { List, ListCell, ListHeader, ListHeaderCell, ListRow, ListRows } from 'frappe-ui/list'
import type { DeliveryStatus, NewsletterDelivery } from '@/types'

const props = defineProps<{ issueId: string; refreshKey: number }>()

const LIMIT = 500

const FILTERS = [
	{ label: 'All', value: '' },
	{ label: 'Sent', value: 'Sent' },
	{ label: 'Queued', value: 'Queued' },
	{ label: 'Failed', value: 'Failed' },
	{ label: 'Skipped', value: 'Skipped' },
]

const STATUS_THEMES: Record<DeliveryStatus, 'gray' | 'blue' | 'green' | 'red'> = {
	Queued: 'blue',
	Sent: 'green',
	Failed: 'red',
	Skipped: 'gray',
}

const status = ref<DeliveryStatus | ''>('')

const deliveries = useList<NewsletterDelivery>({
	doctype: 'Newsletter Delivery',
	fields: ['name', 'email', 'status', 'batch', 'error'],
	filters: computed(() => ({ issue: props.issueId, ...(status.value && { status: status.value }) })),
	orderBy: 'batch asc, email asc',
	limit: LIMIT,
	refetch: true,
})

watch(
	() => props.refreshKey,
	() => deliveries.reload(),
)
</script>
