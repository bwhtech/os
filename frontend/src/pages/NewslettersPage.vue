<template>
	<PageHeader>
		<PageHeaderTitle class="min-w-0 flex-1">
			<h1 class="truncate">Newsletters</h1>
		</PageHeaderTitle>
		<Button
			variant="solid"
			theme="gray"
			icon-left="lucide-plus"
			label="New Newsletter"
			@click="newOpen = true"
		/>
	</PageHeader>

	<div class="px-3 py-5 pb-10 sm:px-5">
		<LoadingText v-if="issues.loading && !issues.data" :lines="4" />
		<ErrorMessage v-else-if="issues.error" :message="issues.error.message" />

		<div
			v-else-if="!issues.data?.length"
			class="flex flex-col items-center justify-center gap-3 py-16 text-center"
		>
			<div class="rounded-full bg-surface-gray-2 p-3 text-ink-gray-5">
				<span class="lucide-newspaper size-6" aria-hidden="true" />
			</div>
			<p class="text-base text-ink-gray-7">No newsletters yet</p>
			<p class="text-sm text-ink-gray-5">Write a draft, preview it, and send yourself a test.</p>
			<Button
				variant="solid"
				theme="gray"
				icon-left="lucide-plus"
				label="New Newsletter"
				class="mt-2"
				@click="newOpen = true"
			/>
		</div>

		<!-- Rows are links, so the hover surface bleeds into the gutter. -->
		<div v-else class="-mx-3 overflow-x-auto">
			<List
				class="min-w-[32rem] list-row-px-3"
				:columns="['minmax(14rem,1fr)', '6rem', '8rem']"
				:row-height="44"
			>
				<ListHeader>
					<ListHeaderCell>Subject</ListHeaderCell>
					<ListHeaderCell>Status</ListHeaderCell>
					<ListHeaderCell class="justify-end">Updated</ListHeaderCell>
				</ListHeader>
				<ListRows :items="issues.data" row-key="name">
					<template #default="{ item, value }">
						<ListRow :value="value" :to="`/newsletters/${item.name}`">
							<ListCell>
								<span class="truncate text-base text-ink-gray-8">{{ item.subject }}</span>
							</ListCell>
							<ListCell>
								<Badge :label="item.status" :theme="STATUS_THEMES[item.status]" variant="subtle" />
							</ListCell>
							<ListCell class="justify-end">
								<span class="text-sm tabular-nums text-ink-gray-6">
									{{ dayjs(item.modified).format('D MMM YYYY') }}
								</span>
							</ListCell>
						</ListRow>
					</template>
				</ListRows>
			</List>
		</div>
	</div>

	<NewNewsletterDialog v-model:open="newOpen" />
</template>

<script setup lang="ts">
import { ref } from 'vue'
import {
	Badge,
	Button,
	ErrorMessage,
	LoadingText,
	PageHeader,
	PageHeaderTitle,
	dayjs,
	useList,
} from 'frappe-ui'
import { List, ListCell, ListHeader, ListHeaderCell, ListRow, ListRows } from 'frappe-ui/list'
import NewNewsletterDialog from '@/components/newsletters/NewNewsletterDialog.vue'
import type { NewsletterIssue, NewsletterStatus } from '@/types'

const STATUS_THEMES: Record<NewsletterStatus, 'gray' | 'blue' | 'amber' | 'green' | 'red'> = {
	Draft: 'gray',
	Scheduled: 'blue',
	Sending: 'amber',
	Sent: 'green',
	Failed: 'red',
}

const newOpen = ref(false)

const issues = useList<NewsletterIssue>({
	doctype: 'Newsletter Issue',
	fields: ['name', 'subject', 'status', 'modified'],
	orderBy: 'creation desc',
	limit: 200,
})
</script>
