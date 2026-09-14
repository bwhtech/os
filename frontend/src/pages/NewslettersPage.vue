<template>
	<AppPageHeader title="Newsletters">
		<template #actions>
			<Button
				variant="solid"
				theme="gray"
				icon-left="lucide-plus"
				label="New Newsletter"
				@click="newOpen = true"
			/>
		</template>
		<template #mobile-actions>
			<Button variant="ghost" size="md" icon="lucide-plus" aria-label="New Newsletter" @click="newOpen = true" />
		</template>
	</AppPageHeader>

	<div class="px-3 py-5 pb-10 sm:px-5">
		<ListSkeleton v-if="issues.loading && !issues.data" />
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
				class="min-w-[48rem] list-row-px-3"
				:columns="['minmax(14rem,1fr)', '6rem', '6rem', '5rem', '5rem', '8rem']"
				:row-height="44"
			>
				<ListHeader>
					<ListHeaderCell>Subject</ListHeaderCell>
					<ListHeaderCell>Status</ListHeaderCell>
					<ListHeaderCell class="justify-end">Recipients</ListHeaderCell>
					<ListHeaderCell class="justify-end">Open %</ListHeaderCell>
					<ListHeaderCell class="justify-end">Click %</ListHeaderCell>
					<ListHeaderCell class="justify-end">Updated</ListHeaderCell>
				</ListHeader>
				<ListRows :items="issues.data" row-key="name">
					<template #default="{ item, value }">
						<ListRow :value="value" :to="`/newsletters/${item.name}`">
							<ListCell>
								<span class="truncate text-base text-ink-gray-8">{{ item.subject }}</span>
								<span
									v-if="item.is_public"
									class="lucide-globe ml-2 size-3.5 shrink-0 text-ink-gray-5"
									aria-label="In the web archive"
								/>
							</ListCell>
							<ListCell>
								<Badge :label="item.status" :theme="STATUS_THEMES[item.status]" variant="subtle" />
							</ListCell>
							<ListCell class="justify-end">
								<span v-if="item.status !== 'Draft'" class="text-sm tabular-nums text-ink-gray-6">
									{{ item.recipient_count }}
								</span>
							</ListCell>
							<ListCell class="justify-end">
								<span class="text-sm tabular-nums text-ink-gray-6">{{ rate(item.opened_count, item.sent_count) }}</span>
							</ListCell>
							<ListCell class="justify-end">
								<span class="text-sm tabular-nums text-ink-gray-6">{{ rate(item.clicked_count, item.sent_count) }}</span>
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
	dayjs,
	useList,
} from 'frappe-ui'
import AppPageHeader from '@/components/shell/AppPageHeader.vue'
import ListSkeleton from '@/components/list/ListSkeleton.vue'
import { List, ListCell, ListHeader, ListHeaderCell, ListRow, ListRows } from 'frappe-ui/list'
import NewNewsletterDialog from '@/components/newsletters/NewNewsletterDialog.vue'
import { STATUS_THEMES } from '@/lib/newsletters'
import type { NewsletterIssue } from '@/types'

const newOpen = ref(false)

const issues = useList<NewsletterIssue>({
	doctype: 'Newsletter Issue',
	fields: ['name', 'subject', 'status', 'is_public', 'recipient_count', 'sent_count', 'opened_count', 'clicked_count', 'modified'],
	orderBy: 'creation desc',
	limit: 200,
})

function rate(count: number, sent: number) {
	return sent ? `${Math.round((count / sent) * 100)}%` : ''
}
</script>
