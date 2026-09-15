<template>
	<!-- Fixed tracks need a floor. Below it the list scrolls sideways in its own box. -->
	<div class="overflow-x-auto">
		<List
			class="min-w-[56rem] list-row-px-0"
			:columns="['minmax(14rem,1fr)', '10rem', '7rem', '9rem', 'minmax(10rem,14rem)', '8rem']"
			:row-height="44"
			selectable
			v-model:selection="selection"
		>
			<ListHeader>
				<ListHeaderCell>Email</ListHeaderCell>
				<ListHeaderCell>Name</ListHeaderCell>
				<ListHeaderCell>Status</ListHeaderCell>
				<ListHeaderCell>Source</ListHeaderCell>
				<ListHeaderCell>Tags</ListHeaderCell>
				<ListHeaderCell class="justify-end">Subscribed</ListHeaderCell>
			</ListHeader>
			<ListRows :items="subscribers" row-key="name">
				<template #default="{ item, value }">
					<ListRow :value="value">
						<ListCell>
							<span class="truncate text-base text-ink-gray-8">{{ item.email }}</span>
						</ListCell>
						<ListCell>
							<span class="truncate text-sm text-ink-gray-7">{{ item.first_name }}</span>
						</ListCell>
						<ListCell>
							<Badge :label="item.status" :theme="statusTheme(item.status)" variant="subtle" />
						</ListCell>
						<ListCell>
							<code v-if="item.source_form" class="truncate font-mono text-sm text-ink-gray-6">
								{{ item.source_form }}
							</code>
							<span v-else class="text-sm text-ink-gray-5">Manual</span>
						</ListCell>
						<ListCell class="gap-1 overflow-hidden">
							<Badge
								v-for="row in item.tags"
								:key="row.tag"
								:label="row.tag"
								variant="outline"
								theme="gray"
								class="shrink-0"
							/>
						</ListCell>
						<ListCell class="justify-end">
							<span class="whitespace-nowrap text-sm text-ink-gray-5">
								{{ formatDate(item.subscribed_on) }}
							</span>
						</ListCell>
					</ListRow>
				</template>
			</ListRows>
		</List>
	</div>
</template>

<script setup lang="ts">
import { Badge, dayjs } from 'frappe-ui'
import { List, ListCell, ListHeader, ListHeaderCell, ListRow, ListRows } from 'frappe-ui/list'
import type { Subscriber, SubscriberStatus } from '@/types'

defineProps<{ subscribers: Subscriber[] }>()

/** Checked subscriber names. */
const selection = defineModel<string[]>('selection', { default: () => [] })

const STATUS_THEMES: Record<SubscriberStatus, 'green' | 'amber' | 'gray' | 'red'> = {
	Active: 'green',
	Pending: 'amber',
	Unsubscribed: 'gray',
	Bounced: 'red',
}

function statusTheme(status: SubscriberStatus) {
	return STATUS_THEMES[status] ?? 'gray'
}

function formatDate(value: string | null) {
	return value ? dayjs(value).format('D MMM YYYY') : ''
}
</script>
