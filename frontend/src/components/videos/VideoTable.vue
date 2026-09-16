<template>
	<!-- Rows are links, so the hover surface bleeds into the gutter. -->
	<div class="-mx-3 overflow-x-auto">
		<List
			class="min-w-[44rem] list-row-px-3"
			:columns="['minmax(12rem,1fr)', 'minmax(10rem,14rem)', '10rem', '6rem', '7rem']"
			:row-height="44"
		>
			<ListHeader>
				<ListHeaderCell>Title</ListHeaderCell>
				<ListHeaderCell>Series</ListHeaderCell>
				<ListHeaderCell>Status</ListHeaderCell>
				<ListHeaderCell>Publish</ListHeaderCell>
				<ListHeaderCell class="justify-end">Updated</ListHeaderCell>
			</ListHeader>
			<ListRows :items="videos" row-key="name">
				<template #default="{ item, value }">
					<ListRow :value="value" :route="videoRoute(item)">
						<ListCell>
							<span class="truncate text-base text-ink-gray-8">{{ item.title }}</span>
						</ListCell>
						<ListCell>
							<span v-if="item.series && seriesByName[item.series]" class="truncate text-sm text-ink-gray-7">
								{{ seriesByName[item.series].emoji }} {{ seriesByName[item.series].title }}
								<span class="tabular-nums text-ink-gray-4">#{{ item.position }}</span>
							</span>
							<span v-else class="text-sm text-ink-gray-4">—</span>
						</ListCell>
						<ListCell>
							<span class="flex items-center gap-2 truncate text-sm text-ink-gray-7">
								<span :class="['size-1.5 shrink-0 rounded-full', statusDot(item.status)]" aria-hidden="true" />
								{{ item.status }}
							</span>
						</ListCell>
						<ListCell>
							<span class="text-sm text-ink-gray-5">
								{{ item.publish_on ? dayjs(item.publish_on).format('D MMM') : '—' }}
							</span>
						</ListCell>
						<ListCell class="justify-end">
							<span class="text-sm text-ink-gray-5">{{ dayjs(item.modified).fromNow() }}</span>
						</ListCell>
					</ListRow>
				</template>
			</ListRows>
		</List>
	</div>
</template>

<script setup lang="ts">
import { dayjs } from 'frappe-ui'
import { List, ListCell, ListHeader, ListHeaderCell, ListRow, ListRows } from 'frappe-ui/list'
import { statusDot, videoRoute } from '@/lib/videos'
import type { Video, VideoSeriesSummary } from '@/types'

defineProps<{
	videos: Video[]
	seriesByName: Record<string, VideoSeriesSummary>
}>()
</script>
