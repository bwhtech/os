<template>
	<section class="space-y-3">
		<div class="space-y-1">
			<h2 class="text-lg-semibold text-ink-gray-8">Downloads</h2>
			<p class="text-p-base text-ink-gray-6">
				<span class="tabular-nums">{{ count }}</span>
				{{ count === 1 ? 'download' : 'downloads' }} from welcome email links.
			</p>
		</div>

		<LoadingText v-if="downloads.loading && !downloads.data" :lines="3" />
		<ErrorMessage v-else-if="downloads.error" :message="downloads.error.message" />
		<div v-else-if="downloads.data?.length" class="overflow-x-auto">
			<List
				class="min-w-[28rem] list-row-px-0"
				:columns="['minmax(14rem,1fr)', '10rem']"
				:row-height="40"
			>
				<ListHeader>
					<ListHeaderCell>Subscriber</ListHeaderCell>
					<ListHeaderCell class="justify-end">Downloaded</ListHeaderCell>
				</ListHeader>
				<ListRows :items="downloads.data" row-key="name">
					<template #default="{ item, value }">
						<ListRow :value="value">
							<ListCell>
								<span class="truncate text-base text-ink-gray-8">{{ item.subscriber }}</span>
							</ListCell>
							<ListCell class="justify-end">
								<span class="whitespace-nowrap text-sm text-ink-gray-5">
									{{ dayjs(item.downloaded_on).format('D MMM YYYY, h:mm a') }}
								</span>
							</ListCell>
						</ListRow>
					</template>
				</ListRows>
			</List>
			<p v-if="count > downloads.data.length" class="pt-2 text-p-sm text-ink-gray-5">
				Showing the last {{ downloads.data.length }} downloads.
			</p>
		</div>
	</section>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { ErrorMessage, LoadingText, dayjs, useList } from 'frappe-ui'
import { List, ListCell, ListHeader, ListHeaderCell, ListRow, ListRows } from 'frappe-ui/list'

const props = defineProps<{ leadMagnetId: string; count: number }>()

const LIMIT = 100

const downloads = useList<{ name: string; subscriber: string; downloaded_on: string }>({
	doctype: 'Lead Magnet Download',
	fields: ['name', 'subscriber', 'downloaded_on'],
	filters: computed(() => ({ lead_magnet: props.leadMagnetId })),
	orderBy: 'downloaded_on desc',
	limit: LIMIT,
})
</script>
