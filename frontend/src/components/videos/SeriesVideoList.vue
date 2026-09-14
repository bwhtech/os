<template>
	<!-- Rows are links, so the hover surface bleeds into the gutter. -->
	<div class="-mx-3 overflow-x-auto">
		<List
			class="min-w-[32rem] list-row-px-3"
			:columns="['2.5rem', 'minmax(10rem,1fr)', '10rem', '6rem']"
			:row-height="48"
		>
			<ListRows :items="videos" row-key="name">
				<template #default="{ item, value }">
					<ListRow :value="value" :to="videoRoute(item)">
						<ListCell>
							<span class="text-sm tabular-nums text-ink-gray-4">{{ String(item.position).padStart(2, '0') }}</span>
						</ListCell>
						<ListCell>
							<span class="truncate text-base text-ink-gray-8">{{ item.title }}</span>
						</ListCell>
						<ListCell>
							<span class="flex items-center gap-2 truncate text-sm text-ink-gray-7">
								<span :class="['size-1.5 shrink-0 rounded-full', statusDot(item.status)]" aria-hidden="true" />
								{{ item.status }}
							</span>
						</ListCell>
						<ListCell class="justify-end">
							<span class="text-sm text-ink-gray-5">
								{{ item.publish_on ? dayjs(item.publish_on).format('D MMM') : '—' }}
							</span>
						</ListCell>
					</ListRow>
				</template>
			</ListRows>
		</List>
	</div>
</template>

<script setup lang="ts">
import { dayjs } from 'frappe-ui'
import { List, ListCell, ListRow, ListRows } from 'frappe-ui/list'
import type { SeriesVideo } from '@/composables/useSeriesVideos'
import { statusDot, videoRoute } from '@/lib/videos'

defineProps<{ videos: SeriesVideo[] }>()
</script>
